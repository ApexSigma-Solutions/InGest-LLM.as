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

    class Config:
        env_file = ".env"
        env_prefix = "INGEST_"


# Global settings instance
settings = Settings()
