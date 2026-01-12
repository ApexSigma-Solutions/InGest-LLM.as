"""
Graph Parser API Endpoint for CortexBridge InGest-LLMs Engine.

Provides REST API endpoint for parsing text into Knowledge Graphs
using DocumentParser with Spacy Transformers and NLTK.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ingest_llm_as.parsers.document_parser import DocumentParser

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
