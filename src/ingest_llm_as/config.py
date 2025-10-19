"""
Configuration settings for InGest-LLM.as service.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from apexsigma_core.vault import get_secret


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    app_name: str = Field(default="InGest-LLM.as", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    hello: Optional[str] = Field(default=None, description="Development setting")

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Service endpoints integration - UPDATED FOR DOCKER NETWORKING
    base_url: str = Field(default="http://localhost:8000", description="Base URL for this service")
    memos_base_url: str = Field(default="http://memos:8090", description="memOS API URL")
    tools_base_url: str = Field(default="http://localhost:8003", description="Tools API URL")
    agent_bridge_url: str = Field(default="http://localhost:8100", description="Agent Bridge URL")
    memos_api_key: Optional[str] = Field(default=None, description="memOS API key")
    memos_timeout: int = Field(default=30, description="memOS API timeout in seconds")

    # Database configuration - UPDATED FOR DOCKER NETWORKING
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="memos", description="PostgreSQL username")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL password")
    postgres_db: str = Field(default="memos", description="PostgreSQL database name")
    
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    
    neo4j_host: str = Field(default="neo4j", description="Neo4j host")
    neo4j_port: int = Field(default=7687, description="Neo4j Bolt port")
    
    qdrant_host: str = Field(default="qdrant", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")

    # Observability endpoints - UPDATED FOR DOCKER NETWORKING
    prometheus_url: str = Field(default="http://prometheus:9090", description="Prometheus URL")
    grafana_url: str = Field(default="http://localhost:3001", description="Grafana URL")
    jaeger_endpoint: str = Field(default="http://jaeger:14268/api/traces", description="Jaeger tracing endpoint")

    # Processing limits
    max_content_size: int = Field(default=1_000_000, description="Max content size in bytes (1MB)")
    default_chunk_size: int = Field(default=1000, description="Default chunk size")
    max_chunks_per_request: int = Field(default=100, description="Max chunks per request")

    # Async processing
    enable_async_processing: bool = Field(default=True, description="Enable async processing")
    async_queue_max_size: int = Field(default=1000, description="Async queue max size")

    # LM Studio integration for embeddings
    lm_studio_base_url: str = Field(default="http://localhost:1234/v1", description="LM Studio API base URL")
    lm_studio_api_key: Optional[str] = Field(default=None, description="LM Studio API key")
    lm_studio_timeout: int = Field(default=30, description="LM Studio timeout in seconds")
    lm_studio_enabled: bool = Field(default=True, description="Enable LM Studio integration")

    # Embedding configuration
    embedding_enabled: bool = Field(default=True, description="Enable embedding generation")
    embedding_batch_size: int = Field(default=10, description="Embedding batch size")
    embedding_dimension: int = Field(default=768, description="Embedding dimension (default for nomic-embed)")

    # Observability
    log_level: str = Field(default="INFO", description="Log level")
    log_json: bool = Field(default=True, description="Use JSON logging")
    environment: str = Field(default="docker", description="Environment name")

    # Langfuse observability integration
    langfuse_public_key: Optional[str] = Field(default=None, description="Langfuse public key")
    langfuse_secret_key: Optional[str] = Field(default=None, description="Langfuse secret key")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse host URL")

    @field_validator("postgres_password", mode="before")
    @classmethod
    def get_postgres_password(cls, v):
        """Fetch PostgreSQL password from Vault if not provided."""
        if v is None:
            return get_secret("services/ingest-llm/database", "postgres_password")
        return v

    @field_validator("langfuse_public_key", mode="before")
    @classmethod
    def get_langfuse_public_key(cls, v):
        """Fetch Langfuse public key from Vault if not provided."""
        if v is None:
            return get_secret("services/ingest-llm/observability", "langfuse_public_key")
        return v

    @field_validator("langfuse_secret_key", mode="before")
    @classmethod
    def get_langfuse_secret_key(cls, v):
        """Fetch Langfuse secret key from Vault if not provided."""
        if v is None:
            return get_secret("services/ingest-llm/observability", "langfuse_secret_key")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INGEST_",
        extra="ignore",
        # CRITICAL: Force reload on every access to prevent caching
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


# CRITICAL: Dynamic settings loading function to prevent caching issues
def get_settings() -> Settings:
    """
    Get fresh settings instance with current environment variables.

    This function prevents the caching issues that occur when settings
    are loaded at module import time.
    """
    # Create a new instance which will reload from environment
    return Settings()


# For backward compatibility, provide a settings instance
# but use get_settings() for any new code
settings = get_settings()
