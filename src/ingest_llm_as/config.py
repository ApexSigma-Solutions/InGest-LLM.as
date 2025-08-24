"""
Configuration settings for InGest-LLM.as service.
"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    app_name: str = "InGest-LLM.as"
    app_version: str = "0.1.0"
    debug: bool = False
    hello: Optional[str] = None  # Development setting

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # memOS.as integration
    memos_base_url: str = "http://localhost:8091"
    memos_api_key: Optional[str] = None
    memos_timeout: int = 30

    # Processing limits
    max_content_size: int = 1_000_000  # 1MB
    default_chunk_size: int = 1000
    max_chunks_per_request: int = 100

    # Async processing
    enable_async_processing: bool = True
    async_queue_max_size: int = 1000

    # LM Studio integration for embeddings
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_api_key: Optional[str] = None
    lm_studio_timeout: int = 30
    lm_studio_enabled: bool = True
    
    # Embedding configuration
    embedding_enabled: bool = True
    embedding_batch_size: int = 10
    embedding_dimension: int = 768  # Default for nomic-embed models

    # Observability
    jaeger_endpoint: str = "http://devenviro_jaeger:14268/api/traces"
    log_level: str = "INFO"
    log_json: bool = True
    environment: str = "docker"
    
    # Langfuse observability integration
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_api_key_public: Optional[str] = None  # Alternative naming
    langfuse_api_key_secret: Optional[str] = None  # Alternative naming

    class Config:
        env_file = ".env"
        env_prefix = "INGEST_"


# Global settings instance
settings = Settings()
