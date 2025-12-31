"""
Unit tests for Saga Orchestrator.

Tests cover transaction lifecycle, stuck transaction detection,
and PostgreSQL table creation functionality.

Phase: TN-100.4 - Saga Implementation
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncpg

from ingest_llm.core.saga_orchestrator import SagaOrchestrator


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


class TestSagaOrchestrator:
    """Test cases for SagaOrchestrator class."""

    def test_init_default_values(self):
        """Test SagaOrchestrator initialization with default values."""
        saga = SagaOrchestrator()
        # Default values come from Settings class, not environment variables
        assert saga.stuck_timeout_minutes == 5
        # Postgres DSN may be overridden by environment, so just check it's not empty
        assert saga.postgres_dsn is not None and len(saga.postgres_dsn) > 0

    def test_init_custom_values(self, mock_postgres_dsn):
        """Test SagaOrchestrator initialization with custom values."""
        saga = SagaOrchestrator(
            postgres_dsn=mock_postgres_dsn, stuck_timeout_minutes=10
        )
        assert saga.postgres_dsn == mock_postgres_dsn
        assert saga.stuck_timeout_minutes == 10

    @pytest.mark.asyncio
    async def test_create_saga_table(self, mock_postgres_dsn):
        """Test creating the ingest_transactions table."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            result = await saga.create_saga_table()

            assert result is True
            mock_connect.assert_called_once_with(dsn=mock_postgres_dsn)
            assert mock_conn.execute.call_count == 2  # CREATE TABLE and CREATE INDEX

    @pytest.mark.asyncio
    async def test_begin_transaction(self, sample_payload, mock_postgres_dsn):
        """Test beginning a transaction."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key: 1 if key == "id" else None
            mock_conn.fetchrow.return_value = mock_row
            mock_connect.return_value = mock_conn

            tx_id = await saga.begin_transaction(sample_payload)

            assert tx_id == 1
            mock_connect.assert_called_once_with(dsn=mock_postgres_dsn)
            mock_conn.fetchrow.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_transaction(self, sample_payload, mock_postgres_dsn):
        """Test committing a transaction."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            result = await saga.commit_transaction(sample_payload)

            assert result is True
            mock_connect.assert_called_once_with(dsn=mock_postgres_dsn)
            mock_conn.execute.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stuck_transactions(self, mock_postgres_dsn):
        """Test getting count of stuck transactions."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn, stuck_timeout_minutes=5)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key: 3 if key == "count" else None
            mock_conn.fetch.return_value = [mock_row]
            mock_connect.return_value = mock_conn

            stuck_count = await saga.get_stuck_transactions()

            assert stuck_count == 3
            mock_connect.assert_called_once_with(dsn=mock_postgres_dsn)
            mock_conn.fetch.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stuck_transactions_no_stuck(self, mock_postgres_dsn):
        """Test getting count of stuck transactions when none are stuck."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key: 0 if key == "count" else None
            mock_conn.fetch.return_value = [mock_row]
            mock_connect.return_value = mock_conn

            stuck_count = await saga.get_stuck_transactions()

            assert stuck_count == 0
            mock_connect.assert_called_once_with(dsn=mock_postgres_dsn)
            mock_conn.fetch.assert_called_once()
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_lifecycle(self, sample_payload, mock_postgres_dsn):
        """Test complete transaction lifecycle: PENDING → COMMITTED → no stuck."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            # Step 1: Begin transaction (PENDING state)
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key: 42 if key == "id" else None
            mock_conn.fetchrow.return_value = mock_row

            tx_id = await saga.begin_transaction(sample_payload)
            assert tx_id == 42
            assert mock_conn.fetchrow.call_count == 1

            # Step 2: Commit transaction (COMMITTED state)
            await saga.commit_transaction(sample_payload)
            assert mock_conn.execute.call_count == 1

            # Step 3: Check for stuck transactions (should be 0)
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key: 0 if key == "count" else None
            mock_conn.fetch.return_value = [mock_row]

            stuck_count = await saga.get_stuck_transactions()
            assert stuck_count == 0

    def test_commit_transaction_where_clause(self, sample_payload, mock_postgres_dsn):
        """Test that commit_transaction only updates PENDING transactions."""
        saga = SagaOrchestrator(postgres_dsn=mock_postgres_dsn)

        with patch("asyncpg.connect") as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn

            # We'll check the SQL query in the execute call
            import asyncio

            asyncio.run(saga.commit_transaction(sample_payload))

            # Verify the WHERE clause includes status check
            call_args = mock_conn.execute.call_args[0][0]
            assert "WHERE webhook_payload = $1 AND status = 'PENDING'" in call_args
