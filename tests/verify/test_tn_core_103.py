import asyncio
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from datetime import datetime
from ingest_llm_as.processors.conversation_ingestor import ConversationIngestor
import asyncpg

@pytest.mark.asyncio
async def test_conversation_ingestor_refactor():
    # 1. Setup Mock API Response
    mock_response = {
        "status": "accepted",
        "neo4j_node_id": "test-neo4j-id",
        "vector_id": 12345
    }
    
    # 2. Mock generate_content_embedding to avoid calling LM Studio
    with patch("ingest_llm_as.processors.conversation_ingestor.generate_content_embedding", return_value=[0.1]*768):
        # 3. Mock OmegaKGClient.validate_and_store
        with patch("ingest_llm_as.services.omegakg_client.OmegaKGClient.validate_and_store", return_value=mock_response) as mock_validate:
            
            ingestor = ConversationIngestor()
            
            # Setup DB record
            db_url = ingestor.settings.raw_db_url.replace("postgresql+asyncpg", "postgresql")
            conn = await asyncpg.connect(db_url)
            
            try:
                # Cleanup and insert test data
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS raw_conversations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        source_id VARCHAR(255) UNIQUE NOT NULL,
                        platform VARCHAR(50),
                        raw_payload JSONB NOT NULL,
                        captured_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        processed BOOLEAN NOT NULL DEFAULT FALSE,
                        processed_at TIMESTAMP,
                        processing_attempts INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT
                    )
                """)
                await conn.execute("DELETE FROM raw_conversations WHERE source_id = 'test-refactor-123'")
                
                raw_payload = {
                    "messages": [
                        {"role": "user", "content": "Hello, how are you?"},
                        {"role": "assistant", "content": "I am fine, thank you!"}
                    ],
                    "url": "http://test.com"
                }
                
                await conn.execute("""
                    INSERT INTO raw_conversations (source_id, platform, raw_payload, captured_at, processed)
                    VALUES ($1, $2, $3, $4, FALSE)
                """, 'test-refactor-123', 'ChatGPT', json.dumps(raw_payload), datetime.utcnow())
                
                # 4. Run Process
                processed_count = await ingestor.process_pending_conversations()
                
                # 5. Assertions
                assert processed_count == 1
                assert mock_validate.called
                
                # Verify record is marked processed in DB
                row = await conn.fetchrow("SELECT processed, last_error FROM raw_conversations WHERE source_id = 'test-refactor-123'")
                assert row['processed'] is True
                assert row['last_error'] is None
                
                print("\n✅ TN-CORE-103 Verification Passed: Ingestor called validation API and updated DB.")
                
            finally:
                await conn.execute("DELETE FROM raw_conversations WHERE source_id = 'test-refactor-123'")
                await conn.close()

if __name__ == "__main__":
    asyncio.run(test_conversation_ingestor_refactor())
    print("\nTests completed.")
