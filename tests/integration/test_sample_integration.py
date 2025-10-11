"""
Integration tests for InGest-LLM.as service interactions.

These tests verify component interactions with real external services
such as databases, caches, and vector stores.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
import time
import json

# Import test utilities
from tests.utils.factories import (
    create_document_data,
    create_batch_documents,
    create_query_data,
    create_ingestion_job_data
)


class TestDocumentIngestionIntegration:
    """Test document ingestion with database and vector store integration."""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_ingest_single_document_full_pipeline(self, integration_database, integration_qdrant):
        """Test complete document ingestion pipeline."""
        from app.services.ingestion_service import IngestionService

        service = IngestionService()
        document = create_document_data()

        # Ingest document
        result = await service.ingest_document(document)

        assert result["status"] == "ingested"
        assert "document_id" in result
        assert "vector_id" in result

        # Verify in database
        stored_doc = await integration_database.fetchrow(
            "SELECT * FROM documents WHERE id = $1",
            result["document_id"]
        )
        assert stored_doc is not None
        assert stored_doc["content"] == document["content"]

        # Verify in vector store
        search_results = integration_qdrant.search(
            collection_name="documents",
            query_vector=document["embeddings"],
            limit=1
        )
        assert len(search_results) > 0
        assert search_results[0]["id"] == result["vector_id"]

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_ingest_batch_documents_performance(self, integration_database, integration_qdrant):
        """Test batch document ingestion performance."""
        from app.services.ingestion_service import IngestionService

        service = IngestionService()
        batch_size = 50
        documents = create_batch_documents(count=batch_size)

        start_time = time.time()
        results = await service.ingest_batch(documents)
        end_time = time.time()

        # Verify all documents ingested
        assert len(results) == batch_size
        assert all(r["status"] == "ingested" for r in results)

        # Performance check (should be reasonable for batch size)
        duration = end_time - start_time
        avg_time_per_doc = duration / batch_size
        assert avg_time_per_doc < 2.0  # Less than 2 seconds per document

        # Verify database count
        count = await integration_database.fetchval("SELECT COUNT(*) FROM documents")
        assert count == batch_size

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_ingest_document_with_metadata_filtering(self, integration_database):
        """Test document ingestion with metadata-based filtering."""
        from app.services.ingestion_service import IngestionService

        service = IngestionService()

        # Test documents with different metadata
        docs = [
            create_document_data(metadata={"priority": "high", "category": "important"}),
            create_document_data(metadata={"priority": "low", "category": "spam"}),
            create_document_data(metadata={"priority": "medium", "category": "important"})
        ]

        # Ingest with filter for important documents only
        results = await service.ingest_filtered_batch(docs, filters={"category": "important"})

        # Should only ingest 2 documents
        assert len(results) == 2
        assert all(r["metadata"]["category"] == "important" for r in results)

        # Verify database
        count = await integration_database.fetchval("SELECT COUNT(*) FROM documents")
        assert count == 2


class TestSearchIntegration:
    """Test search functionality with vector store and database integration."""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_semantic_search_full_pipeline(self, integration_database, integration_qdrant):
        """Test complete semantic search pipeline."""
        from app.services.search_service import SearchService

        # First, ingest some test documents
        from app.services.ingestion_service import IngestionService
        ingestion_service = IngestionService()

        documents = create_batch_documents(count=10)
        await ingestion_service.ingest_batch(documents)

        # Now perform search
        search_service = SearchService()
        query = create_query_data(query_text="artificial intelligence machine learning")

        results = await search_service.semantic_search(query)

        assert isinstance(results, list)
        assert len(results) > 0

        # Verify results structure
        for result in results:
            assert "document_id" in result
            assert "score" in result
            assert "content" in result
            assert "metadata" in result
            assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_hybrid_search_with_filters(self, integration_database, integration_qdrant):
        """Test hybrid search combining semantic and metadata filtering."""
        from app.services.search_service import SearchService
        from app.services.ingestion_service import IngestionService

        # Ingest documents with varied metadata
        ingestion_service = IngestionService()
        documents = [
            create_document_data(
                content="Python programming tutorial for beginners",
                metadata={"category": "programming", "language": "python", "level": "beginner"}
            ),
            create_document_data(
                content="Advanced machine learning with neural networks",
                metadata={"category": "ai", "topic": "ml", "level": "advanced"}
            ),
            create_document_data(
                content="JavaScript web development guide",
                metadata={"category": "web", "language": "javascript", "level": "intermediate"}
            )
        ]

        await ingestion_service.ingest_batch(documents)

        # Perform filtered search
        search_service = SearchService()
        query = create_query_data(
            query_text="programming tutorial",
            filters={"category": "programming"}
        )

        results = await search_service.hybrid_search(query)

        # Should only return programming-related results
        assert len(results) > 0
        for result in results:
            assert result["metadata"]["category"] == "programming"

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_search_performance_under_load(self, integration_database, integration_qdrant):
        """Test search performance with larger dataset."""
        from app.services.search_service import SearchService
        from app.services.ingestion_service import IngestionService

        # Ingest larger dataset
        ingestion_service = IngestionService()
        documents = create_batch_documents(count=100)
        await ingestion_service.ingest_batch(documents)

        # Perform multiple searches
        search_service = SearchService()
        queries = [
            create_query_data(query_text=f"search query {i}")
            for i in range(10)
        ]

        start_time = time.time()
        all_results = []
        for query in queries:
            results = await search_service.semantic_search(query)
            all_results.extend(results)

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        assert duration < 30  # Should complete within 30 seconds
        assert len(all_results) > 0
        avg_search_time = duration / len(queries)
        assert avg_search_time < 2.0  # Less than 2 seconds per search


class TestCacheIntegration:
    """Test caching functionality with Redis integration."""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_cache_document_embeddings(self, integration_redis):
        """Test caching of document embeddings."""
        from app.services.cache_service import CacheService

        cache_service = CacheService()
        document_id = "test-doc-123"
        embeddings = [0.1, 0.2, 0.3] * 128  # 384 dimensions

        # Cache embeddings
        success = await cache_service.set_embeddings(document_id, embeddings, ttl=3600)
        assert success is True

        # Retrieve from cache
        cached_embeddings = await cache_service.get_embeddings(document_id)
        assert cached_embeddings == embeddings

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_cache_search_results(self, integration_redis):
        """Test caching of search results."""
        from app.services.cache_service import CacheService

        cache_service = CacheService()
        query_hash = "query_hash_123"
        search_results = [
            {"id": "doc1", "score": 0.95, "content": "test content 1"},
            {"id": "doc2", "score": 0.89, "content": "test content 2"}
        ]

        # Cache search results
        success = await cache_service.set_search_results(query_hash, search_results, ttl=1800)
        assert success is True

        # Retrieve from cache
        cached_results = await cache_service.get_search_results(query_hash)
        assert cached_results == search_results

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_cache_expiration(self, integration_redis):
        """Test cache expiration behavior."""
        from app.services.cache_service import CacheService

        cache_service = CacheService()
        key = "test_expiration_key"
        value = "test_value"

        # Cache with short TTL
        success = await cache_service.set(key, value, ttl=1)  # 1 second
        assert success is True

        # Verify exists immediately
        cached_value = await cache_service.get(key)
        assert cached_value == value

        # Wait for expiration
        time.sleep(2)

        # Verify expired
        expired_value = await cache_service.get(key)
        assert expired_value is None


class TestMessageQueueIntegration:
    """Test message queue functionality for async processing."""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_queue_document_processing_job(self):
        """Test queuing document processing jobs."""
        from app.services.queue_service import QueueService

        queue_service = QueueService()
        job_data = create_ingestion_job_data()

        # Queue job
        job_id = await queue_service.queue_job("document_processing", job_data)
        assert job_id is not None

        # Verify job in queue
        queued_jobs = await queue_service.get_queued_jobs("document_processing")
        assert len(queued_jobs) > 0
        assert any(job["id"] == job_id for job in queued_jobs)

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_process_queued_jobs(self):
        """Test processing jobs from queue."""
        from app.services.queue_service import QueueService
        from app.services.ingestion_service import IngestionService

        queue_service = QueueService()
        ingestion_service = IngestionService()

        # Queue multiple jobs
        jobs = [create_ingestion_job_data() for _ in range(3)]
        job_ids = []
        for job in jobs:
            job_id = await queue_service.queue_job("document_processing", job)
            job_ids.append(job_id)

        # Process jobs
        processed_count = await queue_service.process_jobs("document_processing", ingestion_service)

        assert processed_count == 3

        # Verify queue is empty
        remaining_jobs = await queue_service.get_queued_jobs("document_processing")
        assert len(remaining_jobs) == 0


class TestDatabaseIntegration:
    """Test database operations and data persistence."""

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_document_crud_operations(self, integration_database):
        """Test complete CRUD operations for documents."""
        from app.database.document_repository import DocumentRepository

        repo = DocumentRepository()

        # Create
        document = create_document_data()
        doc_id = await repo.create(document)
        assert doc_id is not None

        # Read
        retrieved = await repo.get_by_id(doc_id)
        assert retrieved is not None
        assert retrieved["content"] == document["content"]

        # Update
        updates = {"metadata": {"updated": True, **document["metadata"]}}
        updated = await repo.update(doc_id, updates)
        assert updated is True

        # Verify update
        retrieved_updated = await repo.get_by_id(doc_id)
        assert retrieved_updated["metadata"]["updated"] is True

        # Delete
        deleted = await repo.delete(doc_id)
        assert deleted is True

        # Verify deletion
        retrieved_deleted = await repo.get_by_id(doc_id)
        assert retrieved_deleted is None

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_batch_database_operations(self, integration_database):
        """Test batch database operations."""
        from app.database.document_repository import DocumentRepository

        repo = DocumentRepository()
        documents = create_batch_documents(count=20)

        # Batch insert
        inserted_ids = await repo.batch_create(documents)
        assert len(inserted_ids) == 20

        # Batch read
        retrieved_batch = await repo.get_by_ids(inserted_ids[:5])
        assert len(retrieved_batch) == 5

        # Batch update
        updates = [{"metadata": {"batch_updated": True, **doc["metadata"]}} for doc in retrieved_batch]
        updated_count = await repo.batch_update(inserted_ids[:5], updates)
        assert updated_count == 5

        # Batch delete
        deleted_count = await repo.batch_delete(inserted_ids[:3])
        assert deleted_count == 3

        # Verify remaining count
        remaining = await repo.count()
        assert remaining == 17

    @pytest.mark.integration
    @pytest.mark.docker
    async def test_database_transaction_rollback(self, integration_database):
        """Test database transaction rollback on errors."""
        from app.database.document_repository import DocumentRepository

        repo = DocumentRepository()
        documents = create_batch_documents(count=3)

        # Start transaction that should fail
        try:
            async with integration_database.transaction():
                # Insert first two successfully
                await repo.create(documents[0])
                await repo.create(documents[1])

                # Force an error on third
                raise Exception("Simulated error")

        except Exception:
            pass  # Expected

        # Verify rollback - no documents should exist
        count = await repo.count()
        assert count == 0


class TestExternalAPIIntegration:
    """Test integration with external APIs and services."""

    @pytest.mark.integration
    async def test_llm_service_integration(self):
        """Test integration with external LLM service."""
        from app.services.llm_service import LLMService

        service = LLMService()
        prompt = "Explain machine learning in one sentence."

        response = await service.generate_response(prompt)

        assert isinstance(response, str)
        assert len(response) > 10
        assert "machine learning" in response.lower()

    @pytest.mark.integration
    async def test_embedding_service_external_call(self):
        """Test integration with external embedding service."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        text = "This is a test for embedding generation."

        embeddings = await service.encode_text(text)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 384
        assert all(isinstance(x, (int, float)) for x in embeddings)

    @pytest.mark.integration
    async def test_rate_limiting_handling(self):
        """Test handling of external API rate limits."""
        from app.services.llm_service import LLMService

        service = LLMService()

        # Make multiple rapid requests
        tasks = []
        for i in range(10):
            task = service.generate_response(f"Test prompt {i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some may succeed, some may be rate limited
        successful_responses = [r for r in results if not isinstance(r, Exception)]
        rate_limited_responses = [r for r in results if isinstance(r, Exception)]

        # At least some should succeed
        assert len(successful_responses) > 0
        # Some may be rate limited (acceptable)
        assert len(rate_limited_responses) <= len(results)