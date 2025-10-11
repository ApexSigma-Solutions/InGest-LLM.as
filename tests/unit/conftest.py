"""
InGest-LLM.as Unit Test Configuration

This module provides fixtures and configuration specifically for unit tests.
Unit tests focus on isolated components and functions without external dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any


@pytest.fixture(scope="function")
def mock_external_dependencies():
    """Mock all external dependencies for pure unit testing."""
    mocks = {}

    # Mock database operations
    mocks["db_session"] = MagicMock()
    mocks["db_session"].execute.return_value = MagicMock()
    mocks["db_session"].commit.return_value = None
    mocks["db_session"].rollback.return_value = None

    # Mock cache operations
    mocks["cache"] = MagicMock()
    mocks["cache"].get.return_value = None
    mocks["cache"].set.return_value = True

    # Mock vector store
    mocks["vector_store"] = MagicMock()
    mocks["vector_store"].search.return_value = []
    mocks["vector_store"].upsert.return_value = True

    # Mock LLM service
    mocks["llm"] = MagicMock()
    mocks["llm"].generate_response.return_value = "Mock response"
    mocks["llm"].generate_embedding.return_value = [0.1, 0.2, 0.3]

    # Apply patches
    with patch("app.database.get_session", return_value=mocks["db_session"]), \
         patch("app.cache.get_cache", return_value=mocks["cache"]), \
         patch("app.vector_store.get_client", return_value=mocks["vector_store"]), \
         patch("app.llm.get_service", return_value=mocks["llm"]):
        yield mocks


@pytest.fixture(scope="function")
def clean_test_data():
    """Provide clean test data structures."""
    return {
        "document": {
            "id": "unit-test-doc",
            "content": "Unit test content",
            "metadata": {"test": True},
            "embeddings": [0.1] * 384
        },
        "query": {
            "text": "unit test query",
            "filters": {},
            "top_k": 5
        },
        "user": {
            "id": "unit-test-user",
            "name": "Test User",
            "email": "test@example.com"
        }
    }


@pytest.fixture(scope="function")
def mock_config():
    """Mock configuration for unit tests."""
    config = MagicMock()
    config.database_url = "sqlite:///:memory:"
    config.redis_url = "redis://localhost:6379/1"
    config.qdrant_url = "http://localhost:6333"
    config.neo4j_uri = "bolt://localhost:7687"
    config.debug = True
    config.max_batch_size = 10
    config.embedding_dimension = 384
    return config