import asyncio
import json
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from datetime import datetime
from ingest_llm_as.processors.conversation_ingestor import ConversationIngestor
from ingest_llm_as.database.session import get_async_session
from ingest_llm_as.db_models.raw_ingestion import RawIngestion
from sqlalchemy import select

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
            
            # Setup DB record using SQLAlchemy async session
            async for session in get_async_session():
                try:
                    # Cleanup existing test data
                    stmt = select(RawIngestion).where(
                        RawIngestion.raw_metadata['source_id'].astext == 'test-refactor-123'
                    )
                    result = await session.execute(stmt)
                    existing = result.scalars().all()
                    for record in existing:
                        await session.delete(record)
                    await session.commit()
                    
                    # Prepare test conversation data
                    raw_payload = {
                        "messages": [
                            {"role": "user", "content": "Hello, how are you?"},
                            {"role": "assistant", "content": "I am fine, thank you!"}
                        ],
                        "url": "http://test.com"
                    }
                    
                    # Insert test conversation record into raw_ingestions
                    test_record = RawIngestion(
                        ingestion_id=uuid4(),
                        source_type="conversation",
                        content_type="conversation",
                        raw_payload=raw_payload,
                        raw_metadata={
                            "source_id": "test-refactor-123",
                            "platform": "ChatGPT"
                        },
                        captured_at=datetime.utcnow(),
                        processed=False,
                    )
                    session.add(test_record)
                    await session.commit()
                    
                    # 4. Run Process
                    processed_count = await ingestor.process_pending_conversations()
                    
                    # 5. Assertions
                    assert processed_count == 1
                    assert mock_validate.called
                    
                    # Verify record is marked processed in DB
                    await session.refresh(test_record)
                    assert test_record.processed is True
                    assert test_record.last_error is None
                    
                    print("\n✅ TN-CORE-103 Verification Passed: Ingestor called validation API and updated DB.")
                    
                finally:
                    # Cleanup
                    stmt = select(RawIngestion).where(
                        RawIngestion.raw_metadata['source_id'].astext == 'test-refactor-123'
                    )
                    result = await session.execute(stmt)
                    existing = result.scalars().all()
                    for record in existing:
                        await session.delete(record)
                    await session.commit()

if __name__ == "__main__":
    asyncio.run(test_conversation_ingestor_refactor())
    print("\nTests completed.")
