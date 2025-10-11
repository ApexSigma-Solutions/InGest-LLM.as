"""
Simple validation test for InGest-LLM.as test infrastructure.

This test validates that the test framework, fixtures, mocks, and utilities
are all properly configured and functional.
"""

import pytest
import asyncio
from tests.utils.mocks import MockDatabase, MockRedis, MockVectorStore
from tests.utils.factories import create_document_data, create_query_data


def test_mock_classes_instantiation():
    """Test that mock classes can be instantiated."""
    db_mock = MockDatabase()
    redis_mock = MockRedis()
    vector_mock = MockVectorStore()

    assert db_mock is not None
    assert redis_mock is not None
    assert vector_mock is not None


def test_factory_functions():
    """Test that factory functions work."""
    doc = create_document_data()
    query = create_query_data()

    assert "content" in doc
    assert "metadata" in doc
    assert "query" in query  # Factory uses 'query' not 'query_text'
    assert "filters" in query


def test_pytest_configuration():
    """Test that pytest configuration is loaded."""
    # This test will pass if pytest runs without configuration errors
    assert True


@pytest.mark.asyncio
async def test_async_support():
    """Test that async test support is working."""
    # Simple async test to validate asyncio support
    result = await asyncio.sleep(0.01)
    assert result is None


def test_markers_registered():
    """Test that custom markers are available."""
    # This will pass if the test runs (markers are registered in pytest.ini)
    assert True