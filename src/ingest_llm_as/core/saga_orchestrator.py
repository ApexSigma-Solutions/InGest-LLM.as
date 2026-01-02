import asyncpg
import json
import os
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_dsn: str = "postgresql://user:pass@postgres:5432/omega"
    saga_stuck_timeout_minutes: int = 5


settings = Settings()


class SagaOrchestrator:
    def __init__(self, postgres_dsn: Optional[str] = None, stuck_timeout_minutes: Optional[int] = None):
        self.postgres_dsn = postgres_dsn or settings.postgres_dsn
        self.stuck_timeout_minutes = stuck_timeout_minutes or settings.saga_stuck_timeout_minutes

    async def create_saga_table(self) -> bool:
        """Create ingest_transactions table if it doesn't exist."""
        conn = await asyncpg.connect(dsn=self.postgres_dsn)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_transactions (
                id SERIAL PRIMARY KEY,
                webhook_payload JSONB NOT NULL,
                status VARCHAR(20) CHECK (status IN ('PENDING', 'COMMITTED', 'FAILED')),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_transactions
            ON ingest_transactions(created_at)
            WHERE status = 'PENDING'
        """)
        await conn.close()
        return True

    async def begin_transaction(self, payload: Dict[str, Any]) -> int:
        """Insert a PENDING transaction record."""
        conn = await asyncpg.connect(dsn=self.postgres_dsn)
        row = await conn.fetchrow(
            "INSERT INTO ingest_transactions (webhook_payload, status) VALUES ($1, 'PENDING') RETURNING id",
            json.dumps(payload)
        )
        await conn.close()
        return row['id']

    async def commit_transaction(self, payload: Dict[str, Any]) -> bool:
        """Update transaction status to COMMITTED."""
        conn = await asyncpg.connect(dsn=self.postgres_dsn)
        await conn.execute(
            "UPDATE ingest_transactions SET status = 'COMMITTED', updated_at = NOW() WHERE webhook_payload = $1 AND status = 'PENDING'",
            json.dumps(payload)
        )
        await conn.close()
        return True

    async def get_stuck_transactions(self) -> int:
        """Count transactions stuck in PENDING state for > stuck_timeout_minutes."""
        conn = await asyncpg.connect(dsn=self.postgres_dsn)
        rows = await conn.fetch(
            "SELECT COUNT(*) as count FROM ingest_transactions WHERE status = 'PENDING' AND created_at < NOW() - INTERVAL '{} minutes'".format(self.stuck_timeout_minutes)
        )
        await conn.close()
        return rows[0]['count']
