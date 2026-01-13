import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

import asyncpg

from ingest_llm_as.config import get_settings
from ingest_llm_as.services.llm_summarizer import LLMSummarizer
from ingest_llm_as.services.omegakg_client import OmegaKGClient
from ingest_llm_as.services.vectorizer import generate_content_embedding
from ingest_llm_as.models.knowledge_digest import create_conversation_digest

logger = logging.getLogger(__name__)

class ConversationIngestor:
    """
    Polls 'raw_ingestions' table for conversation records, summarizes content, and sends to OmegaKG validation API.
    
    REFACTORED: No longer writes to Neo4j/pgvector directly.
    Uses the migration-managed 'raw_ingestions' table instead of 'raw_conversations'.
    """
    def __init__(self):
        self.settings = get_settings()
        self.summarizer = LLMSummarizer()
        self.omegakg_client = OmegaKGClient()
        self.running = False
        self.db_url = self.settings.raw_db_url

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
        Fetch and process unprocessed conversations from raw_ingestions table.
        Filters for source_type='conversation' or similar conversation-related types.
        """
        # asyncpg connection for polling
        conn = await asyncpg.connect(self.settings.raw_db_url.replace("postgresql+asyncpg", "postgresql"))
        
        try:
            row = await conn.fetchrow("""
                SELECT id, ingestion_id, source_type, raw_payload, raw_metadata, captured_at 
                FROM raw_ingestions 
                WHERE processed = FALSE 
                AND source_type = 'conversation'
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """)

            if not row:
                return 0

            record_id = row['id']
            ingestion_id = row['ingestion_id']
            # asyncpg automatically deserializes JSONB columns to Python dicts
            raw_data = row['raw_payload']
            raw_metadata = row['raw_metadata'] or {}
            source_type = row['source_type']
            captured_at = row['captured_at']
            
            # Extract platform from metadata or raw_payload
            platform = raw_metadata.get('platform') or raw_data.get('platform', 'Unknown')
            source_id = str(ingestion_id)  # Use ingestion_id as source_id
            
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
            for msg in messages[:5]: # Include context from first 5 msgs
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
                    await conn.execute("""
                        UPDATE raw_ingestions 
                        SET processed = TRUE, 
                            processed_at = NOW(),
                            processing_attempts = processing_attempts + 1
                        WHERE id = $1
                    """, record_id)
                    
                    logger.info(f"Successfully processed {source_id}.")
                    return 1
                else:
                    error_msg = response.get("message") or "Unknown validation error"
                    logger.warning(f"OmegaKG rejected digest for {source_id}: {error_msg}")
                    
                    # Mark as processed with error to avoid infinite loop
                    await conn.execute("""
                        UPDATE raw_ingestions 
                        SET processed = TRUE, 
                            processed_at = NOW(),
                            processing_attempts = processing_attempts + 1,
                            last_error = $2
                        WHERE id = $1
                    """, record_id, f"OmegaKG Rejection: {error_msg}")
                    return 1
                    
            except Exception as e:
                logger.error(f"Failed to submit digest to OmegaKG: {str(e)}")
                # Increment attempts but keep processed = FALSE for retry
                await conn.execute("""
                    UPDATE raw_ingestions 
                    SET processing_attempts = processing_attempts + 1,
                        last_error = $2
                    WHERE id = $1
                """, record_id, str(e))
                return 0 # Will retry on next poll

        finally:
            await conn.close()

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
