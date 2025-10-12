"""
InGest-LLM.as Integration Test Configuration

This module provides fixtures and configuration for integration tests.
Integration tests verify component interactions and external service integrations.
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import docker
import time
import requests


@pytest.fixture(scope="session")
def docker_client():
    """Provide Docker client for integration tests."""
    try:
        client = docker.from_env()
        yield client
    except docker.errors.DockerException:
        pytest.skip("Docker not available for integration tests")


@pytest.fixture(scope="session")
def integration_settings():
    """Provide integration test settings."""
    from src.ingest_llm_as.config import Settings
    settings = Settings()
    # Override with test-specific settings
    settings.database_url = "postgresql://test:test@localhost:5433/test_db"
    settings.redis_url = "redis://localhost:6380"
    settings.qdrant_url = "http://localhost:6334"
    settings.neo4j_uri = "bolt://localhost:7688"
    return settings


@pytest.fixture(scope="function", autouse=True)
async def setup_integration_services(docker_client):
    """Set up external services for integration testing."""
    services = {
        "postgres": {"port": 5433, "image": "postgres:15-alpine"},
        "redis": {"port": 6380, "image": "redis:7-alpine"},
        "qdrant": {"port": 6334, "image": "qdrant/qdrant:latest"},
        "neo4j": {"port": 7688, "image": "neo4j:5.15"}
    }

    containers = []

    # Start services
    for service_name, config in services.items():
        try:
            container = docker_client.containers.run(
                config["image"],
                detach=True,
                ports={f"{config['port']}/tcp": config["port"]},
                name=f"test-{service_name}",
                environment={"POSTGRES_PASSWORD": "test"} if service_name == "postgres" else {}
            )
            containers.append(container)

            # Wait for service to be ready
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    if service_name == "postgres":
                        # Test PostgreSQL connection
                        import psycopg2
                        conn = psycopg2.connect(
                            host="localhost",
                            port=config["port"],
                            user="postgres",
                            password="test",
                            database="postgres"
                        )
                        conn.close()
                        break
                    elif service_name == "redis":
                        import redis
                        r = redis.Redis(host="localhost", port=config["port"])
                        r.ping()
                        break
                    elif service_name == "qdrant":
                        response = requests.get(f"http://localhost:{config['port']}/healthz")
                        if response.status_code == 200:
                            break
                    elif service_name == "neo4j":
                        # Neo4j takes longer to start
                        time.sleep(2)
                        continue
                except Exception:
                    time.sleep(1)

            if attempt == max_attempts - 1:
                pytest.skip(f"Could not start {service_name} for integration tests")

        except Exception as e:
            pytest.skip(f"Failed to start {service_name}: {e}")

    yield

    # Cleanup
    for container in containers:
        try:
            container.stop()
            container.remove()
        except:
            pass


@pytest.fixture(scope="function")
async def integration_database():
    """Provide real database connection for integration tests."""
    import asyncpg
    import os

    # Set test database URL
    test_db_url = "postgresql://test:test@localhost:5433/test_db"

    # Create test database if it doesn't exist
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5433,
            user="postgres",
            password="test",
            database="postgres"
        )
        await conn.execute("CREATE DATABASE test_db")
        await conn.close()
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass

    # Connect to test database
    conn = await asyncpg.connect(test_db_url)

    # Create test tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS test_documents (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    yield conn

    # Cleanup
    await conn.execute("DROP TABLE IF EXISTS test_documents")
    await conn.close()


@pytest.fixture(scope="function")
async def integration_redis():
    """Provide real Redis connection for integration tests."""
    import redis.asyncio as redis

    r = redis.Redis(host="localhost", port=6380, db=1)
    yield r

    # Cleanup
    await r.flushdb()
    r.close()


@pytest.fixture(scope="function")
async def integration_qdrant():
    """Provide real Qdrant connection for integration tests."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6334)

    # Create test collection
    collection_name = "test_documents"
    try:
        client.delete_collection(collection_name)
    except:
        pass

    client.create_collection(
        collection_name=collection_name,
        vectors_config={"size": 384, "distance": "Cosine"}
    )

    yield client

    # Cleanup
    try:
        client.delete_collection(collection_name)
    except:
        pass


@pytest.fixture(scope="function")
def integration_sample_data():
    """Provide realistic sample data for integration tests."""
    return {
        "documents": [
            {
                "content": "This is a comprehensive integration test document about artificial intelligence and machine learning.",
                "metadata": {
                    "source": "integration_test",
                    "type": "article",
                    "tags": ["AI", "ML", "integration"],
                    "author": "Test Author",
                    "published_date": "2025-01-01"
                }
            },
            {
                "content": "Another document discussing natural language processing and its applications in modern software systems.",
                "metadata": {
                    "source": "integration_test",
                    "type": "research",
                    "tags": ["NLP", "software", "integration"],
                    "author": "Research Team",
                    "published_date": "2025-01-02"
                }
            }
        ],
        "queries": [
            {
                "text": "artificial intelligence machine learning",
                "expected_results": 1
            },
            {
                "text": "natural language processing software",
                "expected_results": 1
            },
            {
                "text": "nonexistent topic search",
                "expected_results": 0
            }
        ]
    }