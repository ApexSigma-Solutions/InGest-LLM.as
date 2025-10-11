"""
InGest-LLM.as Test Utilities - Mocks

This module provides mock implementations of external services and dependencies
for comprehensive testing of the InGest-LLM service.
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from typing import Dict, Any, List, Optional
import json
import time


class MockDatabase:
    """Mock database client with call tracking and configurable responses."""

    def __init__(self):
        self.calls = []
        self.data = {}
        self.connected = True

    async def connect(self):
        """Mock database connection."""
        self.calls.append(("connect", {}))
        return True

    async def disconnect(self):
        """Mock database disconnection."""
        self.calls.append(("disconnect", {}))
        self.connected = False

    async def execute(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Mock query execution with configurable responses."""
        self.calls.append(("execute", {"query": query, "params": params}))

        # Simulate different query types
        if "SELECT" in query.upper():
            return self._mock_select_results(query, params)
        elif "INSERT" in query.upper():
            return self._mock_insert_results(query, params)
        elif "UPDATE" in query.upper():
            return self._mock_update_results(query, params)
        elif "DELETE" in query.upper():
            return self._mock_delete_results(query, params)

        return []

    async def transaction(self):
        """Mock transaction context manager."""
        return self

    async def commit(self):
        """Mock transaction commit."""
        self.calls.append(("commit", {}))
        return True

    async def rollback(self):
        """Mock transaction rollback."""
        self.calls.append(("rollback", {}))
        return True

    def _mock_select_results(self, query: str, params: Optional[Dict]) -> List[Dict]:
        """Generate mock SELECT results."""
        if "documents" in query.lower():
            return [
                {
                    "id": "mock-doc-1",
                    "content": "Mock document content",
                    "metadata": {"source": "test"},
                    "created_at": "2025-01-01T00:00:00Z"
                }
            ]
        return []

    def _mock_insert_results(self, query: str, params: Optional[Dict]) -> List[Dict]:
        """Generate mock INSERT results."""
        return [{"id": f"mock-id-{int(time.time())}"}]

    def _mock_update_results(self, query: str, params: Optional[Dict]) -> List[Dict]:
        """Generate mock UPDATE results."""
        return [{"affected_rows": 1}]

    def _mock_delete_results(self, query: str, params: Optional[Dict]) -> List[Dict]:
        """Generate mock DELETE results."""
        return [{"affected_rows": 1}]


class MockRedis:
    """Mock Redis client with TTL support and call tracking."""

    def __init__(self):
        self.data = {}
        self.calls = []
        self.connected = True

    async def get(self, key: str) -> Optional[bytes]:
        """Mock Redis GET operation."""
        self.calls.append(("get", {"key": key}))
        return self.data.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Mock Redis SET operation with optional expiration."""
        self.calls.append(("set", {"key": key, "value": value, "ex": ex}))
        self.data[key] = value.encode() if isinstance(value, str) else value
        return True

    async def setex(self, key: str, time: int, value: Any) -> bool:
        """Mock Redis SETEX operation."""
        return await self.set(key, value, ex=time)

    async def delete(self, key: str) -> int:
        """Mock Redis DELETE operation."""
        self.calls.append(("delete", {"key": key}))
        if key in self.data:
            del self.data[key]
            return 1
        return 0

    async def exists(self, key: str) -> int:
        """Mock Redis EXISTS operation."""
        self.calls.append(("exists", {"key": key}))
        return 1 if key in self.data else 0

    async def expire(self, key: str, time: int) -> int:
        """Mock Redis EXPIRE operation."""
        self.calls.append(("expire", {"key": key, "time": time}))
        return 1 if key in self.data else 0

    async def ttl(self, key: str) -> int:
        """Mock Redis TTL operation."""
        self.calls.append(("ttl", {"key": key}))
        return 3600 if key in self.data else -2

    async def ping(self) -> str:
        """Mock Redis PING operation."""
        self.calls.append(("ping", {}))
        return "PONG"


class MockVectorStore:
    """Mock vector store client for testing embeddings and similarity search."""

    def __init__(self):
        self.collections = {}
        self.calls = []

    async def create_collection(self, name: str, vector_size: int = 384) -> bool:
        """Mock collection creation."""
        self.calls.append(("create_collection", {"name": name, "vector_size": vector_size}))
        self.collections[name] = {"vectors": [], "metadata": {}}
        return True

    async def delete_collection(self, name: str) -> bool:
        """Mock collection deletion."""
        self.calls.append(("delete_collection", {"name": name}))
        if name in self.collections:
            del self.collections[name]
            return True
        return False

    async def upsert(self, collection_name: str, vectors: List[Dict]) -> bool:
        """Mock vector upsert operation."""
        self.calls.append(("upsert", {"collection": collection_name, "count": len(vectors)}))
        if collection_name in self.collections:
            self.collections[collection_name]["vectors"].extend(vectors)
            return True
        return False

    async def search(self, collection_name: str, query_vector: List[float],
                    limit: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        """Mock vector similarity search."""
        self.calls.append(("search", {
            "collection": collection_name,
            "query_vector": query_vector[:5],  # Log first 5 elements
            "limit": limit,
            "filters": filters
        }))

        if collection_name not in self.collections:
            return []

        # Return mock results based on limit
        results = []
        for i in range(min(limit, len(self.collections[collection_name]["vectors"]))):
            results.append({
                "id": f"result-{i}",
                "score": 0.95 - (i * 0.05),  # Decreasing similarity scores
                "metadata": {"source": "test", "type": "document"},
                "content": f"Mock search result {i}"
            })

        return results

    async def delete(self, collection_name: str, ids: List[str]) -> bool:
        """Mock vector deletion."""
        self.calls.append(("delete", {"collection": collection_name, "ids": ids}))
        if collection_name in self.collections:
            vectors = self.collections[collection_name]["vectors"]
            self.collections[collection_name]["vectors"] = [
                v for v in vectors if v.get("id") not in ids
            ]
            return True
        return False


class MockLLMService:
    """Mock LLM service for testing text generation and processing."""

    def __init__(self):
        self.calls = []
        self.responses = {
            "generate": "This is a mock LLM response for testing purposes.",
            "summarize": "This is a mock summary of the provided text.",
            "analyze": "Mock analysis result with key insights."
        }

    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Mock text generation."""
        self.calls.append(("generate_response", {"prompt": prompt[:50], "kwargs": kwargs}))
        return self.responses["generate"]

    async def summarize_text(self, text: str, **kwargs) -> str:
        """Mock text summarization."""
        self.calls.append(("summarize_text", {"text_length": len(text), "kwargs": kwargs}))
        return self.responses["summarize"]

    async def analyze_sentiment(self, text: str, **kwargs) -> Dict:
        """Mock sentiment analysis."""
        self.calls.append(("analyze_sentiment", {"text_length": len(text), "kwargs": kwargs}))
        return {
            "sentiment": "positive",
            "confidence": 0.85,
            "scores": {"positive": 0.8, "negative": 0.1, "neutral": 0.1}
        }

    async def extract_keywords(self, text: str, **kwargs) -> List[str]:
        """Mock keyword extraction."""
        self.calls.append(("extract_keywords", {"text_length": len(text), "kwargs": kwargs}))
        return ["artificial intelligence", "machine learning", "technology"]


