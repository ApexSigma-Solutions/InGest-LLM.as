"""
InGest-LLM.as End-to-End Test Configuration

This module provides fixtures and configuration for end-to-end tests.
E2E tests simulate complete user workflows and system interactions.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import asyncio
import time
from fastapi.testclient import TestClient
import httpx


@pytest.fixture(scope="session")
def e2e_settings():
    """Provide end-to-end test settings."""
    from src.ingest_llm_as.config import Settings
    settings = Settings()
    # Use test database and services
    settings.database_url = "postgresql://test:test@localhost:5433/e2e_db"
    settings.redis_url = "redis://localhost:6380/2"
    settings.qdrant_url = "http://localhost:6334"
    settings.neo4j_uri = "bolt://localhost:7688"
    settings.debug = True
    return settings


@pytest.fixture(scope="session")
async def e2e_app(e2e_settings):
    """Create FastAPI test application."""
    from src.ingest_llm_as.main import app

    # Override settings for E2E tests
    from src.ingest_llm_as.config import get_settings
    original_get_settings = get_settings

    def mock_get_settings():
        return e2e_settings

    import src.ingest_llm_as.config as config_module
    config_module.get_settings = mock_get_settings

    yield app

    # Restore original settings
    config_module.get_settings = original_get_settings


@pytest.fixture(scope="session")
async def e2e_client(e2e_app):
    """Provide FastAPI test client."""
    from fastapi.testclient import TestClient
    client = TestClient(e2e_app)
    yield client


@pytest.fixture(scope="session")
async def e2e_http_client():
    """Provide HTTP client for external API calls in E2E tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="function", autouse=True)
async def e2e_database_setup():
    """Set up fresh database state for each E2E test."""
    # This would typically set up database schema and initial data
    # For now, we'll use mocks but structure it for real DB later
    yield
    # Cleanup after test


@pytest.fixture(scope="function")
def e2e_test_user():
    """Provide test user data for E2E scenarios."""
    return {
        "id": "e2e-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user",
        "preferences": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    }


@pytest.fixture(scope="function")
def e2e_test_documents():
    """Provide comprehensive test documents for E2E scenarios."""
    return [
        {
            "title": "Introduction to Artificial Intelligence",
            "content": """
            Artificial Intelligence (AI) represents a transformative technology that has revolutionized
            numerous industries. This comprehensive guide explores the fundamental concepts, current
            applications, and future implications of AI systems.

            From machine learning algorithms to neural networks, AI encompasses a wide range of
            technologies that enable computers to perform tasks that typically require human intelligence.
            """,
            "metadata": {
                "author": "Dr. Sarah Johnson",
                "category": "Technology",
                "tags": ["AI", "Machine Learning", "Technology"],
                "word_count": 284,
                "reading_time": 2,
                "source": "e2e_test",
                "published_date": "2025-01-15"
            }
        },
        {
            "title": "Machine Learning Best Practices",
            "content": """
            Implementing machine learning solutions requires careful consideration of data quality,
            model selection, and deployment strategies. This document outlines industry best practices
            for developing robust ML systems.

            Key considerations include data preprocessing, feature engineering, model validation,
            and monitoring in production environments.
            """,
            "metadata": {
                "author": "Prof. Michael Chen",
                "category": "Data Science",
                "tags": ["Machine Learning", "Best Practices", "Data Science"],
                "word_count": 198,
                "reading_time": 1,
                "source": "e2e_test",
                "published_date": "2025-01-20"
            }
        },
        {
            "title": "Natural Language Processing Applications",
            "content": """
            Natural Language Processing (NLP) has become increasingly important in modern applications.
            From chatbots to content analysis, NLP technologies enable computers to understand and
            generate human language.

            This article explores various NLP applications including sentiment analysis, text summarization,
            and language translation, with practical examples and implementation considerations.
            """,
            "metadata": {
                "author": "Dr. Emily Rodriguez",
                "category": "NLP",
                "tags": ["NLP", "Language Processing", "AI Applications"],
                "word_count": 245,
                "reading_time": 2,
                "source": "e2e_test",
                "published_date": "2025-01-25"
            }
        }
    ]


@pytest.fixture(scope="function")
def e2e_test_queries():
    """Provide comprehensive test queries for E2E scenarios."""
    return [
        {
            "query": "artificial intelligence fundamentals",
            "expected_results": 1,
            "filters": {"category": "Technology"},
            "description": "Search for AI fundamentals in technology category"
        },
        {
            "query": "machine learning best practices data science",
            "expected_results": 1,
            "filters": {"category": "Data Science"},
            "description": "Search for ML best practices in data science"
        },
        {
            "query": "natural language processing applications",
            "expected_results": 1,
            "filters": {"tags": ["NLP"]},
            "description": "Search for NLP applications with tag filter"
        },
        {
            "query": "quantum computing neural networks",
            "expected_results": 0,
            "filters": {},
            "description": "Search for non-existent content combination"
        },
        {
            "query": "AI ML technology applications",
            "expected_results": 2,
            "filters": {},
            "description": "Broad search matching multiple documents"
        }
    ]


@pytest.fixture(scope="function")
async def e2e_workflow_context(e2e_client, e2e_test_user, e2e_test_documents):
    """Set up complete E2E workflow context."""
    context = {
        "client": e2e_client,
        "user": e2e_test_user,
        "documents": e2e_test_documents,
        "ingested_ids": [],
        "session_id": f"e2e-session-{int(time.time())}"
    }

    # Simulate user authentication
    # This would typically involve API calls to auth service
    context["auth_token"] = "e2e-test-token-123"

    # Set up test data in external systems
    # This would typically involve setting up test state in databases/cache/vector stores

    yield context

    # Cleanup after test
    # This would typically clean up test data from all systems
    context["ingested_ids"].clear()