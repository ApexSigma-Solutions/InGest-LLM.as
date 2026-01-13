import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from ingest_llm_as.config import get_settings
from ingest_llm_as.database.session import get_async_session
from ingest_llm_as.db_models.raw_ingestion import RawIngestion
from ingest_llm_as.services.llm_summarizer import LLMSummarizer
from ingest_llm_as.services.omegakg_client import OmegaKGClient
from ingest_llm_as.services.vectorizer import generate_content_embedding
from ingest_llm_as.models.knowledge_digest import create_conversation_digest

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_CONTEXT_MESSAGE_COUNT = 5  # Number of messages to include in embedding context

class ConversationIngestor:
    """
    Polls 'raw_ingestions' table for conversation records, summarizes content, and sends to OmegaKG validation API.
    
    REFACTORED: Uses unified raw_ingestions table with SQLAlchemy async sessions.
    No longer writes to Neo4j/pgvector directly.
    """
    def __init__(self):
        self.settings = get_settings()
        self.summarizer = LLMSummarizer()
        self.omegakg_client = OmegaKGClient()
        self.running = False

    async def start(self):
        """Start the ingestion loop."""
        self.running = True
        logger.info("Starting Conversation Ingestor loop...")
        while self.running:
            try:
                processed_count = await self.process_pending_conversations()
                if processed_count == 0:
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in ingestor loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False
        await self.omegakg_client.close()

    async def process_pending_conversations(self) -> int:
        """
        Fetch and process unprocessed conversations from the unified raw_ingestions table.
        Uses SQLAlchemy async session for database access.
        """
        # Use SQLAlchemy async session for unified data access
        async for session in get_async_session():
            try:
                # Query for unprocessed conversation records using FOR UPDATE SKIP LOCKED
                stmt = (
                    select(RawIngestion)
                    .where(RawIngestion.source_type == "conversation")
                    .where(RawIngestion.processed == False)
                    .limit(1)
                    .with_for_update(skip_locked=True)
                )
                
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()
                
                if not record:
                    return 0
                
                # Extract conversation metadata from raw_metadata
                raw_data = record.raw_payload
                source_id = record.raw_metadata.get('source_id', str(record.ingestion_id))
                platform = record.raw_metadata.get('platform', 'Unknown')
                captured_at = record.captured_at
                
                logger.info(f"Processing conversation: {source_id}")

                # 1. Summarize
                messages = raw_data.get('messages', [])
                message_count = len(messages)
                
                summary_content = await self.summarizer.summarize_conversation(
                    messages, 
                    context=f"Platform: {platform}, Date: {captured_at}"
                )
                
                # 2. Write to Obsidian Vault (Durable local backup)
                file_path = await self._write_to_vault(source_id, platform, summary_content, captured_at)
                
                # 3. Generate Embedding (Vector)
                conversation_text = f"Platform: {platform}\nSummary: {summary_content}\n"
                # Include context from first N messages
                for msg in messages[:EMBEDDING_CONTEXT_MESSAGE_COUNT]:
                    conversation_text += f"{msg.get('role', '')}: {msg.get('content', '')[:200]}\n"
                
                embedding = await generate_content_embedding(conversation_text, content_type="text")
                
                # 4. REFACTORED: Call OmegaKG Validation API Gateway
                # Instead of direct Neo4j/pgvector writes, we delegate to the Gateway.
                try:
                    digest = create_conversation_digest(
                        raw_payload=raw_data,
                        summary=summary_content,
                        vault_filepath=str(file_path),
                        source_id=source_id,
                        platform=platform,
                        message_count=message_count,
                        embedding=embedding,
                        captured_at=captured_at
                    )
                    
                    logger.debug(f"Submitting digest for {source_id} to OmegaKG...")
                    response = await self.omegakg_client.validate_and_store(digest.model_dump(mode="json"))
                    
                    status = response.get("status")
                    if status in ["accepted", "duplicate"]:
                        logger.info(f"OmegaKG {status} digest for {source_id}. IDs: neo4j={response.get('neo4j_node_id')}, vector={response.get('vector_id')}")
                        
                        # 5. Update Local Record (Mark Processed)
                        record.processed = True
                        record.processed_at = datetime.utcnow()
                        record.processing_attempts += 1
                        await session.commit()
                        
                        logger.info(f"Successfully processed {source_id}.")
                        return 1
                    else:
                        error_msg = response.get("message") or "Unknown validation error"
                        logger.warning(f"OmegaKG rejected digest for {source_id}: {error_msg}")
                        
                        # Mark as processed with error to avoid infinite loop
                        record.processed = True
                        record.processed_at = datetime.utcnow()
                        record.processing_attempts += 1
                        record.last_error = f"OmegaKG Rejection: {error_msg}"
                        await session.commit()
                        return 1
                        
                except Exception as e:
                    logger.error(f"Failed to submit digest to OmegaKG: {str(e)}")
                    # Increment attempts but keep processed = FALSE for retry
                    record.processing_attempts += 1
                    record.last_error = str(e)
                    await session.commit()
                    return 0  # Will retry on next poll
                    
            except Exception as e:
                logger.error(f"Error in process_pending_conversations: {e}", exc_info=True)
                await session.rollback()
                return 0

    async def _write_to_vault(self, hash_id: str, platform: str, content: str, date: datetime) -> Path:
        """Writes the summary to the Obsidian Vault."""
        vault_root = Path(self.settings.obsidian_vault_path)
        folder = vault_root / "AI_Conversations" / "Summaries"
        folder.mkdir(parents=True, exist_ok=True)
        
        # Clean safe filename
        safe_date = date.strftime("%Y-%m-%d")
        filename = f"{safe_date} - {platform} - {hash_id}.md"
        full_path = folder / filename

        # Add Metadata Frontmatter
        frontmatter = f"""---
id: {hash_id}
type: ai_conversation
platform: {platform}
date: {safe_date}
tags:
  - ai/conversation
  - source/{platform.lower().replace(' ', '_')}
---
"""
        final_file_content = frontmatter + content
        
        # Write file (sync IO is okay for now, or use aiofiles if high throughput needed)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(final_file_content)
            
        return full_path
