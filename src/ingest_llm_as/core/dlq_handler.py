"""Dead Letter Queue (DLQ) handler for failed webhook processing."""

import json
from typing import Dict, Any, Optional
import asyncpg


async def create_dlq_table(postgres_dsn: str) -> bool:
    """
    Create the DLQ table if it doesn't exist.
    
    Args:
        postgres_dsn: PostgreSQL connection string
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = await asyncpg.connect(dsn=postgres_dsn)
        try:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ingest_failures (
                    id SERIAL PRIMARY KEY,
                    payload JSONB NOT NULL,
                    error_message TEXT NOT NULL,
                    correlation_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            return True
        finally:
            await conn.close()
    except Exception:
        return False


async def write_to_dlq(
    payload: Dict[str, Any],
    error_message: str,
    correlation_id: str,
    postgres_dsn: str
) -> Optional[str]:
    """
    Write failed payload to dead letter queue.
    
    Args:
        payload: The webhook payload that failed processing
        error_message: Error description
        correlation_id: Request correlation ID for tracing
        postgres_dsn: PostgreSQL connection string
        
    Returns:
        Record ID if successful, None otherwise
    """
    try:
        conn = await asyncpg.connect(dsn=postgres_dsn)
        try:
            record_id = await conn.fetchval(
                """
                INSERT INTO ingest_failures 
                (payload, error_message, correlation_id, created_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
                """,
                json.dumps(payload),
                error_message,
                correlation_id
            )
            return str(record_id)
        finally:
            await conn.close()
    except Exception as e:
        # Log error but don't raise - DLQ failure shouldn't crash the service
        print(f"Failed to write to DLQ: {e}")
        return None
