"""
HTTP client for memOS.as integration.

This module provides the client interface for communicating with the memOS.as
memory storage system.
"""

import hashlib
import logging
from typing import Dict, List, Optional

import httpx
from pydantic import ValidationError

from ..config import settings
from ..models import (
    MemoryStorageRequest,
    MemoryStorageResponse,
    MemoryTier,
)

logger = logging.getLogger(__name__)


class MemOSClientError(Exception):
    """Base exception for memOS.as client errors."""

    pass


class MemOSConnectionError(MemOSClientError):
    """Raised when connection to memOS.as fails."""

    pass


class MemOSAPIError(MemOSClientError):
    """Raised when memOS.as returns an API error."""

    pass


class MemOSClient:
    """
    HTTP client for memOS.as memory storage operations.

    Handles communication with the memOS.as service for storing
    ingested content in the appropriate memory tiers.
    """

    def __init__(self):
        self.base_url = settings.memos_base_url.rstrip("/")
        self.timeout = settings.memos_timeout
        self.api_key = settings.memos_api_key

        # HTTP client configuration
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout, headers=headers
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """
        Check if memOS.as is healthy and reachable.

        Returns:
            bool: True if memOS.as is healthy, False otherwise.
        """
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"memOS.as health check failed: {e}")
            return False

    async def store_memory(
        self,
        content: str,
        memory_tier: MemoryTier,
        metadata: Dict,
        embedding: Optional[List[float]] = None,
        relationships: Optional[List[Dict]] = None,
    ) -> MemoryStorageResponse:
        """
        Store content in memOS.as memory system.

        Args:
            content: The content to store
            memory_tier: Which memory tier to store in
            metadata: Associated metadata
            embedding: Optional embedding vector
            relationships: Optional relationship data

        Returns:
            MemoryStorageResponse: Storage confirmation with memory ID

        Raises:
            MemOSConnectionError: If connection fails
            MemOSAPIError: If API returns an error
            ValidationError: If response data is invalid
        """
        try:
            # Prepare storage request
            storage_request = MemoryStorageRequest(
                content=content,
                memory_tier=memory_tier,
                metadata=metadata,
                embedding=embedding,
                relationships=relationships or [],
            )

            # Send to memOS.as
            endpoint = f"/memory/{memory_tier.value}/store"

            logger.info(f"Storing content in {memory_tier.value} memory tier")

            response = await self.client.post(
                endpoint, json=storage_request.model_dump()
            )

            if response.status_code != 200:
                error_msg = f"memOS.as API error: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except Exception:
                    error_msg += f" - {response.text}"
                raise MemOSAPIError(error_msg)

            # Parse response
            response_data = response.json()
            return MemoryStorageResponse(**response_data)

        except httpx.RequestError as e:
            raise MemOSConnectionError(f"Failed to connect to memOS.as: {e}")
        except httpx.HTTPStatusError as e:
            raise MemOSAPIError(f"memOS.as HTTP error: {e}")
        except ValidationError as e:
            logger.error(f"Invalid response from memOS.as: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing memory: {e}")
            raise MemOSClientError(f"Unexpected error: {e}")

    async def store_episodic_memory(
        self, content: str, metadata: Dict
    ) -> MemoryStorageResponse:
        """
        Store content in episodic memory (chronological events).

        Args:
            content: The content to store
            metadata: Event metadata (timestamp, source, etc.)

        Returns:
            MemoryStorageResponse: Storage confirmation
        """
        return await self.store_memory(
            content=content, memory_tier=MemoryTier.EPISODIC, metadata=metadata
        )

    async def store_semantic_memory(
        self,
        content: str,
        metadata: Dict,
        embedding: Optional[List[float]] = None,
        relationships: Optional[List[Dict]] = None,
    ) -> MemoryStorageResponse:
        """
        Store content in semantic memory (knowledge and concepts).

        Args:
            content: The content to store
            metadata: Knowledge metadata
            embedding: Content embedding vector
            relationships: Related concepts/entities

        Returns:
            MemoryStorageResponse: Storage confirmation
        """
        return await self.store_memory(
            content=content,
            memory_tier=MemoryTier.SEMANTIC,
            metadata=metadata,
            embedding=embedding,
            relationships=relationships,
        )


def generate_content_hash(content: str) -> str:
    """
    Generate a deterministic hash for content deduplication.

    Args:
        content: The content to hash

    Returns:
        str: SHA-256 hash of the content
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# Global client instance
_client_instance: Optional[MemOSClient] = None


async def get_memos_client() -> MemOSClient:
    """
    Get or create the global memOS.as client instance.

    Returns:
        MemOSClient: Configured client instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = MemOSClient()
    return _client_instance
