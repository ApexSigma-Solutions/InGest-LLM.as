# Embedding Agent Implementation Plan

**Date**: 2025-08-24  
**Project**: ApexSigma Ecosystem - Embedding Agent  
**Status**: Ready for Implementation

---

## Quick Start Implementation

### Project Structure
```
embedding-agent/
├── src/
│   ├── embedding_agent/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py               # Configuration
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py           # API endpoints
│   │   │   └── models.py           # Pydantic models
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── engine.py           # Embedding engine
│   │   │   ├── batch_processor.py  # Batch operations
│   │   │   ├── cache_manager.py    # Multi-level caching
│   │   │   └── quality_validator.py # Quality assurance
│   │   ├── backends/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Abstract backend
│   │   │   ├── lm_studio.py        # LM Studio backend
│   │   │   └── openai.py           # OpenAI backend
│   │   └── observability/
│   │       ├── __init__.py
│   │       ├── metrics.py          # Prometheus metrics
│   │       └── tracing.py          # Langfuse tracing
├── tests/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Phase 1: Minimum Viable Product (MVP)

### Step 1: Project Setup
```bash
# Create new project
mkdir embedding-agent
cd embedding-agent

# Initialize Poetry
poetry init --name embedding-agent --version 0.1.0
poetry add fastapi uvicorn redis openai httpx pydantic-settings
poetry add --group dev pytest pytest-asyncio black ruff mypy
```

### Step 2: Core API Implementation
```python
# src/embedding_agent/api/models.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EmbedRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    content_type: str = Field(default="text", pattern="^(text|code|documentation)$")
    model_preference: str = Field(default="auto", pattern="^(auto|text|code)$")
    cache: bool = Field(default=True)
    validate: bool = Field(default=False)

class EmbedBatchRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(..., min_items=1, max_items=100)
    batch_size: int = Field(default=32, ge=1, le=64)
    parallel: bool = Field(default=True)

class EmbeddingResult(BaseModel):
    embedding: List[float]
    model_used: str
    processing_time_ms: int
    cache_hit: bool
    quality_score: Optional[float] = None
```

### Step 3: LM Studio Backend Integration
```python
# src/embedding_agent/backends/lm_studio.py
from typing import List, Optional
from openai import AsyncOpenAI
from .base import EmbeddingBackend
from ..api.models import EmbeddingResult

class LMStudioBackend(EmbeddingBackend):
    def __init__(self, base_url: str, api_key: str = "not-needed"):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.available_models = []
    
    async def generate_embedding(self, content: str, model: str) -> EmbeddingResult:
        start_time = time.time()
        
        response = await self.client.embeddings.create(
            model=model,
            input=content
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return EmbeddingResult(
            embedding=response.data[0].embedding,
            model_used=model,
            processing_time_ms=processing_time,
            cache_hit=False
        )
```

### Step 4: Cache Integration
```python
# src/embedding_agent/core/cache_manager.py
import hashlib
import json
from typing import Optional, List
import redis.asyncio as redis

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.ttl = 3600  # 1 hour
    
    def _content_hash(self, content: str, model: str) -> str:
        """Generate cache key from content and model."""
        content_str = f"{content}:{model}"
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    async def get_cached_embedding(self, content: str, model: str) -> Optional[List[float]]:
        """Retrieve cached embedding."""
        key = f"embed:{self._content_hash(content, model)}"
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_embedding(self, content: str, model: str, embedding: List[float]):
        """Store embedding in cache."""
        key = f"embed:{self._content_hash(content, model)}"
        await self.redis.setex(key, self.ttl, json.dumps(embedding))
```

## Phase 2: Integration Testing

### Integration with InGest-LLM.as
```python
# Replace in InGest-LLM.as vectorizer.py
import httpx

class EmbeddingAgentClient:
    def __init__(self, base_url: str = "http://embedding-agent:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def generate_embedding(self, content: str, content_type: str) -> List[float]:
        response = await self.client.post(
            f"{self.base_url}/embed/single",
            json={
                "content": content,
                "content_type": content_type,
                "cache": True,
                "validate": False
            }
        )
        result = response.json()
        return result["embedding"]

# Update content_processor.py to use embedding agent
async def generate_content_embedding(content: str, content_type: str = "text") -> List[float]:
    if settings.embedding_agent_enabled:
        agent = EmbeddingAgentClient()
        return await agent.generate_embedding(content, content_type)
    else:
        # Fallback to direct LM Studio
        return await vectorizer.generate_embedding(content)
```

## Immediate Implementation Priority

### High Priority (Implement First)
1. **Basic FastAPI Service**: Core API with single embedding endpoint
2. **LM Studio Integration**: Direct replacement for current implementation
3. **Redis Caching**: Immediate performance improvement
4. **Docker Integration**: Deploy alongside existing services

### Medium Priority (Week 2)
1. **Batch Processing**: Handle multiple embeddings efficiently
2. **Quality Validation**: Ensure embedding consistency
3. **Monitoring**: Basic metrics and health checks

### Lower Priority (Future)
1. **Multiple Backends**: OpenAI fallback
2. **Advanced Caching**: Multi-level cache hierarchy
3. **A/B Testing**: Model comparison framework

## Quick Deployment

### Docker Compose Addition
```yaml
# Add to existing docker-compose.yml
services:
  embedding-agent:
    build: ./embedding-agent
    ports:
      - "8080:8080"
    environment:
      - LM_STUDIO_URL=http://host.docker.internal:1234
      - REDIS_URL=redis://redis:6379
    networks:
      - apexsigma_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Performance Expectations

### Before (Current State)
- **Single Embedding**: ~200-500ms
- **Batch of 10**: ~2-5 seconds (sequential)
- **Cache Miss Rate**: ~90% (limited caching)

### After (Phase 1 MVP)
- **Single Embedding**: ~50-200ms (with cache)
- **Batch of 10**: ~300-800ms (parallel + cache)
- **Cache Hit Rate**: ~70-80% (intelligent caching)

### After (Phase 2 Optimized)
- **Single Embedding**: ~10-50ms (L1 cache)
- **Batch of 100**: ~1-2 seconds (optimized batching)
- **Cache Hit Rate**: ~85-95% (multi-level cache)

---

## Decision Point

**Recommendation**: Start with **Phase 1 MVP** implementation immediately.

The embedding agent will:
1. **Immediate Value**: Reduce embedding latency by 60-80%
2. **Future-Proof**: Foundation for master knowledge graph ingestion
3. **Low Risk**: Drop-in replacement for existing embedding calls
4. **High Impact**: Benefits all current and future ingestion workflows

Would you like me to begin implementing the Phase 1 MVP embedding agent?
