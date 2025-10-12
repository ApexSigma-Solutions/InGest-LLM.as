"""
Configuration settings for InGest-LLM.as service.
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from apexsigma_core.vault import get_secret


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    app_name: str = "InGest-LLM.as"
    app_version: str = "0.1.0"
    debug: bool = False
    hello: Optional[str] = None  # Development setting
    enable_vault: bool = False  # Enable Vault secret fetching

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Service endpoints integration - UPDATED FOR DOCKER NETWORKING
    base_url: str = "http://localhost:8000"
    memos_base_url: str = "http://memos:8090"  # Use service name, not localhost
    tools_base_url: str = "http://localhost:8003"
    agent_bridge_url: str = "http://localhost:8100"
    memos_api_key: Optional[str] = None
    memos_timeout: int = 30

    # Database configuration - UPDATED FOR DOCKER NETWORKING
    postgres_host: str = "apexsigma_postgres"
    postgres_port: str = "5432"
    postgres_user: str = "apexsigma_user"
    postgres_password: Optional[str] = None
    postgres_db: str = "apexsigma_db"  # Updated to canonical database name
    redis_host: str = "apexsigma_redis"
    redis_port: str = "6379"
    neo4j_host: str = "apexsigma_neo4j"
    neo4j_port: str = "7687"
    qdrant_host: str = "apexsigma_qdrant"
    qdrant_port: str = "6333"

    # Observability endpoints - UPDATED FOR DOCKER NETWORKING
    prometheus_url: str = "http://prometheus:9090"
    grafana_url: str = "http://localhost:3001"
    jaeger_endpoint: str = "http://jaeger:14268/api/traces"

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
    log_level: str = "INFO"
    log_json: bool = True
    environment: str = "docker"

    # Langfuse observability integration
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="INGEST_",
        extra="ignore",
        # CRITICAL: Force reload on every access to prevent caching
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )

    @field_validator("postgres_password", mode="before")
    @classmethod
    def get_postgres_password(cls, v: Optional[str]) -> Optional[str]:
        """Fetch PostgreSQL password from Vault if not provided and Vault is enabled."""
        if v is None or v == "your_secure_postgres_password_here":
            if os.environ.get("ENABLE_VAULT", "").lower() in ("true", "1", "yes"):
                try:
                    return get_secret("services/ingest/database", "postgres_password")
                except Exception:  # noqa: BLE001 - Catching broad exception for external vault library
                    return None
        return v

    @field_validator("memos_api_key", mode="before")
    @classmethod
    def get_memos_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Fetch Memos API key from Vault if not provided and Vault is enabled."""
        if v is None:
            if os.environ.get("ENABLE_VAULT", "").lower() in ("true", "1", "yes"):
                try:
                    return get_secret("services/ingest/api", "memos_api_key")
                except Exception:  # noqa: BLE001 - Catching broad exception for external vault library
                    return None
        return v

    @field_validator("lm_studio_api_key", mode="before")
    @classmethod
    def get_lm_studio_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Fetch LM Studio API key from Vault if not provided and Vault is enabled."""
        if v is None:
            if os.environ.get("ENABLE_VAULT", "").lower() in ("true", "1", "yes"):
                try:
                    return get_secret("services/ingest/llm", "lm_studio_api_key")
                except Exception:  # noqa: BLE001 - Catching broad exception for external vault library
                    return None
        return v

    @field_validator("langfuse_public_key", mode="before")
    @classmethod
    def get_langfuse_public_key(cls, v: Optional[str]) -> Optional[str]:
        """Fetch Langfuse public key from Vault if not provided and Vault is enabled."""
        if v is None:
            if os.environ.get("ENABLE_VAULT", "").lower() in ("true", "1", "yes"):
                try:
                    return get_secret("services/ingest/observability", "langfuse_public_key")
                except Exception:  # noqa: BLE001 - Catching broad exception for external vault library
                    return None
        return v

    @field_validator("langfuse_secret_key", mode="before")
    @classmethod
    def get_langfuse_secret_key(cls, v: Optional[str]) -> Optional[str]:
        """Fetch Langfuse secret key from Vault if not provided and Vault is enabled."""
        if v is None:
            if os.environ.get("ENABLE_VAULT", "").lower() in ("true", "1", "yes"):
                try:
                    return get_secret("services/ingest/observability", "langfuse_secret_key")
                except Exception:  # noqa: BLE001 - Catching broad exception for external vault library
                    return None
        return v


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
