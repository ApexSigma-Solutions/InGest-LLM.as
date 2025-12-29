"""Unit tests for DLQ handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ingest_llm_as.core.dlq_handler import write_to_dlq, create_dlq_table


@pytest.mark.asyncio
@patch('src.ingest_llm_as.core.dlq_handler.asyncpg.connect')
async def test_write_to_dlq_success(mock_connect):
    """Test successful write to DLQ."""
    # Setup mocks
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=123)
    mock_conn.close = AsyncMock()
    mock_connect.return_value = mock_conn
    
    payload = {"action": "create", "data": {"id": "TEST-001"}}
    error_msg = "Processing failed"
    correlation_id = "test-correlation-id"
    postgres_dsn = "postgresql://test:test@localhost/test"
    
    result = await write_to_dlq(payload, error_msg, correlation_id, postgres_dsn)
    
    assert result == "123"
    mock_connect.assert_called_once_with(dsn=postgres_dsn)
    mock_conn.fetchval.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
@patch('src.ingest_llm_as.core.dlq_handler.asyncpg.connect')
async def test_write_to_dlq_connection_error(mock_connect):
    """Test DLQ write handles connection errors gracefully."""
    mock_connect.side_effect = Exception("Connection failed")
    
    payload = {"action": "create", "data": {"id": "TEST-001"}}
    error_msg = "Processing failed"
    correlation_id = "test-correlation-id"
    postgres_dsn = "postgresql://test:test@localhost/test"
    
    result = await write_to_dlq(payload, error_msg, correlation_id, postgres_dsn)
    
    # Should return None on error without raising
    assert result is None


@pytest.mark.asyncio
@patch('src.ingest_llm_as.core.dlq_handler.asyncpg.connect')
async def test_write_to_dlq_insert_error(mock_connect):
    """Test DLQ write handles insert errors gracefully."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(side_effect=Exception("Insert failed"))
    mock_conn.close = AsyncMock()
    mock_connect.return_value = mock_conn
    
    payload = {"action": "create", "data": {"id": "TEST-001"}}
    error_msg = "Processing failed"
    correlation_id = "test-correlation-id"
    postgres_dsn = "postgresql://test:test@localhost/test"
    
    result = await write_to_dlq(payload, error_msg, correlation_id, postgres_dsn)
    
    # Should return None on error without raising
    assert result is None
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
@patch('src.ingest_llm_as.core.dlq_handler.asyncpg.connect')
async def test_create_dlq_table_success(mock_connect):
    """Test successful DLQ table creation."""
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_connect.return_value = mock_conn
    
    postgres_dsn = "postgresql://test:test@localhost/test"
    result = await create_dlq_table(postgres_dsn)
    
    assert result is True
    mock_connect.assert_called_once_with(dsn=postgres_dsn)
    mock_conn.execute.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
@patch('src.ingest_llm_as.core.dlq_handler.asyncpg.connect')
async def test_create_dlq_table_error(mock_connect):
    """Test DLQ table creation handles errors gracefully."""
    mock_connect.side_effect = Exception("Connection failed")
    
    postgres_dsn = "postgresql://test:test@localhost/test"
    result = await create_dlq_table(postgres_dsn)
    
    assert result is False
