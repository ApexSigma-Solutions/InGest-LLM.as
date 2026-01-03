import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase

from ingest_llm_as.config import get_settings

logger = logging.getLogger(__name__)

class Neo4jService:
    """
    Direct client for Neo4j graph operations.
    Replicates logic for ChatSession node creation.
    """
    def __init__(self):
        settings = get_settings()
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )

    def close(self):
        self.driver.close()

    def create_chat_session(self, 
                          source_id: str, 
                          platform: str, 
                          filepath: str, 
                          message_count: int, 
                          url: Optional[str] = None):
        """
        Creates a ChatSession node and links it to Decisions if present.
        """
        query = """
        MERGE (s:ChatSession {conversation_hash: $source_id})
        ON CREATE SET 
            s.created_at = datetime(),
            s.platform = $platform,
            s.filepath = $filepath,
            s.url = $url,
            s.message_count = $message_count
        ON MATCH SET 
            s.updated_at = datetime(),
            s.message_count = $message_count,
            s.filepath = $filepath
        RETURN elementId(s) as element_id
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, {
                    "source_id": source_id,
                    "platform": platform,
                    "filepath": filepath,
                    "url": url,
                    "message_count": message_count
                })
                record = result.single()
                if record:
                    return record["element_id"]
                return None
        except Exception as e:
            logger.error(f"Failed to create ChatSession in Neo4j: {e}")
            raise
            
    def create_decisions(self, session_hash: str, decisions: List[str]):
        """
        Creates Decision nodes linked to the session.
        """
        if not decisions:
            return

        query = """
        MATCH (s:ChatSession {conversation_hash: $session_hash})
        UNWIND $decisions as decision_text
        MERGE (d:Decision {content: decision_text})
        ON CREATE SET d.created_at = datetime()
        MERGE (s)-[:CONTAINS_DECISION]->(d)
        """
        try:
            with self.driver.session() as session:
                session.run(query, {
                    "session_hash": session_hash,
                    "decisions": decisions
                })
        except Exception as e:
            logger.error(f"Failed to create Decisions in Neo4j: {e}")
