"""
Graph Parser API Endpoint for CortexBridge InGest-LLMs Engine.

Provides REST API endpoint for parsing text into Knowledge Graphs
using DocumentParser with Spacy Transformers and NLTK.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, UploadFile, File as FastAPIFile
from pydantic import BaseModel, Field

from ingest_llm_as.parsers.document_parser import DocumentParser
from ingest_llm_as.services.file_loader_service import FileLoaderService

logger = logging.getLogger(__name__)

# Create router for graph parser endpoints
router = APIRouter(prefix="/graph", tags=["Graph Parser"])

# Global parser instance (loaded at startup)
_parser: DocumentParser | None = None


class ParseRequest(BaseModel):
    """Request model for text parsing."""

    text: str = Field(..., description="Text content to parse")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Optional configuration for parsing behavior"
    )


class ParseResponse(BaseModel):
    """Response model containing parsed Knowledge Graph."""

    metadata: Dict[str, Any] = Field(description="Metadata about the parsing operation")
    nodes: list[Dict[str, Any]] = Field(
        description="List of extracted nodes (entities)"
    )
    edges: list[Dict[str, Any]] = Field(
        description="List of extracted relationships (edges)"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    model_loaded: bool = Field(description="Whether NLP model is loaded")
    model_name: str = Field(description="Name of loaded Spacy model")


def get_parser() -> DocumentParser:
    """
    Get or create global parser instance.

    Returns:
        DocumentParser instance

    Raises:
        RuntimeError: If parser cannot be initialized
    """
    global _parser

    if _parser is None:
        try:
            _parser = DocumentParser()
            logger.info("DocumentParser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentParser: {e}")
            raise RuntimeError(f"DocumentParser initialization failed: {e}")

    return _parser


@router.post("/parse", response_model=ParseResponse, tags=["nlp", "graph"])
async def parse_text(request: ParseRequest) -> ParseResponse:
    """
    Parse text into a Knowledge Graph structure.

    Args:
        request: ParseRequest containing text and optional config

    Returns:
        ParseResponse with nodes and edges

    Raises:
        HTTPException: If parsing fails

    Note:
        Large documents (>10,000 characters) may take 10-30 seconds to process.
        Consider increasing client timeout or splitting into smaller chunks.
    """
    try:
        parser = get_parser()

        text_length = len(request.text)
        logger.info(f"Parsing text ({text_length} characters)")

        # Warn about large documents
        if text_length > 50000:
            logger.warning(
                f"Large document detected ({text_length} chars). "
                "This may take 30+ seconds. Consider chunking."
            )

        # Parse text using DocumentParser
        result = parser.parse(request.text)

        # Add processing time warning to metadata if document is large
        if text_length > 10000:
            result["metadata"]["warning"] = (
                f"Large document ({text_length} chars) - "
                "processing may take 10-30s. Increase client timeout if needed."
            )

        logger.info(
            f"✅ Parsed into {len(result['nodes'])} nodes and "
            f"{len(result['edges'])} edges"
        )

        return ParseResponse(
            metadata=result["metadata"],
            nodes=result["nodes"],
            edges=result["edges"],
        )

    except Exception as e:
        logger.error(f"❌ Parsing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post("/parse/file", response_model=ParseResponse, tags=["nlp", "graph", "file-upload"])
async def parse_file(
    file: UploadFile = FastAPIFile(..., description="Document file to parse (TXT, MD, PDF, DOCX)")
) -> ParseResponse:
    """
    Parse uploaded file into a Knowledge Graph structure.
    
    Accepts file uploads and extracts text before parsing into nodes/edges.
    Supported formats: TXT, MD, PDF, DOCX
    
    Args:
        file: Uploaded file object
        
    Returns:
        ParseResponse with nodes and edges
        
    Raises:
        HTTPException: If file processing or parsing fails
        
    Note:
        Large documents (>10,000 characters) may take 10-30 seconds to process.
        Consider increasing client timeout or splitting into smaller chunks.
    """
    try:
        # Read file content
        content_bytes = await file.read()
        filename = file.filename or "unknown"
        
        logger.info(f"Processing uploaded file: {filename} ({len(content_bytes)} bytes)")
        
        # Determine MIME type from file extension or content_type
        mime_type = file.content_type or "text/plain"
        
        # Handle text files directly (TXT, MD)
        if mime_type.startswith("text/") or filename.lower().endswith((".txt", ".md")):
            try:
                extracted_text = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=422,
                    detail=f"File '{filename}' is not valid UTF-8 text."
                )
        else:
            # Use FileLoaderService for binary formats (PDF, DOCX, HTML)
            file_loader = FileLoaderService()
            extracted_text = file_loader.load(content_bytes, mime_type=mime_type)
        
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=422, 
                detail=f"Could not extract text from file '{filename}'. "
                       f"Ensure file is not empty and format is supported (TXT, MD, PDF, DOCX)."
            )
        
        text_length = len(extracted_text)
        logger.info(f"Extracted {text_length} characters from {filename}")
        
        # Parse extracted text
        parser = get_parser()
        
        if text_length > 50000:
            logger.warning(
                f"Large document detected ({text_length} chars). "
                "This may take 30+ seconds. Consider chunking."
            )
        
        result = parser.parse(extracted_text)
        
        # Add filename to metadata
        result["metadata"]["source_file"] = filename
        result["metadata"]["file_size_bytes"] = len(content_bytes)
        result["metadata"]["extracted_text_length"] = text_length
        
        # Add processing time warning if document is large
        if text_length > 10000:
            result["metadata"]["warning"] = (
                f"Large document ({text_length} chars) - "
                "processing may take 10-30s. Increase client timeout if needed."
            )
        
        logger.info(
            f"✅ Parsed {filename} into {len(result['nodes'])} nodes and "
            f"{len(result['edges'])} edges"
        )
        
        return ParseResponse(
            metadata=result["metadata"],
            nodes=result["nodes"],
            edges=result["edges"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File parsing failed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"File parsing failed: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status and model information
    """
    try:
        parser = get_parser()

        # Check if parser is initialized
        model_loaded = parser.nlp is not None

        status = "ready" if model_loaded else "error"

        logger.info(f"Health check: status={status}, model_loaded={model_loaded}")

        return HealthResponse(
            status=status,
            model_loaded=model_loaded,
            model_name=parser.model_name if model_loaded else "not_loaded",
        )

    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
