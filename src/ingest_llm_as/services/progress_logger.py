"""
Progress logging service for repository ingestion tracking.

This module provides comprehensive progress tracking and logging capabilities
for repository processing, integrating with memOS for persistent storage
and providing detailed code structure documentation.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from ..models import (
    RepositoryIngestionRequest,
    RepositoryIngestionResponse,
    FileProcessingResult,
    ProcessingStatus,
    MemoryTier,
)
from ..services.memos_client import get_memos_client
from ..observability.logging import get_logger
from ..observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)


@dataclass
class ProgressLogEntry:
    """Represents a single progress log entry."""

    timestamp: str
    ingestion_id: str
    stage: str
    status: str
    progress_percentage: float
    files_processed: int
    total_files: int
    current_file: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class RepositoryStructureNode:
    """Represents a node in the repository structure tree."""

    name: str
    type: str  # "file", "directory", "function", "class", "method"
    path: str
    size_bytes: Optional[int] = None
    line_count: Optional[int] = None
    complexity_score: Optional[float] = None
    children: Optional[List["RepositoryStructureNode"]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CodeStructureAnalysis:
    """Comprehensive code structure analysis for a repository."""

    repository_path: str
    analysis_timestamp: str
    total_files: int
    total_lines_of_code: int
    total_functions: int
    total_classes: int
    average_complexity: float
    file_type_distribution: Dict[str, int]
    directory_structure: RepositoryStructureNode
    top_level_modules: List[Dict[str, Any]]
    complexity_distribution: Dict[str, int]  # complexity_range: count
    largest_files: List[Dict[str, Any]]
    most_complex_functions: List[Dict[str, Any]]
    dependencies_map: Dict[str, List[str]]
    recommendations: List[str]


class ProgressLogger:
    """
    Comprehensive progress logging system for repository ingestion.

    Provides real-time progress tracking, code structure documentation,
    and integration with memOS for persistent storage.
    """

    def __init__(self):
        """
        Initialize the ProgressLogger instance.
        
        Creates an internal logger, obtains Langfuse and memOS clients, and initializes the in-memory mapping for tracking progress entries by ingestion ID.
        """
        self.logger = get_logger(__name__)
        self.langfuse_client = get_langfuse_client()
        self.memos_client = get_memos_client()
        self.progress_entries: Dict[str, List[ProgressLogEntry]] = {}

    async def start_ingestion_logging(
        self, ingestion_id: str, request: RepositoryIngestionRequest
    ) -> None:
        """
        Initialize and record the initial progress entry for a repository ingestion.
        
        Creates an initial ProgressLogEntry with stage "initialization", status "started", 0% progress, and zero files, stores it in the in-memory progress map for the given ingestion_id, and persists it to memOS.
        
        Parameters:
            ingestion_id (str): Unique identifier for the ingestion.
            request (RepositoryIngestionRequest): Request used to populate initial entry details such as `repository_source`, `source_path`, `max_files`, `include_patterns`, and a truncated `exclude_patterns`.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Initialize progress tracking
        self.progress_entries[ingestion_id] = []

        # Create initial progress entry
        initial_entry = ProgressLogEntry(
            timestamp=timestamp,
            ingestion_id=ingestion_id,
            stage="initialization",
            status="started",
            progress_percentage=0.0,
            files_processed=0,
            total_files=0,
            details={
                "repository_source": request.repository_source.value,
                "source_path": request.source_path,
                "max_files": request.max_files,
                "include_patterns": request.include_patterns,
                "exclude_patterns": request.exclude_patterns[:5],  # Limit for storage
            },
        )

        self.progress_entries[ingestion_id].append(initial_entry)

        # Store in memOS
        await self._store_progress_entry(initial_entry)

        self.logger.info(f"Started progress logging for ingestion {ingestion_id}")

    async def log_discovery_complete(
        self,
        ingestion_id: str,
        files_discovered: int,
        files_to_process: int,
        discovery_time_ms: int,
    ) -> None:
        """
        Record completion of the repository discovery phase for an ingestion.
        
        Creates a ProgressLogEntry for the discovery stage, appends it to the in-memory progress history for the given ingestion_id, and persists the entry to memOS. The entry contains discovery metrics and a discovery efficiency value.
        
        Parameters:
            ingestion_id (str): Unique ingestion identifier.
            files_discovered (int): Total number of files discovered during discovery.
            files_to_process (int): Number of files selected for processing.
            discovery_time_ms (int): Time taken for discovery in milliseconds.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = ProgressLogEntry(
            timestamp=timestamp,
            ingestion_id=ingestion_id,
            stage="discovery",
            status="completed",
            progress_percentage=10.0,  # Discovery is ~10% of total work
            files_processed=0,
            total_files=files_to_process,
            details={
                "files_discovered": files_discovered,
                "files_to_process": files_to_process,
                "discovery_time_ms": discovery_time_ms,
                "discovery_efficiency": (
                    files_to_process / files_discovered if files_discovered > 0 else 0
                ),
            },
        )

        self.progress_entries[ingestion_id].append(entry)
        await self._store_progress_entry(entry)

        self.logger.info(
            f"Discovery complete for {ingestion_id}: {files_to_process} files to process"
        )

    async def log_file_processing_progress(
        self,
        ingestion_id: str,
        current_file: str,
        files_processed: int,
        total_files: int,
        file_result: Optional[FileProcessingResult] = None,
    ) -> None:
        """
        Record progress for a single file during ingestion, append an in-memory progress entry, and persist significant updates to memOS.
        
        Creates a ProgressLogEntry for the "processing" stage (progress is computed as 10% discovery plus up to 80% processing), appends it to the ingestion's in-memory history, and calls persistent storage for significant milestones (every 10% of total progress or every 10 files). If a FileProcessingResult is provided, its metrics and any error_message are included in the entry's details.
         
        Parameters:
            file_result (Optional[FileProcessingResult]): Optional result object whose fields (file_size, elements_extracted,
                chunks_created, embeddings_generated, processing_time_ms, complexity_score, error_message) are added to the
                progress details when present.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate progress (discovery=10%, processing=80%, finalization=10%)
        processing_progress = (
            (files_processed / total_files) * 80.0 if total_files > 0 else 0
        )
        total_progress = 10.0 + processing_progress  # Add discovery progress

        details = {
            "files_processed": files_processed,
            "total_files": total_files,
            "processing_rate": f"{files_processed/max(1, total_files)*100:.1f}%",
        }

        if file_result:
            details.update(
                {
                    "file_size": file_result.file_size,
                    "elements_extracted": file_result.elements_extracted,
                    "chunks_created": file_result.chunks_created,
                    "embeddings_generated": file_result.embeddings_generated,
                    "processing_time_ms": file_result.processing_time_ms,
                    "complexity_score": file_result.complexity_score,
                }
            )

        entry = ProgressLogEntry(
            timestamp=timestamp,
            ingestion_id=ingestion_id,
            stage="processing",
            status="in_progress",
            progress_percentage=total_progress,
            files_processed=files_processed,
            total_files=total_files,
            current_file=current_file,
            details=details,
            error_message=(
                file_result.error_message
                if file_result and file_result.error_message
                else None
            ),
        )

        self.progress_entries[ingestion_id].append(entry)

        # Store significant progress updates (every 10% or every 10 files)
        if (
            files_processed % max(1, total_files // 10) == 0
            or files_processed % 10 == 0
        ):
            await self._store_progress_entry(entry)

    async def log_ingestion_complete(
        self,
        ingestion_id: str,
        response: RepositoryIngestionResponse,
        structure_analysis: Optional[CodeStructureAnalysis] = None,
    ) -> None:
        """
        Record the final progress for a completed repository ingestion and persist a comprehensive ingestion report.
        
        Parameters:
            ingestion_id (str): Unique identifier for the ingestion run.
            response (RepositoryIngestionResponse): Final ingestion response containing timing, discovery and processing summaries, and lists of processed files.
            structure_analysis (Optional[CodeStructureAnalysis]): Optional code-structure analysis to include in the stored ingestion report.
        
        Notes:
            This creates a completion progress entry (100% progress), persists it to memory storage, and stores a combined ingestion report that may include the provided code structure analysis.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = ProgressLogEntry(
            timestamp=timestamp,
            ingestion_id=ingestion_id,
            stage="completion",
            status="completed",
            progress_percentage=100.0,
            files_processed=len(response.files_processed),
            total_files=response.files_to_process,
            details={
                "total_time_ms": response.total_time_ms,
                "discovery_time_ms": response.discovery_time_ms,
                "processing_time_ms": response.processing_time_ms,
                "files_discovered": response.files_discovered,
                "files_processed": len(response.files_processed),
                "summary": (
                    response.processing_summary.model_dump()
                    if response.processing_summary
                    else None
                ),
            },
        )

        self.progress_entries[ingestion_id].append(entry)
        await self._store_progress_entry(entry)

        # Store comprehensive ingestion report
        await self._store_ingestion_report(ingestion_id, response, structure_analysis)

        self.logger.info(
            f"Ingestion complete for {ingestion_id}: {len(response.files_processed)} files processed"
        )

    async def log_ingestion_error(
        self, ingestion_id: str, error_message: str, stage: str = "unknown"
    ) -> None:
        """
        Record a failed ingestion event and persist a corresponding progress entry.
        
        Creates a ProgressLogEntry with status "failed" for the given ingestion, appends it to the in-memory progress history for that ingestion, persists the entry to persistent storage, and logs an error message.
        
        Parameters:
            ingestion_id (str): Unique identifier for the ingestion run.
            error_message (str): Human-readable description of the error that occurred.
            stage (str): Ingestion stage where the error occurred (defaults to "unknown").
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        entry = ProgressLogEntry(
            timestamp=timestamp,
            ingestion_id=ingestion_id,
            stage=stage,
            status="failed",
            progress_percentage=0.0,
            files_processed=0,
            total_files=0,
            error_message=error_message,
        )

        if ingestion_id not in self.progress_entries:
            self.progress_entries[ingestion_id] = []

        self.progress_entries[ingestion_id].append(entry)
        await self._store_progress_entry(entry)

        self.logger.error(f"Ingestion failed for {ingestion_id}: {error_message}")

    async def generate_code_structure_analysis(
        self, repository_path: str, file_results: List[FileProcessingResult]
    ) -> CodeStructureAnalysis:
        """
        Produce a comprehensive analysis of a repository's code structure and metrics.
        
        Parameters:
            repository_path (str): Filesystem path to the repository root being analyzed.
            file_results (List[FileProcessingResult]): List of file processing results used to compute metrics and structure.
        
        Returns:
            CodeStructureAnalysis: Analysis including totals (files, lines, functions, classes), average complexity, file type distribution, directory tree, top-level modules, complexity distribution, largest files, most complex functions, an empty dependencies map (AST-based dependency extraction not performed), and generated recommendations.
        """
        analysis_timestamp = datetime.now(timezone.utc).isoformat()

        # Calculate aggregate metrics
        successful_files = [
            r for r in file_results if r.status == ProcessingStatus.COMPLETED
        ]
        total_files = len(successful_files)
        total_lines_of_code = sum(
            self._estimate_lines_of_code(r) for r in successful_files
        )
        total_functions = sum(r.elements_extracted for r in successful_files)
        total_classes = sum(self._estimate_classes(r) for r in successful_files)

        # Calculate average complexity
        complexities = [
            r.complexity_score
            for r in successful_files
            if r.complexity_score and r.complexity_score > 0
        ]
        average_complexity = (
            sum(complexities) / len(complexities) if complexities else 0.0
        )

        # File type distribution
        file_type_distribution = {}
        for result in file_results:
            ext = Path(result.relative_path).suffix or "no_extension"
            file_type_distribution[ext] = file_type_distribution.get(ext, 0) + 1

        # Build directory structure
        directory_structure = self._build_directory_structure(
            repository_path, file_results
        )

        # Generate top-level modules
        top_level_modules = self._extract_top_level_modules(file_results)

        # Complexity distribution
        complexity_distribution = self._calculate_complexity_distribution(complexities)

        # Largest files
        largest_files = sorted(
            [
                {
                    "path": r.relative_path,
                    "size": r.file_size,
                    "lines": self._estimate_lines_of_code(r),
                }
                for r in successful_files
            ],
            key=lambda x: x["size"],
            reverse=True,
        )[:10]

        # Most complex functions (estimated)
        most_complex_functions = sorted(
            [
                {
                    "path": r.relative_path,
                    "complexity": r.complexity_score,
                    "elements": r.elements_extracted,
                }
                for r in successful_files
                if r.complexity_score and r.complexity_score > 0
            ],
            key=lambda x: x["complexity"],
            reverse=True,
        )[:10]

        # Generate recommendations
        recommendations = self._generate_recommendations(
            total_files, average_complexity, file_type_distribution, largest_files
        )

        return CodeStructureAnalysis(
            repository_path=repository_path,
            analysis_timestamp=analysis_timestamp,
            total_files=total_files,
            total_lines_of_code=total_lines_of_code,
            total_functions=total_functions,
            total_classes=total_classes,
            average_complexity=average_complexity,
            file_type_distribution=file_type_distribution,
            directory_structure=directory_structure,
            top_level_modules=top_level_modules,
            complexity_distribution=complexity_distribution,
            largest_files=largest_files,
            most_complex_functions=most_complex_functions,
            dependencies_map={},  # Would need AST analysis for detailed deps
            recommendations=recommendations,
        )

    async def get_progress_status(
        self, ingestion_id: str
    ) -> Optional[List[ProgressLogEntry]]:
        """
        Retrieve the list of progress log entries for a given ingestion.
        
        Returns:
            List[ProgressLogEntry] of entries for the ingestion, or `None` if no entries exist.
        """
        return self.progress_entries.get(ingestion_id)

    async def _store_progress_entry(self, entry: ProgressLogEntry) -> None:
        """
        Persist a progress log entry to memOS as an episodic memory.
        
        Formats the ProgressLogEntry into human-readable content, attaches metadata
        (ingestion_id, stage, status, progress_percentage, timestamp, entry_type),
        and stores it via the memos_client. Any exceptions raised during storage are
        caught and result in a warning log rather than being propagated.
        
        Parameters:
            entry (ProgressLogEntry): The progress entry to format and persist.
        """
        try:
            content = f"Repository Ingestion Progress - {entry.stage.title()}\n\n"
            content += f"Ingestion ID: {entry.ingestion_id}\n"
            content += f"Stage: {entry.stage}\n"
            content += f"Status: {entry.status}\n"
            content += f"Progress: {entry.progress_percentage:.1f}%\n"
            content += f"Files Processed: {entry.files_processed}/{entry.total_files}\n"

            if entry.current_file:
                content += f"Current File: {entry.current_file}\n"

            if entry.error_message:
                content += f"Error: {entry.error_message}\n"

            if entry.details:
                content += f"\nDetails:\n{json.dumps(entry.details, indent=2)}\n"

            metadata = {
                "ingestion_id": entry.ingestion_id,
                "stage": entry.stage,
                "status": entry.status,
                "progress_percentage": entry.progress_percentage,
                "timestamp": entry.timestamp,
                "entry_type": "progress_log",
            }

            await self.memos_client.store_memory(
                content=content,
                memory_tier=MemoryTier.EPISODIC,  # Progress logs are episodic memories
                metadata=metadata,
            )

        except Exception as e:
            self.logger.warning(f"Failed to store progress entry in memOS: {e}")

    async def _store_ingestion_report(
        self,
        ingestion_id: str,
        response: RepositoryIngestionResponse,
        structure_analysis: Optional[CodeStructureAnalysis],
    ) -> None:
        """
        Builds a human-readable ingestion report and stores it (and optional code structure analysis) in memOS as semantic memory entries.
        
        Parameters:
            ingestion_id (str): Unique identifier for the ingestion run.
            response (RepositoryIngestionResponse): Aggregated ingestion result containing repository path, timings, file counts, status, and optional processing summary.
            structure_analysis (Optional[CodeStructureAnalysis]): Optional code structure analysis to store as a separate semantic memory entry.
        
        Notes:
            - The function creates a textual report summarizing processing metrics, detailed analysis (if available), code structure recommendations (if provided), and recent progress history, then stores it in memOS with metadata.
            - If a CodeStructureAnalysis is provided, a separate semantic memory entry containing the serialized analysis is also stored.
            - Any exceptions raised while storing memories are caught and a warning is logged; errors are not re-raised.
        """
        try:
            # Create comprehensive report
            content = f"Repository Ingestion Report\n{'='*50}\n\n"
            content += f"Ingestion ID: {ingestion_id}\n"
            content += f"Repository: {response.repository_path}\n"
            content += f"Completed: {response.completed_at}\n"
            content += f"Status: {response.status.value}\n\n"

            # Processing Summary
            content += f"Processing Summary\n{'-'*20}\n"
            content += f"Files Discovered: {response.files_discovered}\n"
            content += f"Files Processed: {len(response.files_processed)}\n"
            content += f"Discovery Time: {response.discovery_time_ms}ms\n"
            content += f"Processing Time: {response.processing_time_ms}ms\n"
            content += f"Total Time: {response.total_time_ms}ms\n\n"

            # Detailed Summary
            if response.processing_summary:
                summary = response.processing_summary
                content += f"Detailed Analysis\n{'-'*20}\n"
                content += f"Elements Extracted: {summary.total_elements_extracted}\n"
                content += f"Chunks Created: {summary.total_chunks_created}\n"
                content += (
                    f"Embeddings Generated: {summary.total_embeddings_generated}\n"
                )
                content += f"Average Complexity: {summary.average_complexity:.2f}\n"
                content += f"File Types: {summary.file_type_distribution}\n\n"

                if summary.largest_files:
                    content += "Largest Files:\n"
                    for file_info in summary.largest_files[:5]:
                        content += (
                            f"  - {file_info['path']} ({file_info['size']} bytes)\n"
                        )
                    content += "\n"

                if summary.most_complex_files:
                    content += "Most Complex Files:\n"
                    for file_info in summary.most_complex_files[:5]:
                        content += f"  - {file_info['path']} (complexity: {file_info['complexity']:.2f})\n"
                    content += "\n"

            # Code Structure Analysis
            if structure_analysis:
                content += f"Code Structure Analysis\n{'-'*25}\n"
                content += (
                    f"Total Lines of Code: {structure_analysis.total_lines_of_code:,}\n"
                )
                content += f"Total Functions: {structure_analysis.total_functions}\n"
                content += f"Total Classes: {structure_analysis.total_classes}\n"
                content += f"Average Complexity: {structure_analysis.average_complexity:.2f}\n\n"

                if structure_analysis.recommendations:
                    content += "Recommendations:\n"
                    for rec in structure_analysis.recommendations:
                        content += f"  • {rec}\n"
                    content += "\n"

            # Progress History
            progress_history = self.progress_entries.get(ingestion_id, [])
            if progress_history:
                content += f"Progress History\n{'-'*15}\n"
                for entry in progress_history[-10:]:  # Last 10 entries
                    content += f"{entry.timestamp}: {entry.stage} - {entry.status} ({entry.progress_percentage:.1f}%)\n"

            metadata = {
                "ingestion_id": ingestion_id,
                "repository_path": response.repository_path,
                "files_processed": len(response.files_processed),
                "total_time_ms": response.total_time_ms,
                "report_type": "repository_ingestion_report",
                "entry_type": "ingestion_report",
            }

            # Store in memOS as semantic memory (long-term knowledge)
            await self.memos_client.store_memory(
                content=content, memory_tier=MemoryTier.SEMANTIC, metadata=metadata
            )

            # Also store structure analysis as separate entry if available
            if structure_analysis:
                structure_content = f"Repository Code Structure Analysis\n{'='*40}\n\n"
                structure_content += json.dumps(asdict(structure_analysis), indent=2)

                await self.memos_client.store_memory(
                    content=structure_content,
                    memory_tier=MemoryTier.SEMANTIC,
                    metadata={
                        **metadata,
                        "entry_type": "code_structure_analysis",
                        "analysis_timestamp": structure_analysis.analysis_timestamp,
                    },
                )

        except Exception as e:
            self.logger.warning(f"Failed to store ingestion report in memOS: {e}")

    def _estimate_lines_of_code(self, file_result: FileProcessingResult) -> int:
        """
        Estimate the number of source code lines in a file.
        
        Parameters:
            file_result (FileProcessingResult): Metadata for the processed file; this function uses the file_size (in bytes) to compute the estimate.
        
        Returns:
            lines_estimate (int): Estimated lines of code computed from file_size assuming ~50 characters per line; always at least 1.
        """
        # Rough estimate: ~50 chars per line average
        return max(1, file_result.file_size // 50)

    def _estimate_classes(self, file_result: FileProcessingResult) -> int:
        """
        Estimate the number of classes in a processed file using a simple heuristic.
        
        Parameters:
            file_result (FileProcessingResult): Processing result whose `elements_extracted` field is used by the heuristic.
        
        Returns:
            int: Estimated number of classes (>= 0), computed as 20% of `elements_extracted`, rounded down.
        """
        # Assume ~20% of elements are classes (very rough)
        return max(0, int(file_result.elements_extracted * 0.2))

    def _build_directory_structure(
        self, repository_path: str, file_results: List[FileProcessingResult]
    ) -> RepositoryStructureNode:
        """
        Create a simplified directory-tree representation for a repository and its processed files.
        
        Parameters:
            repository_path (str): Path to the repository root used as the root node name and path.
            file_results (List[FileProcessingResult]): File processing results used to create file nodes (each becomes a child node).
        
        Returns:
            RepositoryStructureNode: Root directory node representing the repository with child file nodes summarizing each file's size, estimated line count, and complexity.
        """
        root = RepositoryStructureNode(
            name=Path(repository_path).name,
            type="directory",
            path=repository_path,
            children=[],
        )

        # Group files by directory
        dirs = {}
        for result in file_results:
            dir_path = str(Path(result.relative_path).parent)
            if dir_path not in dirs:
                dirs[dir_path] = []
            dirs[dir_path].append(result)

        # Add files to structure (simplified)
        for dir_path, files in dirs.items():
            for file_result in files:
                file_node = RepositoryStructureNode(
                    name=Path(file_result.relative_path).name,
                    type="file",
                    path=file_result.relative_path,
                    size_bytes=file_result.file_size,
                    line_count=self._estimate_lines_of_code(file_result),
                    complexity_score=file_result.complexity_score,
                )
                root.children.append(file_node)

        return root

    def _extract_top_level_modules(
        self, file_results: List[FileProcessingResult]
    ) -> List[Dict[str, Any]]:
        """
        Identify top-level Python modules from processed file results and return their key metrics sorted by element count.
        
        Parameters:
            file_results (List[FileProcessingResult]): List of file processing results to inspect.
        
        Returns:
            List[Dict[str, Any]]: Up to 20 dictionaries for files that are top-level Python modules (no subdirectory, `.py` extension). Each dictionary contains:
                - `name`: module name (filename without extension)
                - `path`: relative path to the file
                - `elements`: number of extracted elements
                - `complexity`: complexity score
                - `size`: file size in bytes
            The list is sorted by `elements` in descending order.
        """
        modules = []
        for result in file_results:
            if result.relative_path.endswith(".py") and "/" not in result.relative_path:
                modules.append(
                    {
                        "name": Path(result.relative_path).stem,
                        "path": result.relative_path,
                        "elements": result.elements_extracted,
                        "complexity": result.complexity_score,
                        "size": result.file_size,
                    }
                )
        return sorted(modules, key=lambda x: x["elements"], reverse=True)[:20]

    def _calculate_complexity_distribution(
        self, complexities: List[float]
    ) -> Dict[str, int]:
        """
        Summarizes a list of numeric complexity scores into predefined complexity bands.
        
        Parameters:
            complexities (List[float]): Numeric complexity scores for functions or files.
        
        Returns:
            distribution (Dict[str, int]): Mapping from band name to count:
                - "low (0-2)": count of scores <= 2
                - "medium (2-5)": count of scores > 2 and <= 5
                - "high (5-10)": count of scores > 5 and <= 10
                - "very_high (10+)": count of scores > 10
        """
        if not complexities:
            return {}

        distribution = {
            "low (0-2)": 0,
            "medium (2-5)": 0,
            "high (5-10)": 0,
            "very_high (10+)": 0,
        }

        for complexity in complexities:
            if complexity <= 2:
                distribution["low (0-2)"] += 1
            elif complexity <= 5:
                distribution["medium (2-5)"] += 1
            elif complexity <= 10:
                distribution["high (5-10)"] += 1
            else:
                distribution["very_high (10+)"] += 1

        return distribution

    def _generate_recommendations(
        self,
        total_files: int,
        average_complexity: float,
        file_type_distribution: Dict[str, int],
        largest_files: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Generate a list of actionable recommendations for improving repository maintainability and testing based on aggregate metrics.
        
        Parameters:
            total_files (int): Total number of files analyzed in the repository.
            average_complexity (float): Average complexity score computed across analyzed files/functions.
            file_type_distribution (Dict[str, int]): Mapping of file extension or type to counts (e.g., {".py": 120, ".md": 10}).
            largest_files (List[Dict[str, Any]]): List of file descriptors sorted by size descending; each item should include at least `"path"` and `"size"`.
        
        Returns:
            List[str]: A list of human-readable recommendation strings derived from thresholds such as complexity, repository size, dominant file types, large file detection, and relative test-file coverage.
        """
        recommendations = []

        if average_complexity > 7:
            recommendations.append(
                "Consider refactoring complex functions to improve maintainability"
            )

        if total_files > 100:
            recommendations.append(
                "Large codebase - consider implementing automated testing and CI/CD"
            )

        python_files = file_type_distribution.get(".py", 0)
        if python_files > 50:
            recommendations.append("Consider organizing code into packages and modules")

        if largest_files and largest_files[0]["size"] > 100000:
            recommendations.append(
                f"Large file detected ({largest_files[0]['path']}) - consider splitting into smaller modules"
            )

        test_files = sum(
            1 for f in file_type_distribution.keys() if "test" in f.lower()
        )
        if test_files < python_files * 0.3:
            recommendations.append(
                "Consider adding more test coverage for better code quality"
            )

        return recommendations


# Global progress logger instance
_progress_logger: Optional[ProgressLogger] = None


def get_progress_logger() -> ProgressLogger:
    """
    Get the global progress logger instance.

    Returns:
        ProgressLogger: Configured logger instance
    """
    global _progress_logger
    if _progress_logger is None:
        _progress_logger = ProgressLogger()
    return _progress_logger