"""
Unit tests for Dead Letter Queue (DLQ) persistence.

Tests cover PostgreSQL connection, payload serialization, error handling,
and table creation functionality.

Phase: TN-LINEAR-06 - Webhook Ingestion
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncpg

from ingest_llm.core.dlq_handler import (
    create_dlq_table,
    write_to_dlq,
)


@pytest.fixture
def mock_postgres_dsn():
    """Provide a mock PostgreSQL DSN for testing."""
    return "postgresql://test:test@localhost:5432/test_db"


@pytest.fixture
def sample_payload():
    """Provide a sample Linear webhook payload."""
    return {
        "action": "IssueCreated",
        "data": {
            "id": "LIN-123",
            "title": "Test Issue",
            "description": "Test description",
        },
        "createdAt": "2025-12-29T12:00:00Z",
    }


@pytest.fixture
def sample_error_message():
    """Provide a sample error message."""
    return "Failed to process webhook: database connection error"


@pytest.fixture
def sample_correlation_id():
    """Provide a sample correlation ID."""
    return "test-correlation-id-12345"


class TestWriteToDlqSuccess:
    """Test successful DLQ write operations."""

    @pytest.mark.asyncio
    async def test_write_to_dlq_success(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Successfully writing to DLQ should return record ID."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-123")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Verify connection was established
        assert asyncpg.connect.call_count > 0
        assert asyncpg.connect.call_args[0][0] == mock_postgres_dsn

        # Verify cursor was created
        assert mock_connection.cursor.call_count > 0

        # Verify INSERT query was executed
        assert mock_cursor.execute.call_count > 0

        # Verify record ID was returned
        assert record_id == "test-record-id-123"

    @pytest.mark.asyncio
    async def test_write_to_dlq_serializes_payload(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Payload should be serialized to JSON before writing."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-456")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Get the INSERT query from execute call
        execute_call = mock_cursor.execute.call_args_list[0]
        query = execute_call[0][0]
        params = execute_call[0][1]

        # Verify payload is JSON serialized
        assert "payload" in query
        assert "error_message" in query
        assert "correlation_id" in query

        # Verify payload is JSON string
        payload_param = params[params.index(sample_payload)]
        assert isinstance(payload_param, str)
        # Verify it's valid JSON
        json.loads(payload_param)

    @pytest.mark.asyncio
    async def test_write_to_dlq_includes_correlation_id(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Correlation ID should be included in DLQ record."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-789")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Get the INSERT query from execute call
        execute_call = mock_cursor.execute.call_args_list[0]
        params = execute_call[0][1]

        # Verify correlation_id is in parameters
        assert sample_correlation_id in params


class TestWriteToDlqErrorHandling:
    """Test error handling in DLQ write operations."""

    @pytest.mark.asyncio
    async def test_write_to_dlq_connection_error(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Connection errors should be handled gracefully."""
        # Mock asyncpg to raise connection error
        with patch("asyncpg.connect", side_effect=asyncpg.PostgresConnectionError("Connection failed")):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should return None on error
        assert record_id is None

    @pytest.mark.asyncio
    async def test_write_to_dlq_cursor_error(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Cursor errors should be handled gracefully."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = asyncpg.PostgresError("Query failed")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should return None on error
        assert record_id is None

    @pytest.mark.asyncio
    async def test_write_to_dlq_serialization_error(
        self,
        mock_postgres_dsn,
        sample_error_message,
        sample_correlation_id,
    ):
        """Serialization errors should be handled gracefully."""
        # Create a payload that can't be serialized
        unserializable_payload = {"data": lambda x: x}

        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-999")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=unserializable_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should return None on error
        assert record_id is None


class TestWriteToDlqConnectionCleanup:
    """Test connection cleanup in DLQ write operations."""

    @pytest.mark.asyncio
    async def test_write_to_dlq_closes_connection(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Connection should be closed after writing."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-111")

        with patch("asyncpg.connect", return_value=mock_connection):
            await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Verify connection was closed
        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_to_dlq_closes_connection_on_error(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Connection should be closed even on error."""
        # Mock asyncpg to raise connection error
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = asyncpg.PostgresError("Query failed")

        with patch("asyncpg.connect", return_value=mock_connection):
            await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Verify connection was closed even on error
        mock_connection.close.assert_called_once()


class TestCreateDlqTableSuccess:
    """Test successful DLQ table creation."""

    @pytest.mark.asyncio
    async def test_create_dlq_table_success(self, mock_postgres_dsn):
        """Successfully creating DLQ table should return True."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = None

        with patch("asyncpg.connect", return_value=mock_connection):
            result = await create_dlq_table(postgres_dsn=mock_postgres_dsn)

        # Verify connection was established
        assert asyncpg.connect.call_count > 0
        assert asyncpg.connect.call_args[0][0] == mock_postgres_dsn

        # Verify cursor was created
        assert mock_connection.cursor.call_count > 0

        # Verify CREATE TABLE query was executed
        assert mock_cursor.execute.call_count > 0

        # Verify connection was closed
        mock_connection.close.assert_called_once()

        # Verify success
        assert result is True

    @pytest.mark.asyncio
    async def test_create_dlq_table_creates_correct_schema(self, mock_postgres_dsn):
        """DLQ table should have correct schema."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = None

        with patch("asyncpg.connect", return_value=mock_connection):
            await create_dlq_table(postgres_dsn=mock_postgres_dsn)

        # Get the CREATE TABLE query from execute call
        execute_calls = mock_cursor.execute.call_args_list

        # Verify table name is correct
        create_table_call = execute_calls[0]
        query = create_table_call[0][0]
        assert "ingest_failures" in query

        # Verify columns are correct
        assert "payload" in query
        assert "error_message" in query
        assert "correlation_id" in query
        assert "created_at" in query


class TestCreateDlqTableErrorHandling:
    """Test error handling in DLQ table creation."""

    @pytest.mark.asyncio
    async def test_create_dlq_table_connection_error(self, mock_postgres_dsn):
        """Connection errors should be handled gracefully."""
        # Mock asyncpg to raise connection error
        with patch("asyncpg.connect", side_effect=asyncpg.PostgresConnectionError("Connection failed")):
            result = await create_dlq_table(postgres_dsn=mock_postgres_dsn)

        # Should return False on error
        assert result is False

    @pytest.mark.asyncio
    async def test_create_dlq_table_query_error(self, mock_postgres_dsn):
        """Query errors should be handled gracefully."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = asyncpg.PostgresError("Query failed")

        with patch("asyncpg.connect", return_value=mock_connection):
            result = await create_dlq_table(postgres_dsn=mock_postgres_dsn)

        # Should return False on error
        assert result is False

    @pytest.mark.asyncio
    async def test_create_dlq_table_closes_connection_on_error(
        self,
        mock_postgres_dsn,
    ):
        """Connection should be closed even on error."""
        # Mock asyncpg to raise connection error
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = asyncpg.PostgresError("Query failed")

        with patch("asyncpg.connect", return_value=mock_connection):
            await create_dlq_table(postgres_dsn=mock_postgres_dsn)

        # Verify connection was closed even on error
        mock_connection.close.assert_called_once()


class TestDlqIntegration:
    """Integration tests for DLQ operations."""

    @pytest.mark.asyncio
    async def test_write_and_create_table_sequence(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_error_message,
        sample_correlation_id,
    ):
        """Table creation and write operations should work together."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-sequential")

        with patch("asyncpg.connect", return_value=mock_connection):
            # Create table first
            table_created = await create_dlq_table(postgres_dsn=mock_postgres_dsn)
            assert table_created is True

            # Reset mock for write operation
            mock_connection.reset_mock()

            # Then write to DLQ
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

            # Verify record ID was returned
            assert record_id == "test-record-id-sequential"


class TestDlqEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_write_to_dlq_empty_payload(
        self,
        mock_postgres_dsn,
        sample_error_message,
        sample_correlation_id,
    ):
        """Empty payload should be handled correctly."""
        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-empty")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload={},
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should succeed with empty payload
        assert record_id == "test-record-id-empty"

    @pytest.mark.asyncio
    async def test_write_to_dlq_large_payload(
        self,
        mock_postgres_dsn,
        sample_error_message,
        sample_correlation_id,
    ):
        """Large payloads should be handled correctly."""
        # Create a large payload
        large_payload = {"data": "x" * 10000}

        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-large")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=large_payload,
                error_message=sample_error_message,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should succeed with large payload
        assert record_id == "test-record-id-large"

    @pytest.mark.asyncio
    async def test_write_to_dlq_special_characters_in_error_message(
        self,
        mock_postgres_dsn,
        sample_payload,
        sample_correlation_id,
    ):
        """Special characters in error message should be handled correctly."""
        # Create error message with special characters
        special_error = "Error: 'test' \"quotes\" \n newline \t tab"

        # Mock asyncpg connection
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.return_value = MagicMock(insert_id="test-record-id-special")

        with patch("asyncpg.connect", return_value=mock_connection):
            record_id = await write_to_dlq(
                payload=sample_payload,
                error_message=special_error,
                correlation_id=sample_correlation_id,
                postgres_dsn=mock_postgres_dsn,
            )

        # Should succeed with special characters
        assert record_id == "test-record-id-special"
