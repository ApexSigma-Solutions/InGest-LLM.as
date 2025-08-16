"""
Content processing utilities for text ingestion.

This module provides utilities for processing, chunking, and preparing
content for storage in the memOS.as memory system.
"""

import re
import logging
from typing import List, Tuple
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    Handles content processing and chunking for ingestion.

    Provides methods to clean, validate, and chunk content
    for optimal storage in different memory tiers.
    """

    def __init__(self, chunk_size: int = None):
        """
        Initialize content processor.

        Args:
            chunk_size: Maximum size for content chunks
        """
        self.chunk_size = chunk_size or settings.default_chunk_size
        self.max_chunk_size = 10000  # Hard limit
        self.min_chunk_size = 100  # Minimum viable chunk

    def clean_content(self, content: str) -> str:
        """
        Clean and normalize content for processing.

        Args:
            content: Raw content string

        Returns:
            str: Cleaned content
        """
        # Strip whitespace
        cleaned = content.strip()

        # Normalize whitespace (multiple spaces/newlines to single)
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Remove control characters except newlines and tabs
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", cleaned)

        return cleaned

    def chunk_content(self, content: str, chunk_size: int = None) -> List[str]:
        """
        Split content into optimally-sized chunks.

        Uses intelligent chunking that tries to preserve:
        - Sentence boundaries
        - Paragraph boundaries
        - Code block boundaries

        Args:
            content: Content to chunk
            chunk_size: Override default chunk size

        Returns:
            List[str]: List of content chunks
        """
        target_size = chunk_size or self.chunk_size

        # For small content, return as single chunk
        if len(content) <= target_size:
            return [content]

        chunks = []
        remaining = content

        while remaining and len(remaining) > target_size:
            # Find optimal split point
            chunk, remaining = self._find_optimal_split(remaining, target_size)

            if chunk:
                chunks.append(chunk.strip())

            # Safety check to prevent infinite loops
            if len(chunks) > settings.max_chunks_per_request:
                logger.warning(
                    f"Hit max chunks limit ({settings.max_chunks_per_request})"
                )
                break

        # Add final chunk if remaining content
        if remaining and remaining.strip():
            chunks.append(remaining.strip())

        return [chunk for chunk in chunks if len(chunk) >= self.min_chunk_size]

    def _find_optimal_split(self, content: str, target_size: int) -> Tuple[str, str]:
        """
        Find optimal split point for content chunking.

        Tries to split at natural boundaries in order of preference:
        1. Double newline (paragraph boundary)
        2. Single newline + sentence end
        3. Sentence boundary (. ! ?)
        4. Word boundary
        5. Character boundary (fallback)

        Args:
            content: Content to split
            target_size: Target chunk size

        Returns:
            Tuple[str, str]: (chunk, remaining_content)
        """
        if len(content) <= target_size:
            return content, ""

        # Define search window (look back from target size)
        search_start = max(0, target_size - 200)
        search_end = min(len(content), target_size + 100)
        search_text = content[search_start:search_end]

        # Try paragraph boundary first
        paragraph_matches = list(re.finditer(r"\n\s*\n", search_text))
        if paragraph_matches:
            split_pos = search_start + paragraph_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try sentence boundary at line end
        sentence_line_matches = list(re.finditer(r"[.!?]\s*\n", search_text))
        if sentence_line_matches:
            split_pos = search_start + sentence_line_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try sentence boundary
        sentence_matches = list(re.finditer(r"[.!?]\s+", search_text))
        if sentence_matches:
            split_pos = search_start + sentence_matches[-1].end()
            return content[:split_pos], content[split_pos:]

        # Try word boundary
        word_matches = list(re.finditer(r"\s+", search_text))
        if word_matches:
            split_pos = search_start + word_matches[-1].start()
            return content[:split_pos], content[split_pos:]

        # Fallback: hard split at target size
        return content[:target_size], content[target_size:]

    def extract_metadata_from_content(self, content: str) -> dict:
        """
        Extract implicit metadata from content structure.

        Args:
            content: Content to analyze

        Returns:
            dict: Extracted metadata
        """
        metadata = {}

        # Basic content statistics
        metadata["word_count"] = len(content.split())
        metadata["char_count"] = len(content)
        metadata["line_count"] = content.count("\n") + 1

        # Try to detect content patterns
        if self._looks_like_code(content):
            metadata["detected_type"] = "code"
        elif self._looks_like_markdown(content):
            metadata["detected_type"] = "markdown"
        elif self._looks_like_json(content):
            metadata["detected_type"] = "json"
        else:
            metadata["detected_type"] = "text"

        # Extract potential title (first line if it looks like a title)
        lines = content.split("\n")
        if lines:
            first_line = lines[0].strip()
            if (
                len(first_line) < 100
                and not first_line.endswith(".")
                and len(first_line.split()) <= 10
            ):
                metadata["potential_title"] = first_line

        return metadata

    def _looks_like_code(self, content: str) -> bool:
        """Check if content appears to be code."""
        code_indicators = [
            "def ",
            "function ",
            "class ",
            "import ",
            "from ",
            "#!/",
            "<?",
            "<!--",
            "{",
            "}",
            "()",
            "=>",
            "console.log",
            "print(",
            "System.out",
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in code_indicators)

    def _looks_like_markdown(self, content: str) -> bool:
        """Check if content appears to be Markdown."""
        md_indicators = ["# ", "## ", "### ", "- ", "* ", "```", "[", "]("]
        return any(indicator in content for indicator in md_indicators)

    def _looks_like_json(self, content: str) -> bool:
        """Check if content appears to be JSON."""
        stripped = content.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        )


def create_ingestion_metadata(
    original_metadata: dict,
    chunk_index: int = 0,
    total_chunks: int = 1,
    processing_info: dict = None,
) -> dict:
    """
    Create comprehensive metadata for memory storage.

    Args:
        original_metadata: Original request metadata
        chunk_index: Index of this chunk (0-based)
        total_chunks: Total number of chunks
        processing_info: Additional processing information

    Returns:
        dict: Complete metadata for memOS.as storage
    """
    metadata = {
        # Original metadata
        **original_metadata,
        # Processing metadata
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "chunk_info": {
            "index": chunk_index,
            "total": total_chunks,
            "is_chunked": total_chunks > 1,
        },
        "processor_version": "1.0.0",
        # Service metadata
        "ingested_by": "InGest-LLM.as",
        "service_version": settings.app_version,
    }

    # Add processing info if provided
    if processing_info:
        metadata["processing"] = processing_info

    return metadata
