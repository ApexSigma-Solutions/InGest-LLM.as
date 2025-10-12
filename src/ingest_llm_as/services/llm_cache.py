"""
Redis-based LLM Cache Service

This service provides efficient caching for LLM prompts and responses
to optimize costs and improve performance across the ApexSigma ecosystem.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List, Callable, Awaitable
from dataclasses import dataclass, asdict

import numpy as np

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from ..observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    prompt_hash: str
    response: str
    model: str
    timestamp: datetime
    token_count: int
    cost_estimate: float
    metadata: Dict[str, Any]
    ttl_seconds: int = 3600  # 1 hour default

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the CacheEntry to a dictionary suitable for Redis storage.
        
        Returns:
            dict: Mapping of dataclass fields to serializable values. The `timestamp` field
            is converted to an ISO 8601 string.
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """
        Create a CacheEntry from a dictionary produced by storage.
        
        Parameters:
            data (dict): Dictionary in the storage format (as produced by CacheEntry.to_dict()),
                with the "timestamp" field as an ISO 8601 string.
        
        Returns:
            CacheEntry: A new CacheEntry instance with the "timestamp" converted to a datetime.
        """
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class CacheStats:
    """Cache statistics."""

    total_entries: int
    hit_rate: float
    total_cost_saved: float
    total_tokens_saved: int
    cache_size_mb: float
    oldest_entry: Optional[datetime]
    newest_entry: Optional[datetime]


class LLMCache:
    """
    Redis-based LLM cache for prompt optimization.

    Features:
    - Prompt deduplication based on semantic hashing
    - Configurable TTL per model/use case
    - Cost tracking and optimization metrics
    - Automatic cache cleanup and rotation
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "apexsigma:llm_cache:",
        default_ttl: int = 3600,
        max_cache_size_mb: float = 100.0,
    ):
        """
        Configure the LLMCache instance with connection and sizing defaults.
        
        Parameters:
            redis_url (str): Redis connection URL used to connect to the cache backend (default "redis://localhost:6379").
            key_prefix (str): Namespace prefix prepended to all cache keys to avoid collisions (default "apexsigma:llm_cache:").
            default_ttl (int): Default time-to-live in seconds applied to cache entries when no explicit TTL is provided (default 3600).
            max_cache_size_mb (float): Target maximum cache size in megabytes; exceeding this triggers cleanup of oldest entries (default 100.0).
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.max_cache_size_mb = max_cache_size_mb
        self.logger = get_logger(__name__)

        # Redis client (will be initialized in connect)
        self.redis_client = None

        # Stats tracking
        self.hits = 0
        self.misses = 0
        self.total_cost_saved = 0.0
        self.total_tokens_saved = 0

    async def connect(self) -> bool:
        """
        Establishes a Redis connection and stores the connected client on the instance.
        
        If the Redis library is not available or the connection/ping fails, the instance's
        `redis_client` remains unset (or unchanged) and the method returns `False`. On
        success, `self.redis_client` is assigned a connected Redis client.
        
        Returns:
            bool: `True` if a Redis client was created and verified reachable, `False` otherwise.
        """
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis library not available, cache disabled")
            return False

        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            return False

    def _generate_cache_key(
        self, prompt: str, model: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a deterministic, namespaced cache key for a model prompt.
        
        When provided, only the following metadata fields are incorporated into the key: "temperature", "max_tokens", "top_p", and "system_prompt". The key is the SHA-256 hex digest of the combined model, prompt, and selected metadata, prefixed with the instance's key_prefix.
        
        Parameters:
            metadata (Dict[str, Any], optional): Optional request metadata; only stable fields listed above affect the generated key.
        
        Returns:
            str: Namespaced cache key consisting of `self.key_prefix` followed by the SHA-256 hex digest of the content.
        """

        # Create a hash based on prompt content and model
        content = f"{model}:{prompt}"

        # Include relevant metadata in the hash
        if metadata:
            # Only include stable metadata that affects the response
            stable_metadata = {
                k: v
                for k, v in metadata.items()
                if k in ["temperature", "max_tokens", "top_p", "system_prompt"]
            }
            content += f":{json.dumps(stable_metadata, sort_keys=True)}"

        # Generate SHA-256 hash
        prompt_hash = hashlib.sha256(content.encode()).hexdigest()

        return f"{self.key_prefix}{prompt_hash}"

    def score_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)

            if norms == 0:
                return 0.0

            similarity = dot_product / norms

            # Ensure result is in [0, 1] range
            return max(0.0, min(1.0, (similarity + 1) / 2))

        except Exception as e:
            self.logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    async def get(
        self, prompt: str, model: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[CacheEntry]:
        """
        Retrieve the cached entry for a given prompt and model.
        
        Parameters:
            prompt (str): The prompt text used to generate the cache key.
            model (str): The model identifier used to generate the cache key.
            metadata (Dict[str, Any], optional): Stable request parameters (e.g., temperature, max_tokens, top_p, system_prompt) included when generating the cache key.
        
        Returns:
            CacheEntry: The cached entry if present, `None` otherwise.
        """

        if not self.redis_client:
            return None

        cache_key = self._generate_cache_key(prompt, model, metadata)

        try:
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode("utf-8")
                entry_dict = json.loads(cached_data)
                entry = CacheEntry.from_dict(entry_dict)

                # Update stats
                self.hits += 1
                self.total_cost_saved += entry.cost_estimate
                self.total_tokens_saved += entry.token_count

                self.logger.debug(f"Cache hit for model {model}")
                return entry
            else:
                self.misses += 1
                self.logger.debug(f"Cache miss for model {model}")
                return None

        except Exception as e:
            self.logger.error(f"Error retrieving from cache: {e}")
            return None

    async def set(
        self,
        prompt: str,
        response: str,
        model: str,
        token_count: int,
        cost_estimate: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Store a prompt-response pair in the cache with associated metadata and TTL.
        
        Parameters:
            prompt (str): The prompt text used to generate the response.
            response (str): The LLM-generated response to cache.
            model (str): The model identifier associated with this response.
            token_count (int): Number of tokens consumed to produce the response.
            cost_estimate (float): Estimated cost for producing the response.
            metadata (Dict[str, Any]): Optional additional data that influences cache key stability (e.g., temperature, max_tokens).
            ttl_seconds (int): Optional time-to-live in seconds for this cache entry; falls back to the cache's default TTL when omitted.
        
        Returns:
            bool: `True` if the entry was successfully stored in the cache, `False` otherwise.
        """

        if not self.redis_client:
            return False

        cache_key = self._generate_cache_key(prompt, model, metadata)
        ttl = ttl_seconds or self.default_ttl

        try:
            entry = CacheEntry(
                prompt_hash=cache_key.replace(self.key_prefix, ""),
                response=response,
                model=model,
                timestamp=datetime.now(),
                token_count=token_count,
                cost_estimate=cost_estimate,
                metadata=metadata or {},
                ttl_seconds=ttl,
            )

            # Store in Redis with TTL
            await self.redis_client.setex(cache_key, ttl, json.dumps(entry.to_dict()))

            self.logger.debug(f"Cached response for model {model} (TTL: {ttl}s)")

            # Check cache size and cleanup if needed
            await self._cleanup_if_needed()

            return True

        except Exception as e:
            self.logger.error(f"Error storing in cache: {e}")
            return False

    async def delete(
        self, prompt: str, model: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Delete the cache entry for a given prompt and model.
        
        Parameters:
            prompt: The prompt text whose cached response should be removed.
            model: The model identifier used when the entry was stored.
            metadata: Optional request metadata that affects the cache key (e.g., temperature, max_tokens, system prompt).
        
        Returns:
            `true` if an entry was deleted, `false` otherwise.
        """

        if not self.redis_client:
            return False

        cache_key = self._generate_cache_key(prompt, model, metadata)

        try:
            result = await self.redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {e}")
            return False

    async def clear_model_cache(self, model: str) -> int:
        """
        Remove all cache entries associated with the given model.
        
        Returns:
            int: Number of cache entries deleted; 0 if Redis is unavailable or an error occurred.
        """

        if not self.redis_client:
            return 0

        try:
            # Find all keys for this model
            pattern = f"{self.key_prefix}*"
            keys = []

            async for key in self.redis_client.scan_iter(match=pattern):
                # Check if this key belongs to the specified model
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    entry_dict = json.loads(cached_data)
                    if entry_dict.get("model") == model:
                        keys.append(key)

            # Delete all found keys
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.logger.info(f"Cleared {deleted} cache entries for model {model}")
                return deleted

            return 0

        except Exception as e:
            self.logger.error(f"Error clearing model cache: {e}")
            return 0

    async def get_stats(self) -> CacheStats:
        """
        Collect aggregated cache metrics including counts, hit rate, size, cost and token savings, and oldest/newest entry timestamps.
        
        Returns:
            CacheStats: Aggregated statistics containing:
                - total_entries (int): Number of cached entries.
                - hit_rate (float): Fraction of requests served from cache (0.0 to 1.0).
                - total_cost_saved (float): Cumulative estimated cost saved by cache hits.
                - total_tokens_saved (int): Cumulative tokens saved by cache hits.
                - cache_size_mb (float): Total cache payload size in megabytes.
                - oldest_entry (datetime | None): Timestamp of the oldest cached entry, or None if unavailable.
                - newest_entry (datetime | None): Timestamp of the newest cached entry, or None if unavailable.
        """

        if not self.redis_client:
            return CacheStats(0, 0.0, 0.0, 0, 0.0, None, None)

        try:
            # Count total entries
            pattern = f"{self.key_prefix}*"
            total_entries = 0
            total_size_bytes = 0
            oldest_entry = None
            newest_entry = None

            async for key in self.redis_client.scan_iter(match=pattern):
                total_entries += 1

                # Get entry to check timestamp and calculate size
                cached_data = await self.redis_client.get(key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode("utf-8")
                    total_size_bytes += len(cached_data.encode())

                    try:
                        entry_dict = json.loads(cached_data)
                        timestamp = datetime.fromisoformat(entry_dict["timestamp"])

                        if oldest_entry is None or timestamp < oldest_entry:
                            oldest_entry = timestamp
                        if newest_entry is None or timestamp > newest_entry:
                            newest_entry = timestamp
                    except:
                        pass

            # Calculate hit rate
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0

            # Convert size to MB
            cache_size_mb = total_size_bytes / (1024 * 1024)

            return CacheStats(
                total_entries=total_entries,
                hit_rate=hit_rate,
                total_cost_saved=self.total_cost_saved,
                total_tokens_saved=self.total_tokens_saved,
                cache_size_mb=cache_size_mb,
                oldest_entry=oldest_entry,
                newest_entry=newest_entry,
            )

        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return CacheStats(0, 0.0, 0.0, 0, 0.0, None, None)

    async def _cleanup_if_needed(self) -> None:
        """
        Remove old cache entries when the cache exceeds the configured maximum size.
        
        When the total cache size in MB is greater than `self.max_cache_size_mb`, this routine scans stored entries, identifies entries by their stored timestamp, and deletes the oldest 25% of entries to reduce size. Corrupted entries (invalid JSON or missing/invalid timestamp) are removed during the scan. Information and error conditions are logged.
        """

        try:
            stats = await self.get_stats()

            if stats.cache_size_mb > self.max_cache_size_mb:
                self.logger.info(
                    f"Cache size ({stats.cache_size_mb:.1f}MB) exceeds limit ({self.max_cache_size_mb}MB), cleaning up..."
                )

                # Get all entries with timestamps
                entries_with_timestamps = []
                pattern = f"{self.key_prefix}*"

                async for key in self.redis_client.scan_iter(match=pattern):
                    cached_data = await self.redis_client.get(key)
                    if cached_data:
                        if isinstance(cached_data, bytes):
                            cached_data = cached_data.decode("utf-8")
                        try:
                            entry_dict = json.loads(cached_data)
                            timestamp = datetime.fromisoformat(entry_dict["timestamp"])
                            entries_with_timestamps.append((key, timestamp))
                        except:
                            # Delete corrupted entries
                            await self.redis_client.delete(key)

                # Sort by timestamp (oldest first)
                entries_with_timestamps.sort(key=lambda x: x[1])

                # Delete oldest 25% of entries
                entries_to_delete = len(entries_with_timestamps) // 4
                if entries_to_delete > 0:
                    keys_to_delete = [
                        entry[0]
                        for entry in entries_with_timestamps[:entries_to_delete]
                    ]
                    deleted = await self.redis_client.delete(*keys_to_delete)
                    self.logger.info(f"Cleaned up {deleted} old cache entries")

        except Exception as e:
            self.logger.error(f"Error during cache cleanup: {e}")

    async def close(self) -> None:
        """
        Close the Redis client connection if one is established.
        
        If the cache has an active Redis client, close its connection and log the action; otherwise do nothing.
        """
        if self.redis_client:
            await self.redis_client.close()
            self.logger.info("Redis connection closed")


# Global cache instance
_llm_cache: Optional[LLMCache] = None


async def get_llm_cache() -> LLMCache:
    """Get the global LLM cache instance."""
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache()
        await _llm_cache.connect()
    return _llm_cache


async def cached_llm_request(
    prompt: str,
    model: str,
    llm_function: Callable[[str], Awaitable[str]],
    token_count_estimate: int = 0,
    cost_estimate: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
    ttl_seconds: Optional[int] = None,
) -> Tuple[str, bool]:
    """
    Use the cache to return a cached LLM response for the given prompt and model, or call the provided async LLM function and cache its result.
    
    Parameters:
        prompt (str): The prompt text to query the LLM with.
        model (str): Model identifier used as part of the cache key.
        llm_function (Callable[[str], Awaitable[str]]): Async callable that accepts the prompt and returns the response string.
        token_count_estimate (int): Estimated token count for the response; used for cache metrics.
        cost_estimate (float): Estimated cost for the request; used for cache metrics.
        metadata (Dict[str, Any] | None): Optional metadata affecting cache key generation (e.g., temperature, system prompt).
        ttl_seconds (int | None): Optional TTL override (seconds) for the cached entry.
    
    Returns:
        Tuple[str, bool]: The LLM response string and a boolean indicating whether the response was served from cache (`True`) or obtained from the LLM and then cached (`False`).
    """

    cache = await get_llm_cache()

    # Try to get from cache first
    cached_entry = await cache.get(prompt, model, metadata)

    if cached_entry:
        return cached_entry.response, True

    # Not in cache, make the request
    try:
        response = await llm_function(prompt)

        # Cache the response
        await cache.set(
            prompt=prompt,
            response=response,
            model=model,
            token_count=token_count_estimate,
            cost_estimate=cost_estimate,
            metadata=metadata,
            ttl_seconds=ttl_seconds,
        )

        return response, False

    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        raise