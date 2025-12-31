-- Initialize ingest-llm database schema
-- Create transaction tracking table for Saga orchestrator

CREATE TABLE IF NOT EXISTS ingest_transactions (
    id SERIAL PRIMARY KEY,
    webhook_payload JSONB NOT NULL,
    status VARCHAR(20) CHECK (status IN ('PENDING', 'COMMITTED', 'FAILED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for efficient querying of pending transactions
CREATE INDEX IF NOT EXISTS idx_pending_transactions 
ON ingest_transactions(created_at) 
WHERE status = 'PENDING';

-- Create index for payload-based lookups
CREATE INDEX IF NOT EXISTS idx_webhook_payload 
ON ingest_transactions USING GIN(webhook_payload);

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ingest_transactions TO omega_user;
-- GRANT USAGE, SELECT ON SEQUENCE ingest_transactions_id_seq TO omega_user;