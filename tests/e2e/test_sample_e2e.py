"""
End-to-end tests for InGest-LLM.as complete workflows.

These tests simulate real user scenarios and verify the complete system
functionality from ingestion to search and retrieval.
"""

import pytest
import pytest_asyncio
from typing import Dict, Any, List
import time
import json
import asyncio

# Import test utilities
from tests.utils.factories import (
    create_document_data,
    create_batch_documents,
    create_query_data,
    create_search_test_suite
)


class TestDocumentIngestionWorkflow:
    """Test complete document ingestion workflows."""

    @pytest.mark.e2e
    async def test_complete_document_lifecycle(self, e2e_workflow_context):
        """Test complete document lifecycle from ingestion to search."""
        client = e2e_workflow_context["client"]
        documents = e2e_workflow_context["documents"]

        # Step 1: Ingest document via API
        document = documents[0]
        response = client.post(
            "/api/v1/documents",
            json=document,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 201
        ingestion_result = response.json()
        assert "document_id" in ingestion_result
        document_id = ingestion_result["document_id"]

        # Step 2: Verify document is searchable
        search_query = create_query_data(query_text="artificial intelligence")
        response = client.post(
            "/api/v1/search",
            json=search_query,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 200
        search_results = response.json()
        assert len(search_results["results"]) > 0

        # Verify our document is in results
        document_found = any(r["document_id"] == document_id for r in search_results["results"])
        assert document_found, "Ingested document should be searchable"

        # Step 3: Retrieve document details
        response = client.get(
            f"/api/v1/documents/{document_id}",
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 200
        retrieved_doc = response.json()
        assert retrieved_doc["content"] == document["content"]
        assert retrieved_doc["metadata"]["source"] == document["metadata"]["source"]

    @pytest.mark.e2e
    async def test_batch_ingestion_workflow(self, e2e_workflow_context):
        """Test batch document ingestion workflow."""
        client = e2e_workflow_context["client"]
        documents = create_batch_documents(count=10)

        # Ingest batch via API
        response = client.post(
            "/api/v1/documents/batch",
            json={"documents": documents},
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 201
        batch_result = response.json()
        assert len(batch_result["results"]) == 10
        assert all(r["status"] == "ingested" for r in batch_result["results"])

        # Verify all documents are searchable
        search_query = create_query_data(query_text="batch test document")
        response = client.post(
            "/api/v1/search",
            json=search_query,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 200
        search_results = response.json()
        assert len(search_results["results"]) >= 5  # At least some should match

    @pytest.mark.e2e
    async def test_document_update_workflow(self, e2e_workflow_context):
        """Test document update workflow."""
        client = e2e_workflow_context["client"]
        document = create_document_data()

        # Create document
        response = client.post(
            "/api/v1/documents",
            json=document,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )
        document_id = response.json()["document_id"]

        # Update document
        updated_content = "This is updated content for the document."
        update_data = {
            "content": updated_content,
            "metadata": {"updated": True, **document["metadata"]}
        }

        response = client.put(
            f"/api/v1/documents/{document_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        assert response.status_code == 200

        # Verify update
        response = client.get(
            f"/api/v1/documents/{document_id}",
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        retrieved_doc = response.json()
        assert retrieved_doc["content"] == updated_content
        assert retrieved_doc["metadata"]["updated"] is True


class TestSearchAndRetrievalWorkflow:
    """Test complete search and retrieval workflows."""

    @pytest.mark.e2e
    async def test_semantic_search_workflow(self, e2e_workflow_context):
        """Test semantic search workflow with natural language queries."""
        client = e2e_workflow_context["client"]

        # First ingest diverse documents
        documents = create_search_test_suite()["documents"]
        for doc in documents:
            response = client.post(
                "/api/v1/documents",
                json=doc,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )
            assert response.status_code == 201

        # Test various search queries
        test_queries = [
            ("python programming tutorial", "Should find programming document"),
            ("machine learning neural networks", "Should find AI/ML document"),
            ("javascript react web development", "Should find web development document"),
            ("database sql optimization", "Should find database document"),
            ("nonexistent topic search", "Should return empty or low results")
        ]

        for query_text, description in test_queries:
            search_query = create_query_data(query_text=query_text)

            response = client.post(
                "/api/v1/search",
                json=search_query,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

            assert response.status_code == 200, f"Search failed for: {description}"
            results = response.json()

            if "nonexistent" not in query_text:
                assert len(results["results"]) > 0, f"No results for: {description}"
                # Verify result structure
                for result in results["results"]:
                    assert "document_id" in result
                    assert "score" in result
                    assert "content" in result
                    assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.e2e
    async def test_filtered_search_workflow(self, e2e_workflow_context):
        """Test search with metadata filters."""
        client = e2e_workflow_context["client"]

        # Ingest documents with different categories
        documents = [
            create_document_data(
                content="Python programming fundamentals",
                metadata={"category": "programming", "language": "python"}
            ),
            create_document_data(
                content="Machine learning algorithms",
                metadata={"category": "ai", "topic": "ml"}
            ),
            create_document_data(
                content="Web development with JavaScript",
                metadata={"category": "web", "language": "javascript"}
            )
        ]

        for doc in documents:
            client.post(
                "/api/v1/documents",
                json=doc,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

        # Search with category filter
        search_query = create_query_data(
            query_text="programming",
            filters={"category": "programming"}
        )

        response = client.post(
            "/api/v1/search",
            json=search_query,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        results = response.json()
        assert len(results["results"]) > 0

        # All results should match the filter
        for result in results["results"]:
            assert result["metadata"]["category"] == "programming"

    @pytest.mark.e2e
    async def test_search_performance_workflow(self, e2e_workflow_context):
        """Test search performance under load."""
        client = e2e_workflow_context["client"]

        # Ingest larger dataset
        documents = create_batch_documents(count=50)
        for doc in documents:
            client.post(
                "/api/v1/documents",
                json=doc,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

        # Perform multiple searches
        search_queries = [
            create_query_data(query_text=f"performance test query {i}")
            for i in range(10)
        ]

        start_time = time.time()
        all_results = []

        for query in search_queries:
            response = client.post(
                "/api/v1/search",
                json=query,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )
            results = response.json()
            all_results.extend(results["results"])

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        assert duration < 60, f"Searches took too long: {duration}s"
        avg_search_time = duration / len(search_queries)
        assert avg_search_time < 3.0, f"Average search time too slow: {avg_search_time}s"


class TestUserInteractionWorkflow:
    """Test complete user interaction workflows."""

    @pytest.mark.e2e
    async def test_user_document_management_workflow(self, e2e_workflow_context):
        """Test complete user document management workflow."""
        client = e2e_workflow_context["client"]
        user = e2e_workflow_context["user"]

        # Create user session
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user["username"], "password": "testpass"}
        )

        # Assuming login succeeds or we mock it
        if response.status_code == 200:
            auth_token = response.json()["token"]
        else:
            # Use mock token for testing
            auth_token = e2e_workflow_context["auth_token"]

        headers = {"Authorization": f"Bearer {auth_token}"}

        # User uploads multiple documents
        documents = create_batch_documents(count=5)
        uploaded_ids = []

        for doc in documents:
            response = client.post("/api/v1/documents", json=doc, headers=headers)
            assert response.status_code == 201
            uploaded_ids.append(response.json()["document_id"])

        # User searches their documents
        search_query = create_query_data(query_text="test document")
        response = client.post("/api/v1/search", json=search_query, headers=headers)

        assert response.status_code == 200
        results = response.json()
        assert len(results["results"]) > 0

        # User retrieves specific document
        doc_id = uploaded_ids[0]
        response = client.get(f"/api/v1/documents/{doc_id}", headers=headers)

        assert response.status_code == 200
        retrieved = response.json()
        assert retrieved["id"] == doc_id

        # User updates document
        update_data = {"metadata": {"favorite": True}}
        response = client.patch(f"/api/v1/documents/{doc_id}", json=update_data, headers=headers)

        assert response.status_code == 200

        # User deletes a document
        response = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 204

        # Verify deletion
        response = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 404

    @pytest.mark.e2e
    async def test_concurrent_user_workflows(self, e2e_workflow_context):
        """Test concurrent user workflows."""
        client = e2e_workflow_context["client"]

        async def user_workflow(user_id: int):
            """Simulate a single user's workflow."""
            documents = create_batch_documents(count=3)
            uploaded_ids = []

            # Upload documents
            for doc in documents:
                doc["metadata"]["user_id"] = user_id
                response = client.post(
                    "/api/v1/documents",
                    json=doc,
                    headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
                )
                if response.status_code == 201:
                    uploaded_ids.append(response.json()["document_id"])

            # Search documents
            search_query = create_query_data(
                query_text=f"user {user_id} documents",
                filters={"user_id": user_id}
            )

            response = client.post(
                "/api/v1/search",
                json=search_query,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

            return len(uploaded_ids) if response.status_code == 200 else 0

        # Run concurrent workflows
        tasks = [user_workflow(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all workflows completed successfully
        assert all(r > 0 for r in results), "Some user workflows failed"


class TestSystemResilienceWorkflow:
    """Test system resilience and error handling workflows."""

    @pytest.mark.e2e
    async def test_system_recovery_workflow(self, e2e_workflow_context):
        """Test system recovery after simulated failures."""
        client = e2e_workflow_context["client"]

        # Simulate system under load
        documents = create_batch_documents(count=100)

        # Attempt to ingest large batch
        response = client.post(
            "/api/v1/documents/batch",
            json={"documents": documents},
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        # System should handle load gracefully
        if response.status_code == 201:
            batch_result = response.json()
            successful_ingests = sum(1 for r in batch_result["results"] if r["status"] == "ingested")
            assert successful_ingests > 80  # At least 80% success rate
        else:
            # If batch fails, try individual ingests
            successful_count = 0
            for doc in documents[:20]:  # Test first 20
                response = client.post(
                    "/api/v1/documents",
                    json=doc,
                    headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
                )
                if response.status_code == 201:
                    successful_count += 1

            assert successful_count > 15  # At least 75% success rate

    @pytest.mark.e2e
    async def test_data_consistency_workflow(self, e2e_workflow_context):
        """Test data consistency across system components."""
        client = e2e_workflow_context["client"]
        document = create_document_data()

        # Ingest document
        response = client.post(
            "/api/v1/documents",
            json=document,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        document_id = response.json()["document_id"]

        # Verify consistency across multiple retrievals
        for _ in range(5):
            response = client.get(
                f"/api/v1/documents/{document_id}",
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

            assert response.status_code == 200
            retrieved = response.json()

            # Data should be consistent
            assert retrieved["content"] == document["content"]
            assert retrieved["metadata"]["source"] == document["metadata"]["source"]

        # Verify search consistency
        search_query = create_query_data(query_text=document["content"][:50])
        response = client.post(
            "/api/v1/search",
            json=search_query,
            headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
        )

        results = response.json()
        document_in_search = any(r["document_id"] == document_id for r in results["results"])
        assert document_in_search, "Document should be consistently searchable"


class TestAPIPerformanceWorkflow:
    """Test API performance and scalability workflows."""

    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_api_performance_under_load(self, e2e_workflow_context):
        """Test API performance under sustained load."""
        client = e2e_workflow_context["client"]

        # Setup: Ingest test documents
        documents = create_batch_documents(count=20)
        for doc in documents:
            client.post(
                "/api/v1/documents",
                json=doc,
                headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
            )

        # Load test: Multiple concurrent searches
        async def search_worker(worker_id: int):
            """Worker function for concurrent searches."""
            search_times = []

            for i in range(10):
                query = create_query_data(query_text=f"load test query {worker_id}-{i}")
                start_time = time.time()

                response = client.post(
                    "/api/v1/search",
                    json=query,
                    headers={"Authorization": f"Bearer {e2e_workflow_context['auth_token']}"}
                )

                end_time = time.time()
                search_times.append(end_time - start_time)

                assert response.status_code == 200

            return search_times

        # Run concurrent workers
        worker_tasks = [search_worker(i) for i in range(5)]
        results = await asyncio.gather(*worker_tasks)

        # Analyze performance
        all_times = [time for worker_times in results for time in worker_times]
        avg_response_time = sum(all_times) / len(all_times)
        max_response_time = max(all_times)
        min_response_time = min(all_times)

        # Performance assertions
        assert avg_response_time < 2.0, f"Average response time too slow: {avg_response_time}s"
        assert max_response_time < 5.0, f"Max response time too slow: {max_response_time}s"
        assert min_response_time < 0.5, f"Min response time too slow: {min_response_time}s"

        print(f"Performance Results: Avg={avg_response_time:.2f}s, Min={min_response_time:.2f}s, Max={max_response_time:.2f}s")