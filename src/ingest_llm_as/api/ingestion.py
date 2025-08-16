"""
Ingestion API endpoints.

This module implements the core ingestion endpoints for processing
and storing content in the memOS.as memory system.
"""

import time
from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks

from ..models import (
    IngestionRequest,
    IngestionResponse,
    IngestionResult,
    ProcessingStatus,
    MemoryTier,
)
from ..services.memos_client import (
    get_memos_client,
    MemOSClient,
    MemOSConnectionError,
    MemOSAPIError,
    generate_content_hash,
)
from ..utils.content_processor import ContentProcessor, create_ingestion_metadata
from ..config import settings
from ..observability.logging import get_logger, log_ingestion_start, log_ingestion_complete
from ..observability.metrics import record_ingestion_start, record_ingestion_complete
from ..observability.tracing import add_span_attributes
from ..observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/text", response_model=IngestionResponse)
async def ingest_text(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    memos_client: MemOSClient = Depends(get_memos_client),
) -> IngestionResponse:
    """
    Ingest text content into the memory system.

    This endpoint processes text content, chunks it if necessary,
    and stores it in the appropriate memOS.as memory tiers.

    Args:
        request: Ingestion request with content and metadata
        background_tasks: FastAPI background tasks for async processing
        memos_client: memOS.as client dependency

    Returns:
        IngestionResponse: Processing status and results

    Raises:
        HTTPException: On validation or processing errors
    """
    start_time = time.time()
    ingestion_id = uuid4()
    
    # Initialize Langfuse tracing
    langfuse_client = get_langfuse_client()
    trace_id = None
    
    if langfuse_client.enabled:
        trace_id = langfuse_client.create_trace(
            name="text_ingestion",
            metadata={
                "ingestion_id": str(ingestion_id),
                "content_type": request.metadata.content_type.value,
                "content_size": len(request.content),
                "source_type": request.metadata.source.value,
                "process_async": request.process_async,
                "endpoint": "/ingest/text"
            },
            tags=["ingestion", "text", request.metadata.content_type.value],
            input_data={
                "content_preview": request.content[:200] + "..." if len(request.content) > 200 else request.content,
                "metadata": request.metadata.model_dump(),
                "chunk_size": request.chunk_size
            }
        )

    # Record metrics and logging
    record_ingestion_start("/ingest/text", request.metadata.content_type.value, len(request.content))
    log_ingestion_start(logger, str(ingestion_id), request.metadata.content_type.value, len(request.content), request.metadata.model_dump())
    
    # Add tracing attributes
    add_span_attributes(
        ingestion_id=str(ingestion_id),
        content_type=request.metadata.content_type.value,
        content_size=len(request.content),
        source_type=request.metadata.source.value
    )

    try:
        # Initialize content processor
        processor = ContentProcessor(chunk_size=request.chunk_size)

        # Clean and validate content
        cleaned_content = processor.clean_content(request.content)

        if len(cleaned_content) > settings.max_content_size:
            raise HTTPException(
                status_code=413,
                detail=f"Content too large: {len(cleaned_content)} > {settings.max_content_size}",
            )

        # Check memOS.as connectivity
        if not await memos_client.health_check():
            raise HTTPException(status_code=503, detail="memOS.as service unavailable")

        # Process content into chunks
        chunks = processor.chunk_content(cleaned_content)

        if not chunks:
            raise HTTPException(
                status_code=400, detail="No valid content chunks could be created"
            )

        logger.info(f"Created {len(chunks)} chunks for ingestion {ingestion_id}")

        # Process synchronously or asynchronously based on request
        if request.process_async and settings.enable_async_processing:
            # Queue for background processing
            background_tasks.add_task(
                _process_chunks_async, chunks, request, ingestion_id, processor
            )

            # Return immediate response
            response = IngestionResponse(
                ingestion_id=ingestion_id,
                status=ProcessingStatus.PENDING,
                total_chunks=len(chunks),
                message="Ingestion queued for async processing",
            )
        else:
            # Process synchronously
            results = await _process_chunks_sync(
                chunks, request, processor, memos_client
            )

            # Determine overall status
            failed_results = [r for r in results if r.status == ProcessingStatus.FAILED]
            overall_status = (
                ProcessingStatus.FAILED
                if failed_results
                else ProcessingStatus.COMPLETED
            )

            response = IngestionResponse(
                ingestion_id=ingestion_id,
                status=overall_status,
                total_chunks=len(chunks),
                results=results,
                processing_time_ms=int((time.time() - start_time) * 1000),
                message=f"Processed {len(results)} chunks, {len(failed_results)} failed",
            )

        # Record completion metrics and logging
        duration_ms = int((time.time() - start_time) * 1000)
        chunks_count = len(getattr(response, 'results', []))
        
        record_ingestion_complete(
            "/ingest/text", 
            request.metadata.content_type.value, 
            duration_ms / 1000, 
            response.status.value,
            chunks_count
        )
        
        log_ingestion_complete(
            logger, 
            str(ingestion_id), 
            response.status.value, 
            duration_ms, 
            chunks_count
        )
        
        # Update Langfuse trace with completion data
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "status": response.status.value,
                    "total_chunks": response.total_chunks,
                    "processing_time_ms": duration_ms,
                    "chunks_processed": chunks_count
                }
            )
            
            # Add quality score based on success rate
            success_rate = 1.0 if response.status == ProcessingStatus.COMPLETED else 0.0
            if response.results:
                failed_count = len([r for r in response.results if r.status == ProcessingStatus.FAILED])
                success_rate = (len(response.results) - failed_count) / len(response.results)
            
            langfuse_client.score_trace(
                trace_id=trace_id,
                name="ingestion_success_rate",
                value=success_rate,
                comment=f"Ingestion completed with {chunks_count} chunks processed"
            )
        
        return response

    except HTTPException:
        raise
    except MemOSConnectionError as e:
        logger.error(f"memOS.as connection error in ingestion {ingestion_id}: {e}")
        raise HTTPException(
            status_code=503, detail="Memory storage service unavailable"
        )
    except MemOSAPIError as e:
        logger.error(f"memOS.as API error in ingestion {ingestion_id}: {e}")
        raise HTTPException(status_code=502, detail="Memory storage service error")
    except Exception as e:
        logger.error(f"Unexpected error in ingestion {ingestion_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Internal server error during ingestion"
        )


