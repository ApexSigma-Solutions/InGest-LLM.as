import asyncio
import logging
import json

import asyncpg
import httpx

from ingest_llm_as.config import get_settings
from ingest_llm_as.database.session import get_async_session
from ingest_llm_as.db_models.raw_ingestion import RawIngestion
from ingest_llm_as.services.llm_summarizer import LLMSummarizer

logger = logging.getLogger(__name__)


class ConversationIngestor:
    """
    Workhorse service: Polls 'raw_conversations' table, synthesizes content,
    and proposes knowledge to the OmegaKG Guardian.
    """

    def __init__(self):
        self.settings = get_settings()
        self.summarizer = LLMSummarizer()
        self.running = False

    async def start(self):
        """Start the ingestion loop."""
        self.running = True
        logger.info("Starting Conversation Ingestor (Workhorse) loop...")
        while self.running:
            try:
                processed_count = await self.process_pending_conversations()
                if processed_count == 0:
                    await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Error in ingestor loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False

    async def process_pending_conversations(self) -> int:
        """
        Fetch and process unprocessed conversations from raw_ingestions table.
        Filters for source_type='conversation' or similar conversation-related types.
        """
        db_url = self.settings.raw_db_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        conn = await asyncpg.connect(db_url)

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

            record_id = row["id"]
            source_id = row["source_id"]
            raw_data = json.loads(row["raw_payload"])
            platform = row["platform"]
            captured_at = row["captured_at"]

            logger.info(f"Processing conversation: {source_id}")

            # 1. Summarize (Heavy Lifting)
            messages = raw_data.get("messages", [])
            summary_content = await self.summarizer.summarize_conversation(
                messages, context=f"Platform: {platform}, Date: {captured_at}"
            )

            # 2. Prep Knowledge Digest
            digest = {
                "title": f"Conversation: {source_id[:8]}",
                "summary": summary_content,
                "entities": [],  # In future, extract entities with LLM
                "concepts": [],
                "decisions": [],
                "outcomes": [],
                "tags": ["ai-conversation", platform.lower()],
            }

            # 3. Commit to Guardian (OmegaKG)
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Assuming OmegaKG is at http://localhost:8765
                guardian_url = "http://localhost:8765/guardian/commit"
                logger.info(f"Committing knowledge to Guardian: {guardian_url}")

                payload = {
                    "raw_id": str(record_id),
                    "type": "conversation",
                    "digest": digest,
                    "metadata": {
                        "platform": platform,
                        "source_id": source_id,
                        "captured_at": captured_at.isoformat(),
                    },
                }

                resp = await client.post(guardian_url, json=payload)
                resp.raise_for_status()
                commit_result = resp.json()
                logger.info(f"Guardian result: {commit_result.get('message')}")

            # 4. Update Record (Mark Processed)
            await conn.execute(
                """
                UPDATE raw_conversations 
                SET processed = TRUE, 
                    processed_at = NOW()
                WHERE id = $1
            """,
                record_id,
            )

            logger.info(f"Successfully processed {source_id} via Guardian.")
            return 1

        except Exception as e:
            logger.error(f"Failed to process {source_id}: {e}", exc_info=True)
            return 0
        finally:
            await conn.close()
