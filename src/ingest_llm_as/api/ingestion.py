"""
Ingestion API endpoints.

This module implements the core ingestion endpoints for processing
and storing content in the memOS.as memory system.
"""

import time
import traceback
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..config import get_settings
from ..models import (
    IngestionRequest,
    IngestionResponse,
    IngestionResult,
    ProcessingStatus,
    MemoryTier,
)
from ..observability.langfuse_client import get_langfuse_client
from ..observability.logging import (
    get_logger,
    log_ingestion_start,
    log_ingestion_complete,
)
from ..observability.metrics import (
    record_ingestion_start,
    record_ingestion_complete,
)
from ..observability.tracing import add_span_attributes
from ..utils.content_processor import (
    ContentProcessor,
    create_ingestion_metadata,
)
from ingest_llm_as.services.memos_client import (
    get_memos_client,
    MemOSClient,
    MemOSConnectionError,
    MemOSAPIError,
    generate_content_hash,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/text", response_model=IngestionResponse)
async def ingest_text(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
    memos_client: MemOSClient = Depends(get_memos_client),
) -> IngestionResponse:
    """
    Ingests text content, generates chunks and embeddings, and stores them in memOS; supports immediate synchronous processing or queued asynchronous processing.
    
    Returns:
        IngestionResponse: Contains `ingestion_id`, overall `status` (PENDING, COMPLETED, or FAILED), `total_chunks`, optional per-chunk `results`, `processing_time_ms` when available, and a human-readable `message`.
    
    Raises:
        HTTPException: On validation failures, storage/service connectivity issues, or other processing errors.
    """
    print("DEBUG ingest_text: Endpoint called")
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
                "endpoint": "/ingest/text",
            },
            tags=["ingestion", "text", request.metadata.content_type.value],
            input_data={
                "content_preview": (
                    request.content[:200] + "..."
                    if len(request.content) > 200
                    else request.content
                ),
                "metadata": request.metadata.model_dump(),
                "chunk_size": request.chunk_size,
            },
        )

    # Record metrics and logging
    record_ingestion_start(
        "/ingest/text",
        request.metadata.content_type.value,
        len(request.content),
    )
    log_ingestion_start(
        logger,
        str(ingestion_id),
        request.metadata.content_type.value,
        len(request.content),
        request.metadata.model_dump(),
    )

    # Add tracing attributes
    add_span_attributes(
        ingestion_id=str(ingestion_id),
        content_type=request.metadata.content_type.value,
        content_size=len(request.content),
        source_type=request.metadata.source.value,
    )

    try:
        # Initialize content processor with embedding capability
        processor = ContentProcessor(chunk_size=request.chunk_size)

        # Validate content size early
        if len(request.content) > get_settings().max_content_size:
            raise HTTPException(
                status_code=413,
                detail=f"Content too large: {len(request.content)} > {get_settings().max_content_size}",
            )

        # Check memOS.as connectivity
        if not await memos_client.health_check():
            raise HTTPException(
                status_code=503, detail="memOS.as service unavailable"
            )

        # Detect content type for intelligent processing
        detected_type = processor.detect_content_type(
            content=request.content, file_path=request.metadata.source_url
        )

        # Process content with embeddings - use AST parser for Python code
        if detected_type == "python" or request.metadata.content_type.value == "code":
            processing_result = await processor.process_python_code_with_embeddings(
                source_code=request.content,
                file_path=request.metadata.source_url,
                content_type=request.metadata.content_type.value,
            )
        else:
            processing_result = await processor.process_content_with_embeddings(
                content=request.content,
                content_type=request.metadata.content_type.value,
                detected_type=detected_type,
            )

        chunks = processing_result["chunks"]
        embeddings = processing_result["embeddings"]
        processing_stats = processing_result["processing_stats"]

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No valid content chunks could be created",
            )

        logger.info(
            f"Created {len(chunks)} chunks for ingestion {ingestion_id}",
            embeddings_generated=processing_stats["embeddings_generated"],
            embedding_enabled=processing_stats["embedding_enabled"],
        )

        # Process synchronously or asynchronously based on request
        if request.process_async and get_settings().enable_async_processing:
            # Queue for background processing
            background_tasks.add_task(
                _process_chunks_async,
                chunks,
                embeddings,
                request,
                ingestion_id,
                processor,
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
                chunks, embeddings, request, processor, memos_client
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
        chunks_count = len(getattr(response, "results", []))

        record_ingestion_complete(
            "/ingest/text",
            request.metadata.content_type.value,
            duration_ms / 1000,
            response.status.value,
            chunks_count,
        )

        log_ingestion_complete(
            logger,
            str(ingestion_id),
            response.status.value,
            duration_ms,
            chunks_count,
        )

        # Update Langfuse trace with completion data
        if langfuse_client.enabled and trace_id:
            langfuse_client.client.trace(
                id=trace_id,
                output={
                    "status": response.status.value,
                    "total_chunks": response.total_chunks,
                    "processing_time_ms": duration_ms,
                    "chunks_processed": chunks_count,
                },
            )

            # Add quality score based on success rate
            success_rate = 1.0 if response.status == ProcessingStatus.COMPLETED else 0.0
            if response.results:
                failed_count = len(
                    [r for r in response.results if r.status == ProcessingStatus.FAILED]
                )
                success_rate = (len(response.results) - failed_count) / len(
                    response.results
                )

            langfuse_client.score_trace(
                trace_id=trace_id,
                name="ingestion_success_rate",
                value=success_rate,
                comment=f"Ingestion completed with {chunks_count} chunks processed",
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
    embeddings: List[Optional[List[float]]],
    request: IngestionRequest,
    processor: ContentProcessor,
    memos_client: MemOSClient,
) -> List[IngestionResult]:
    """
    Process chunks synchronously with embeddings.

    Args:
        chunks: Content chunks to process
        embeddings: Corresponding embeddings for each chunk
        request: Original ingestion request
        processor: Content processor instance
        memos_client: memOS.as client

    Returns:
        List[IngestionResult]: Processing results for each chunk
    """
    results = []

    for i, chunk in enumerate(chunks):
        try:
            # Get corresponding embedding for this chunk
            embedding = embeddings[i] if i < len(embeddings) else None

            result = await _process_single_chunk(
                chunk=chunk,
                chunk_index=i,
                total_chunks=len(chunks),
                request=request,
                processor=processor,
                memos_client=memos_client,
                embedding=embedding,
            )
            results.append(result)

        except Exception as e:
            # Capture full traceback and error type to aid debugging
            logger.error(
                f"Error processing chunk {i}: {e} ({type(e).__name__})\n{traceback.format_exc()}"
            )

            # Create failed result
            result = IngestionResult(
                memory_tier=MemoryTier.SEMANTIC,  # Default tier
                content_hash=generate_content_hash(chunk),
                chunk_size=len(chunk),
                status=ProcessingStatus.FAILED,
                error_message=f"{type(e).__name__}: {e}",
            )
            results.append(result)

    return results


async def _process_chunks_async(
    chunks: List[str],
    embeddings: List[Optional[List[float]]],
    request: IngestionRequest,
    ingestion_id: UUID,
    processor: ContentProcessor,
):
    """
    Process a batch of content chunks with their embeddings in a background context using a fresh MemOS client.
    
    This runs processing for each chunk (including storage) using the provided content processor and logs completion or failure for the given ingestion operation.
    
    Parameters:
        chunks (List[str]): Ordered list of content chunks to process.
        embeddings (List[Optional[List[float]]]): Parallel list of optional embeddings corresponding to each chunk.
        request (IngestionRequest): Original ingestion request carrying metadata and options.
        ingestion_id (UUID): Unique identifier for the ingestion run, used for logging and tracing.
        processor (ContentProcessor): Processor instance responsible for extracting metadata and preparing chunks.
    """
    logger.info(f"Starting async processing for ingestion {ingestion_id}")

    try:
        # Use a fresh client context to avoid un-awaited coroutine issues
        async with MemOSClient() as memos_client:
            await _process_chunks_sync(
                chunks, embeddings, request, processor, memos_client
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
    embedding: Optional[List[float]] = None,
) -> IngestionResult:
    """
    Process a single content chunk and store it in memOS, producing a per-chunk IngestionResult.
    
    Parameters:
        embedding (Optional[List[float]]): Optional embedding vector to attach to the stored memory.
    
    Returns:
        IngestionResult: Result for this chunk containing the stored memory's id (or None if not returned),
        the selected memory tier, the content hash, the chunk size in characters, and a status of
        `ProcessingStatus.COMPLETED` if storage succeeded or `ProcessingStatus.FAILED` otherwise.
    """
    try:
        print(f"DEBUG: Processing chunk {chunk_index}, starting...")

        # Generate content hash for deduplication
        content_hash = generate_content_hash(chunk)
        print(f"DEBUG: Generated content hash: {content_hash}")

        # Extract additional metadata from content
        content_metadata = processor.extract_metadata_from_content(chunk)
        print("DEBUG: Extracted content metadata")

        # Create comprehensive metadata
        storage_metadata = create_ingestion_metadata(
            original_metadata=request.metadata.model_dump(),
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            processing_info=content_metadata,
        )
        print("DEBUG: Created storage metadata")

        # Determine memory tier based on content type and metadata
        memory_tier = _determine_memory_tier(request.metadata.content_type)
        print(f"DEBUG: Determined memory tier: {memory_tier}")

        # Store in memOS.as with embedding
        print("DEBUG: About to call memos_client.store_memory")
        storage_response = await memos_client.store_memory(
            content=chunk,
            memory_tier=memory_tier,
            metadata=storage_metadata,
            embedding=embedding,
        )
        print("DEBUG: memOS storage completed successfully")

        # Create result - handle case where memory_id may not be returned
        result_memory_id = None
        if hasattr(storage_response, "memory_id") and storage_response.memory_id:
            # memOS.as returns integer memory_id, use it directly
            result_memory_id = storage_response.memory_id

        print("DEBUG: About to create IngestionResult")
        result = IngestionResult(
            memory_id=result_memory_id,
            memory_tier=memory_tier,
            content_hash=content_hash,
            chunk_size=len(chunk),
            status=(
                ProcessingStatus.COMPLETED
                if storage_response.success
                else ProcessingStatus.FAILED
            ),
        )
        print("DEBUG: Created IngestionResult successfully")
        return result

    except Exception as e:
        print(f"DEBUG: Exception occurred in _process_single_chunk: {e}")
        print(f"DEBUG: Exception type: {type(e).__name__}")
        import traceback

        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise


def _determine_memory_tier(content_type) -> MemoryTier:
    """
    Map a content type identifier to the MemoryTier to use for storage.
    
    Parameters:
        content_type: A content type name or enum (e.g., "text", "python", enum with a .value) used to select the memory tier.
    
    Returns:
        MemoryTier: The selected memory tier. Unrecognized content types default to MemoryTier.SEMANTIC.
    """
    # Simple mapping for now - can be enhanced with ML-based classification
    # Normalize to a lowercase string whether enum or str
    try:
        ct_str = (
            content_type.value if hasattr(content_type, "value") else str(content_type)
        )
        ct_str = ct_str.lower()
    except Exception:
        ct_str = "text"

    tier_mapping = {
        "text": MemoryTier.SEMANTIC,
        "documentation": MemoryTier.SEMANTIC,
        "markdown": MemoryTier.SEMANTIC,
        "code": MemoryTier.PROCEDURAL,
        "json": MemoryTier.SEMANTIC,
        # Add common aliases
        "python": MemoryTier.PROCEDURAL,
        "source_code": MemoryTier.PROCEDURAL,
    }

    return tier_mapping.get(ct_str, MemoryTier.SEMANTIC)


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