async def _process_chunks_sync(
    chunks: List[str],
    request: IngestionRequest,
    processor: ContentProcessor,
    memos_client: MemOSClient,
) -> List[IngestionResult]:
    """
    Process chunks synchronously.

    Args:
        chunks: Content chunks to process
        request: Original ingestion request
        processor: Content processor instance
        memos_client: memOS.as client

    Returns:
        List[IngestionResult]: Processing results for each chunk
    """
    results = []

    for i, chunk in enumerate(chunks):
        try:
            result = await _process_single_chunk(
                chunk=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                request=request,
                processor=processor,
                memos_client=memos_client,
            )
            results.append(result)

        except Exception as e:
            logger.error(f"Error processing chunk {i}: {e}")

            # Create failed result
            result = IngestionResult(
                memory_tier=MemoryTier.SEMANTIC,  # Default tier
                content_hash=generate_content_hash(chunk),
                chunk_size=len(chunk),
                status=ProcessingStatus.FAILED,
                error_message=str(e),
            )
            results.append(result)

    return results


async def _process_chunks_async(
    chunks: List[str],
    request: IngestionRequest,
    ingestion_id: uuid4,
    processor: ContentProcessor,
):
    """
    Process chunks asynchronously in background.

    Args:
        chunks: Content chunks to process
        request: Original ingestion request
        ingestion_id: Unique ingestion identifier
        processor: Content processor instance
    """
    logger.info(f"Starting async processing for ingestion {ingestion_id}")

    try:
        async with get_memos_client() as memos_client:
            await _process_chunks_sync(
                chunks, request, processor, memos_client
            )

        # TODO: Store results for later retrieval via status endpoint
        logger.info(f"Async processing completed for ingestion {ingestion_id}")

    except Exception as e:
        logger.error(f"Async processing failed for ingestion {ingestion_id}: {e}")


async def _process_single_chunk(
    chunk: str,
    chunk_index: int,
    total_chunks: int,
    request: IngestionRequest,
    processor: ContentProcessor,
    memos_client: MemOSClient,
) -> IngestionResult:
    """
    Process a single content chunk.

    Args:
        chunk: Content chunk to process
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks
        request: Original ingestion request
        processor: Content processor instance
        memos_client: memOS.as client

    Returns:
        IngestionResult: Processing result for this chunk
    """
    # Generate content hash for deduplication
    content_hash = generate_content_hash(chunk)

    # Extract additional metadata from content
    content_metadata = processor.extract_metadata_from_content(chunk)

    # Create comprehensive metadata
    storage_metadata = create_ingestion_metadata(
        original_metadata=request.metadata.model_dump(),
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        processing_info=content_metadata,
    )

    # Determine memory tier based on content type and metadata
    memory_tier = _determine_memory_tier(request.metadata.content_type)

    # Store in memOS.as
    storage_response = await memos_client.store_memory(
        content=chunk, memory_tier=memory_tier, metadata=storage_metadata
    )

    # Create result
    return IngestionResult(
        memory_id=storage_response.memory_id,
        memory_tier=memory_tier,
        content_hash=content_hash,
        chunk_size=len(chunk),
        status=ProcessingStatus.COMPLETED,
    )


def _determine_memory_tier(content_type: str) -> MemoryTier:
    """
    Determine appropriate memory tier for content type.

    Args:
        content_type: Type of content being ingested

    Returns:
        MemoryTier: Appropriate memory tier
    """
    # Simple mapping for now - can be enhanced with ML-based classification
    tier_mapping = {
        "text": MemoryTier.SEMANTIC,
        "documentation": MemoryTier.SEMANTIC,
        "markdown": MemoryTier.SEMANTIC,
        "code": MemoryTier.PROCEDURAL,
        "json": MemoryTier.SEMANTIC,
    }

    return tier_mapping.get(content_type.lower(), MemoryTier.SEMANTIC)


@router.get("/status/{ingestion_id}")
async def get_ingestion_status(ingestion_id: str):
    """
    Get status of an async ingestion operation.

    Args:
        ingestion_id: UUID of the ingestion operation

    Returns:
        Current status of the ingestion
    """
    # TODO: Implement status tracking for async operations
    return {"message": "Status tracking not yet implemented"}