class MockHTTPClient:
    """Mock HTTP client for testing external API integrations."""

    def __init__(self):
        self.calls = []
        self.responses = {}

    def set_response(self, url: str, method: str = "GET", response: Dict = None):
        """Configure mock response for specific URL and method."""
        key = f"{method}:{url}"
        self.responses[key] = response or {"status": "success", "data": {}}

    async def get(self, url: str, **kwargs) -> Dict:
        """Mock GET request."""
        self.calls.append(("GET", {"url": url, "kwargs": kwargs}))
        key = f"GET:{url}"
        return self.responses.get(key, {"status": "success", "data": {}})

    async def post(self, url: str, data: Any = None, **kwargs) -> Dict:
        """Mock POST request."""
        self.calls.append(("POST", {"url": url, "data": data, "kwargs": kwargs}))
        key = f"POST:{url}"
        return self.responses.get(key, {"status": "success", "data": {"id": "mock-id"}})

    async def put(self, url: str, data: Any = None, **kwargs) -> Dict:
        """Mock PUT request."""
        self.calls.append(("PUT", {"url": url, "data": data, "kwargs": kwargs}))
        key = f"PUT:{url}"
        return self.responses.get(key, {"status": "success", "data": {"updated": True}})

    async def delete(self, url: str, **kwargs) -> Dict:
        """Mock DELETE request."""
        self.calls.append(("DELETE", {"url": url, "kwargs": kwargs}))
        key = f"DELETE:{url}"
        return self.responses.get(key, {"status": "success", "data": {"deleted": True}})


class MockMessageQueue:
    """Mock message queue for testing async communication."""

    def __init__(self):
        self.queues = {}
        self.calls = []

    async def publish(self, queue: str, message: Any) -> bool:
        """Mock message publishing."""
        self.calls.append(("publish", {"queue": queue, "message": message}))
        if queue not in self.queues:
            self.queues[queue] = []
        self.queues[queue].append(message)
        return True

    async def consume(self, queue: str) -> List[Any]:
        """Mock message consumption."""
        self.calls.append(("consume", {"queue": queue}))
        return self.queues.get(queue, [])

    async def acknowledge(self, queue: str, message_id: str) -> bool:
        """Mock message acknowledgement."""
        self.calls.append(("acknowledge", {"queue": queue, "message_id": message_id}))
        return True

    async def purge(self, queue: str) -> int:
        """Mock queue purging."""
        self.calls.append(("purge", {"queue": queue}))
        if queue in self.queues:
            count = len(self.queues[queue])
            self.queues[queue].clear()
            return count
        return 0