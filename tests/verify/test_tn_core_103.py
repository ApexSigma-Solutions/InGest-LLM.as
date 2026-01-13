import asyncio
import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from datetime import datetime
from uuid import uuid4
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
                # Generate unique test ID
                test_ingestion_id = uuid4()
                test_platform = "ChatGPT"
                
                # Prepare test data matching raw_ingestions schema
                raw_payload = {
                    "messages": [
                        {"role": "user", "content": "Hello, how are you?"},
                        {"role": "assistant", "content": "I am fine, thank you!"}
                    ],
                    "url": "http://test.com",
                    "platform": test_platform
                }
                
                raw_metadata = {
                    "platform": test_platform
                }
                
                # Clean up any existing test data
                await conn.execute("DELETE FROM raw_ingestions WHERE ingestion_id = $1", test_ingestion_id)
                
                # Insert test data into raw_ingestions table
                await conn.execute("""
                    INSERT INTO raw_ingestions 
                    (ingestion_id, source_type, raw_payload, raw_metadata, captured_at, processed)
                    VALUES ($1, $2, $3, $4, $5, FALSE)
                """, test_ingestion_id, 'conversation', json.dumps(raw_payload), json.dumps(raw_metadata), datetime.utcnow())
                
                # 4. Run Process
                processed_count = await ingestor.process_pending_conversations()
                
                # 5. Assertions
                assert processed_count == 1
                assert mock_validate.called
                
                # Verify record is marked processed in DB
                row = await conn.fetchrow("SELECT processed, last_error FROM raw_ingestions WHERE ingestion_id = $1", test_ingestion_id)
                assert row['processed'] is True
                assert row['last_error'] is None
                
                print("\n✅ TN-CORE-103 Verification Passed: Ingestor called validation API and updated DB.")
                
            finally:
                await conn.execute("DELETE FROM raw_ingestions WHERE ingestion_id = $1", test_ingestion_id)
                await conn.close()

if __name__ == "__main__":
    asyncio.run(test_conversation_ingestor_refactor())
    print("\nTests completed.")
