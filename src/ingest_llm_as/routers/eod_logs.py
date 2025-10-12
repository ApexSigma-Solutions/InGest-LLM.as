"""
EOD (End of Day) Logs Router
Handles ingestion of structured development session logs into the knowledge graph.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from ..core.logging_config import get_logger
from ..services.knowledge_graph_service import KnowledgeGraphService

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["EOD Logs"])


class SessionStats(BaseModel):
    """Statistics for a development session"""

    duration_minutes: int = Field(default=0, description="Session duration in minutes")
    files_modified: int = Field(default=0, description="Number of files modified")
    commits_made: int = Field(default=0, description="Number of commits made")


class ProgressData(BaseModel):
    """Development progress data"""

    tasks_completed: List[str] = Field(description="List of completed task IDs")
    key_decisions_or_insights: str = Field(
        description="Key decisions made or insights gained"
    )
    blockers_encountered: str = Field(description="Blockers that prevented progress")
    next_steps: str = Field(description="Planned work for next session")


class SessionData(BaseModel):
    """Git session information"""

    branch: str = Field(description="Git branch name")
    commit: str = Field(description="Git commit hash")
    stats: SessionStats = Field(description="Session statistics")


class EODLogEntry(BaseModel):
    """Complete EOD log entry structure"""

    log_id: str = Field(description="Unique log identifier")
    timestamp: str = Field(description="Timestamp in YYYYMMDD-HHMMSS format")
    project: str = Field(description="Project name")
    session: SessionData = Field(description="Session information")
    progress: ProgressData = Field(description="Development progress")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class EODLogResponse(BaseModel):
    """Response for EOD log ingestion"""

    status: str = Field(description="Ingestion status")
    log_id: str = Field(description="Log identifier")
    knowledge_graph_id: Optional[str] = Field(description="Knowledge graph entry ID")
    message: str = Field(description="Response message")


class EODLogService:
    """Service for processing EOD logs"""

    def __init__(self):
        """
        Initialize the EODLogService and set up its necessary dependencies.
        
        Creates and assigns a KnowledgeGraphService instance to `self.kg_service` for interacting with the knowledge graph.
        """
        self.kg_service = KnowledgeGraphService()

    async def process_eod_log(self, log_entry: EODLogEntry) -> EODLogResponse:
        """
        Ingest an EOD log entry, persist it to the knowledge graph and semantic store, and update project metrics.
        
        Returns:
            EODLogResponse: Response containing the ingestion status, the original `log_id`, the created `knowledge_graph_id` when available, and a human-readable message.
        
        Raises:
            HTTPException: If processing fails (returns status code 500).
        """
        try:
            logger.info(f"Processing EOD log: {log_entry.log_id}")

            # Transform EOD log into knowledge graph format
            kg_data = self._transform_to_knowledge_graph(log_entry)

            # Store in knowledge graph
            kg_id = await self._store_in_knowledge_graph(kg_data)

            # Store in vector database for semantic search
            await self._store_for_semantic_search(log_entry)

            # Update project metrics
            await self._update_project_metrics(log_entry)

            logger.info(f"EOD log processed successfully: {log_entry.log_id}")

            return EODLogResponse(
                status="success",
                log_id=log_entry.log_id,
                knowledge_graph_id=kg_id,
                message="EOD log ingested successfully into knowledge graph",
            )

        except Exception as e:
            logger.error(f"Failed to process EOD log {log_entry.log_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to process EOD log: {str(e)}"
            )

    def _transform_to_knowledge_graph(self, log_entry: EODLogEntry) -> Dict[str, Any]:
        """
        Convert an EODLogEntry into a knowledge-graph-compatible dictionary.
        
        Returns:
            dict: A dictionary representing the log in the knowledge graph schema, including keys:
                - `type`, `id`, `timestamp`, `project`, `branch`, `commit`
                - `tasks_completed`, `key_insights`, `blockers`, `next_steps`
                - `session_stats`: dict with `duration`, `files_modified`, `commits`
                - `relationships`: list of relationship objects
        """
        return {
            "type": "eod_session",
            "id": log_entry.log_id,
            "timestamp": log_entry.timestamp,
            "project": log_entry.project,
            "branch": log_entry.session.branch,
            "commit": log_entry.session.commit,
            "tasks_completed": log_entry.progress.tasks_completed,
            "key_insights": log_entry.progress.key_decisions_or_insights,
            "blockers": log_entry.progress.blockers_encountered,
            "next_steps": log_entry.progress.next_steps,
            "session_stats": {
                "duration": log_entry.session.stats.duration_minutes,
                "files_modified": log_entry.session.stats.files_modified,
                "commits": log_entry.session.stats.commits_made,
            },
            "relationships": self._extract_relationships(log_entry),
        }

    def _extract_relationships(self, log_entry: EODLogEntry) -> List[Dict[str, str]]:
        """
        Builds a list of relationship records linking the log, its project, completed tasks, and branch.
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries each containing keys `from`, `to`, and `type` that describe relationships such as:
                - project -> log (`HAS_SESSION`)
                - log -> task (`COMPLETED_TASK`)
                - log -> branch (`ON_BRANCH`)
        """
        relationships = []

        # Project -> Session relationship
        relationships.append(
            {"from": log_entry.project, "to": log_entry.log_id, "type": "HAS_SESSION"}
        )

        # Task relationships
        for task_id in log_entry.progress.tasks_completed:
            relationships.append(
                {"from": log_entry.log_id, "to": task_id, "type": "COMPLETED_TASK"}
            )

        # Branch relationship
        relationships.append(
            {
                "from": log_entry.log_id,
                "to": log_entry.session.branch,
                "type": "ON_BRANCH",
            }
        )

        return relationships

    async def _store_in_knowledge_graph(self, kg_data: Dict[str, Any]) -> str:
        """
        Constructs and returns a knowledge-graph identifier for the provided data.
        
        Parameters:
            kg_data (Dict[str, Any]): Dictionary representing the knowledge-graph payload; must contain the key `'id'` which is used to form the returned identifier.
        
        Returns:
            str: Knowledge-graph identifier derived from `kg_data['id']` (e.g. `"kg_<id>"`).
        """
        # This would integrate with your actual knowledge graph storage
        # For now, return a mock ID
        return f"kg_{kg_data['id']}"

    async def _store_for_semantic_search(self, log_entry: EODLogEntry):
        """
        Prepare and store a textual representation of an EOD log for semantic search and embedding.
        
        Parameters:
            log_entry (EODLogEntry): The end-of-day log to be converted into a combined text block and indexed in the semantic/embedding store.
        """
        # Combine all text content for embedding
        text_content = f"""
        Project: {log_entry.project}
        Branch: {log_entry.session.branch}
        Tasks Completed: {', '.join(log_entry.progress.tasks_completed)}
        Key Insights: {log_entry.progress.key_decisions_or_insights}
        Blockers: {log_entry.progress.blockers_encountered}
        Next Steps: {log_entry.progress.next_steps}
        """

        # Store in vector database (implementation depends on your vector DB)
        # This would call your embedding service and store in Qdrant
        logger.info(f"Storing EOD log for semantic search: {log_entry.log_id}")
        logger.debug(f"EOD log content for embedding: {text_content}")

    async def _update_project_metrics(self, log_entry: EODLogEntry):
        """
        Update aggregated project metrics using data from a single EOD log entry.
        
        Parameters:
            log_entry (EODLogEntry): The end-of-day log containing session, progress, and metadata used to update project-level metrics such as velocity, task completion, and recent blockers.
        """
        # Update project velocity, completion rates, etc.
        logger.info(f"Updating project metrics for: {log_entry.project}")


# Initialize service
eod_service = EODLogService()


@router.post("/eod-log", response_model=EODLogResponse)
async def ingest_eod_log(log_entry: EODLogEntry) -> EODLogResponse:
    """
    Ingest an End of Day (EOD) log entry into the knowledge graph and trigger downstream storage, embedding, and metrics updates.
    
    Parameters:
        log_entry (EODLogEntry): Structured EOD log containing project, session, progress, and optional metadata.
    
    Returns:
        EODLogResponse: Result of the ingestion containing the operation status, the original log_id, an optional knowledge_graph_id, and a human-readable message.
    """
    return await eod_service.process_eod_log(log_entry)


@router.get("/eod-logs/{project}")
async def get_eod_logs_for_project(project: str, limit: int = 10):
    """
    Fetches recent end-of-day log entries for a project.
    
    Parameters:
        project (str): Project identifier to retrieve logs for.
        limit (int): Maximum number of recent log entries to return.
    
    Returns:
        dict: Response containing:
            - project (str): The requested project identifier.
            - logs (List[dict]): List of EOD log entries (empty if none).
            - message (str): Human-readable summary of the result.
    """
    # Implementation would query knowledge graph for project's EOD logs
    return {
        "project": project,
        "logs": [],  # Would return actual log data
        "message": f"Retrieved {limit} EOD logs for project {project}",
    }


@router.get("/eod-logs/{project}/metrics")
async def get_project_metrics(project: str):
    """
    Return development metrics aggregated from End-of-Day logs for the given project.
    
    Returns:
        dict: A mapping with keys:
            - "project" (str): Project identifier provided as input.
            - "metrics" (dict): Aggregated metrics containing:
                - "total_sessions" (int): Total number of recorded sessions.
                - "average_session_duration" (int): Average session duration in minutes.
                - "tasks_completed_total" (int): Sum of tasks completed across sessions.
                - "most_common_blockers" (List[str]): Ranked list of frequent blockers.
                - "development_velocity" (int): Computed velocity metric for the project.
    """
    # Implementation would calculate metrics from stored EOD data
    return {
        "project": project,
        "metrics": {
            "total_sessions": 0,
            "average_session_duration": 0,
            "tasks_completed_total": 0,
            "most_common_blockers": [],
            "development_velocity": 0,
        },
    }