"""
Pydantic models for the InGest-LLM.as ingestion pipeline.

This module defines the data models used for:
- Ingestion requests and responses
- Integration with memOS.as
- Validation and error handling
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class ContentType(str, Enum):
    """Supported content types for ingestion."""

    TEXT = "text"
    CODE = "code"
    DOCUMENTATION = "documentation"
    MARKDOWN = "markdown"
    JSON = "json"


class SourceType(str, Enum):
    """Source types for ingested content."""

    MANUAL = "manual"
    API = "api"
    UPLOAD = "upload"
    WEB_SCRAPE = "web_scrape"
    REPOSITORY = "repository"


class IngestionMetadata(BaseModel):
    """Metadata associated with ingested content."""

    source: SourceType
    content_type: ContentType
    source_url: Optional[str] = Field(
        None, description="Original URL or path if applicable"
    )
    author: Optional[str] = Field(None, description="Content author if known")
    title: Optional[str] = Field(None, description="Content title or identifier")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator("tags")
    def validate_tags(cls, v):
        """Ensure tags are non-empty strings."""
        return [tag.strip() for tag in v if tag and tag.strip()]


class IngestionRequest(BaseModel):
    """Request model for text ingestion."""

    content: str = Field(
        ..., min_length=1, max_length=1_000_000, description="Content to ingest"
    )
    metadata: IngestionMetadata
    chunk_size: Optional[int] = Field(
        None, ge=100, le=10000, description="Optional chunking size"
    )
    process_async: bool = Field(False, description="Whether to process asynchronously")

    @validator("content")
    def validate_content(cls, v):
        """Ensure content is not empty after stripping."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Content cannot be empty or whitespace only")
        return stripped


class MemoryTier(str, Enum):
    """Memory tiers in memOS.as."""

    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryStorageRequest(BaseModel):
    """Request model for storing data in memOS.as memory system."""

    content: str
    memory_tier: MemoryTier
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    relationships: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryStorageResponse(BaseModel):
    """Response from memOS.as memory storage."""

    memory_id: UUID
    memory_tier: MemoryTier
    status: str
    created_at: datetime


class ProcessingStatus(str, Enum):
    """Status of ingestion processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionResult(BaseModel):
    """Individual ingestion result for content chunk."""

    chunk_id: UUID = Field(default_factory=uuid4)
    memory_id: Optional[UUID] = None
    memory_tier: MemoryTier
    content_hash: str
    chunk_size: int
    status: ProcessingStatus
    error_message: Optional[str] = None


class IngestionResponse(BaseModel):
    """Response model for ingestion requests."""

    ingestion_id: UUID = Field(default_factory=uuid4)
    status: ProcessingStatus
    total_chunks: int = Field(ge=1)
    results: List[IngestionResult] = Field(default_factory=list)
    processing_time_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = Field(default="Ingestion initiated successfully")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class ValidationError(BaseModel):
    """Validation error details."""

    field: str
    message: str
    value: Any = None


class IngestionError(BaseModel):
    """Error response for ingestion failures."""

    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    validation_errors: List[ValidationError] = Field(default_factory=list)
    ingestion_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: str}


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "ok"
    service: str = "InGest-LLM.as"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    metrics_enabled: Optional[bool] = None
    tracing_enabled: Optional[bool] = None
    logging_structured: Optional[bool] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
