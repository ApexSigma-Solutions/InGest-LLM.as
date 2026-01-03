import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

import asyncpg

from ingest_llm_as.config import get_settings
from ingest_llm_as.services.llm_summarizer import LLMSummarizer
from ingest_llm_as.services.neo4j_service import Neo4jService
from ingest_llm_as.services.vectorizer import generate_content_embedding

logger = logging.getLogger(__name__)

class ConversationIngestor:
    """
    Polls 'raw_conversations' table, summarizes content, and ingests into Vault & Graph.
    """
    def __init__(self):
        self.settings = get_settings()
        self.summarizer = LLMSummarizer()
        self.neo4j_service = Neo4jService()
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
                logger.error(f"Error in ingestor loop: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False
        self.neo4j_service.close()

    async def process_pending_conversations(self) -> int:
        """
        Fetch and process unprocessed conversations.
        """
        conn = await asyncpg.connect(self.settings.raw_db_url.replace("postgresql+asyncpg", "postgresql"))
        
        try:
            row = await conn.fetchrow("""
                SELECT id, source_id, platform, raw_payload, captured_at 
                FROM raw_conversations 
                WHERE processed = FALSE 
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """)

            if not row:
                return 0

            record_id = row['id']
            source_id = row['source_id']
            raw_data = json.loads(row['raw_payload'])
            platform = row['platform']
            captured_at = row['captured_at']
            
            logger.info(f"Processing conversation: {source_id}")

            # 1. Summarize
            messages = raw_data.get('messages', [])
            message_count = len(messages)
            
            summary_content = await self.summarizer.summarize_conversation(
                messages, 
                context=f"Platform: {platform}, Date: {captured_at}"
            )
            
            # 2. Write to Obsidian
            file_path = await self._write_to_vault(source_id, platform, summary_content, captured_at)
            
            # 3. Generate Embedding (Vector)
            # Combine content for embedding: platform + summary + first few messages
            conversation_text = f"Platform: {platform}\nSummary: {summary_content}\n"
            for msg in messages[:5]: # Include context from first 5 msgs
                conversation_text += f"{msg.get('role', '')}: {msg.get('content', '')}\n"
            
            embedding = await generate_content_embedding(conversation_text, content_type="text")
            
            # 4. Write to Neo4j (Graph)
            # Extract URL if available
            url = raw_data.get('url')
            
            node_id = self.neo4j_service.create_chat_session(
                source_id=source_id,
                platform=platform,
                filepath=str(file_path),
                message_count=message_count,
                url=url
            )
            logger.info(f"Created Neo4j Node: {node_id}")

            # 5. Update Record (Mark Processed + Save Embedding)
            if embedding:
                # asyncpg requires native list for vector input if pgvector is used, 
                # but usually string representation works like '[1,2,3]'
                # Let's try passing string format which pgvector accepts
                embedding_str = str(embedding)
                await conn.execute("""
                    UPDATE raw_conversations 
                    SET processed = TRUE, 
                        processed_at = NOW(),
                        embedding = $2
                    WHERE id = $1
                """, record_id, embedding_str)
            else:
                await conn.execute("""
                    UPDATE raw_conversations 
                    SET processed = TRUE, processed_at = NOW() 
                    WHERE id = $1
                """, record_id)
            
            logger.info(f"Successfully processed {source_id}.")
            return 1

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
