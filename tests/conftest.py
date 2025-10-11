"""
InGest-LLM.as Test Configuration and Shared Fixtures

This module provides shared test fixtures and configuration for all test types
(unit, integration, e2e) in the InGest-LLM service.
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os
from pathlib import Path

# Import service modules for testing
try:
    from app.main import app
    from app.core.config import Settings
    from app.services.llm_service import LLMService
    from app.services.embedding_service import EmbeddingService
    from app.services.vector_store import VectorStoreService
except ImportError:
    # Handle case where modules aren't available during test discovery
    app = None
    Settings = None
    LLMService = None
    EmbeddingService = None
    VectorStoreService = None


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def test_settings():
    """Provide test configuration settings."""
    if Settings:
        # Override settings for testing
        settings = Settings()
        settings.database_url = "sqlite:///./test.db"
        settings.redis_url = "redis://localhost:6379/1"
        settings.qdrant_url = "http://localhost:6333"
        settings.neo4j_uri = "bolt://localhost:7687"
        settings.debug = True
        return settings
    return MagicMock()


@pytest.fixture(scope="function")
async def mock_database():
    """Mock database session for testing."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.execute = AsyncMock(return_value=AsyncMock())
    mock_session.scalars = AsyncMock(return_value=AsyncMock())

    with patch("app.database.get_db_session", return_value=mock_session):
        yield mock_session


@pytest.fixture(scope="function")
async def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=b"test_value")
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.exists = AsyncMock(return_value=True)
    mock_redis.expire = AsyncMock(return_value=True)

    with patch("app.cache.redis_client", mock_redis):
        yield mock_redis


@pytest.fixture(scope="function")
async def mock_qdrant():
    """Mock Qdrant vector store for testing."""
    mock_client = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])
    mock_client.upsert = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=True)
    mock_client.scroll = AsyncMock(return_value=([], None))

    with patch("app.vector_store.qdrant_client", mock_client):
        yield mock_client


@pytest.fixture(scope="function")
async def mock_llm_service():
    """Mock LLM service for testing."""
    if LLMService:
        mock_service = AsyncMock(spec=LLMService)
        mock_service.generate_response = AsyncMock(return_value="Mock LLM response")
        mock_service.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_service.summarize_text = AsyncMock(return_value="Mock summary")

        with patch("app.services.llm_service.LLMService", return_value=mock_service):
            yield mock_service
    else:
        yield AsyncMock()


@pytest.fixture(scope="function")
async def mock_embedding_service():
    """Mock embedding service for testing."""
    if EmbeddingService:
        mock_service = AsyncMock(spec=EmbeddingService)
        mock_service.encode_text = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
        mock_service.encode_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_service.get_dimension = AsyncMock(return_value=384)

        with patch("app.services.embedding_service.EmbeddingService", return_value=mock_service):
            yield mock_service
    else:
        yield AsyncMock()


@pytest.fixture(scope="function")
def sample_document_data():
    """Provide sample document data for testing."""
    return {
        "id": "test-doc-123",
        "content": "This is a test document for ingestion testing.",
        "metadata": {
            "source": "test",
            "type": "text",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "embeddings": [0.1, 0.2, 0.3] * 128  # 384 dimensions
    }


@pytest.fixture(scope="function")
def sample_batch_documents():
    """Provide sample batch of documents for testing."""
    return [
        {
            "id": f"test-doc-{i}",
            "content": f"This is test document {i} for batch ingestion testing.",
            "metadata": {
                "source": "test_batch",
                "type": "text",
                "batch_id": "batch-123",
                "timestamp": "2025-01-01T00:00:00Z"
            },
            "embeddings": [0.1 * i, 0.2 * i, 0.3 * i] * 128
        }
        for i in range(1, 6)
    ]


@pytest.fixture(scope="function")
def sample_query_data():
    """Provide sample query data for testing."""
    return {
        "query": "What is the meaning of life?",
        "top_k": 5,
        "filters": {
            "source": "test",
            "type": "text"
        },
        "query_embedding": [0.1, 0.2, 0.3] * 128
    }


@pytest.fixture(scope="function")
async def mock_http_client():
    """Mock HTTP client for external API calls."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.put = AsyncMock()
    mock_client.delete = AsyncMock()

    # Configure default responses
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"status": "success"})
    mock_response.text = AsyncMock(return_value="success")

    mock_client.get.return_value = mock_response
    mock_client.post.return_value = mock_response

    with patch("httpx.AsyncClient", return_value=mock_client):
        yield mock_client


@pytest.fixture(scope="function")
def mock_langfuse():
    """Mock Langfuse for observability testing."""
    mock_client = MagicMock()
    mock_client.trace = MagicMock(return_value=MagicMock())
    mock_client.score = MagicMock()
    mock_client.flush = MagicMock()

    with patch("app.observability.langfuse_client", mock_client):
        yield mock_client


@pytest.fixture(scope="session")
def test_logger():
    """Provide a test logger instance."""
    import structlog
    return structlog.get_logger("test")