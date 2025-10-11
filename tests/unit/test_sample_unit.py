"""
Unit tests for InGest-LLM.as core functionality.

These tests focus on isolated components and functions without external dependencies.
All external services are mocked to ensure fast, reliable unit testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any
import json

# Import test utilities
from tests.utils.factories import (
    create_document_data,
    create_query_data,
    create_edge_case_documents
)
from tests.utils.mocks import MockLLMService, MockVectorStore


class TestDocumentProcessing:
    """Test document processing functionality."""

    @pytest.mark.unit
    def test_process_valid_document(self, mock_external_dependencies):
        """Test processing a valid document."""
        from app.services.document_processor import DocumentProcessor

        document = create_document_data()
        processor = DocumentProcessor()

        result = processor.process(document)

        assert result["status"] == "processed"
        assert "processed_at" in result
        assert result["document_id"] == document["id"]

    @pytest.mark.unit
    def test_process_empty_document_raises_error(self):
        """Test that empty documents raise appropriate errors."""
        from app.services.document_processor import DocumentProcessor

        document = create_document_data(content="")
        processor = DocumentProcessor()

        with pytest.raises(ValueError, match="empty content"):
            processor.process(document)

    @pytest.mark.unit
    @pytest.mark.parametrize("content_length", [100, 1000, 10000])
    def test_process_documents_various_sizes(self, content_length):
        """Test processing documents of various sizes."""
        from app.services.document_processor import DocumentProcessor

        long_content = "Sample content " * (content_length // 14)  # Approximate word count
        document = create_document_data(content=long_content)
        processor = DocumentProcessor()

        result = processor.process(document)

        assert result["status"] == "processed"
        assert result["word_count"] == len(long_content.split())

    @pytest.mark.unit
    def test_process_document_with_special_characters(self):
        """Test processing documents with special characters and unicode."""
        from app.services.document_processor import DocumentProcessor

        special_content = "Content with éñüñ 中文 🔥 🚀 special chars"
        document = create_document_data(content=special_content)
        processor = DocumentProcessor()

        result = processor.process(document)

        assert result["status"] == "processed"
        assert "unicode_detected" in result
        assert result["language_detected"] in ["mixed", "en", "zh"]

    @pytest.mark.unit
    def test_process_document_metadata_validation(self):
        """Test document metadata validation during processing."""
        from app.services.document_processor import DocumentProcessor

        # Test with missing required metadata
        document = create_document_data(metadata={})
        processor = DocumentProcessor()

        result = processor.process(document)

        # Should add default metadata
        assert "source" in result["metadata"]
        assert "processed_at" in result["metadata"]


class TestEmbeddingService:
    """Test embedding service functionality."""

    @pytest.mark.unit
    def test_generate_embeddings_for_text(self, mock_external_dependencies):
        """Test generating embeddings for text content."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        text = "This is a test document for embedding generation."

        embeddings = service.encode_text(text)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 384  # Expected embedding dimension
        assert all(isinstance(x, float) for x in embeddings)

    @pytest.mark.unit
    def test_generate_embeddings_batch(self, mock_external_dependencies):
        """Test batch embedding generation."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        texts = [
            "First test document",
            "Second test document",
            "Third test document"
        ]

        embeddings = service.encode_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    @pytest.mark.unit
    def test_embedding_similarity_calculation(self):
        """Test calculation of embedding similarity."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        # Create two similar embeddings
        emb1 = [1.0, 0.0, 0.0] * 128  # 384 dimensions
        emb2 = [0.9, 0.1, 0.0] * 128  # Similar but not identical

        similarity = service.calculate_similarity(emb1, emb2)

        assert 0.7 <= similarity <= 1.0  # Should be highly similar

    @pytest.mark.unit
    def test_embedding_dimension_validation(self):
        """Test validation of embedding dimensions."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        # Test with wrong dimension
        invalid_embedding = [1.0, 0.0, 0.0]  # Only 3 dimensions

        with pytest.raises(ValueError, match="dimension"):
            service.validate_embedding(invalid_embedding)


class TestVectorSearch:
    """Test vector search functionality."""

    @pytest.mark.unit
    def test_search_similar_documents(self, mock_external_dependencies):
        """Test searching for similar documents using vectors."""
        from app.services.vector_search import VectorSearchService

        service = VectorSearchService()
        query_embedding = [0.1, 0.2, 0.3] * 128  # 384 dimensions

        results = service.search_similar(query_embedding, top_k=5)

        assert isinstance(results, list)
        assert len(results) <= 5
        # Each result should have id, score, and metadata
        for result in results:
            assert "id" in result
            assert "score" in result
            assert "metadata" in result
            assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.unit
    def test_search_with_filters(self, mock_external_dependencies):
        """Test vector search with metadata filters."""
        from app.services.vector_search import VectorSearchService

        service = VectorSearchService()
        query_embedding = [0.1, 0.2, 0.3] * 128
        filters = {"category": "technology", "language": "en"}

        results = service.search_similar(
            query_embedding,
            filters=filters,
            top_k=3
        )

        assert isinstance(results, list)
        # All results should match the filters
        for result in results:
            assert result["metadata"].get("category") == "technology"
            assert result["metadata"].get("language") == "en"

    @pytest.mark.unit
    def test_search_empty_results(self, mock_external_dependencies):
        """Test search behavior when no results are found."""
        from app.services.vector_search import VectorSearchService

        service = VectorSearchService()
        # Use a very specific embedding that's unlikely to match
        query_embedding = [999.0] * 384

        results = service.search_similar(query_embedding, top_k=5)

        assert isinstance(results, list)
        assert len(results) == 0


class TestQueryProcessing:
    """Test query processing and validation."""

    @pytest.mark.unit
    def test_parse_search_query(self):
        """Test parsing of search query strings."""
        from app.services.query_processor import QueryProcessor

        processor = QueryProcessor()

        query_text = "artificial intelligence machine learning"
        parsed = processor.parse_query(query_text)

        assert parsed["original_query"] == query_text
        assert "tokens" in parsed
        assert "language" in parsed
        assert len(parsed["tokens"]) > 0

    @pytest.mark.unit
    def test_validate_query_filters(self):
        """Test validation of query filters."""
        from app.services.query_processor import QueryProcessor

        processor = QueryProcessor()

        valid_filters = {
            "category": "technology",
            "language": "en",
            "date_from": "2024-01-01"
        }

        result = processor.validate_filters(valid_filters)
        assert result["valid"] is True

    @pytest.mark.unit
    def test_validate_invalid_query_filters(self):
        """Test validation of invalid query filters."""
        from app.services.query_processor import QueryProcessor

        processor = QueryProcessor()

        invalid_filters = {
            "invalid_field": "value",
            "date_from": "invalid-date"
        }

        result = processor.validate_filters(invalid_filters)
        assert result["valid"] is False
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.unit
    @pytest.mark.parametrize("query_length", [10, 100, 500])
    def test_process_queries_various_lengths(self, query_length):
        """Test processing queries of various lengths."""
        from app.services.query_processor import QueryProcessor

        processor = QueryProcessor()
        long_query = "word " * query_length

        result = processor.process_query(long_query)

        assert result["status"] == "processed"
        assert "query_length" in result
        assert result["query_length"] == query_length


class TestDataValidation:
    """Test data validation utilities."""

    @pytest.mark.unit
    def test_validate_document_schema(self):
        """Test document schema validation."""
        from app.utils.validation import validate_document_schema

        valid_document = create_document_data()
        result = validate_document_schema(valid_document)

        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.unit
    def test_validate_invalid_document_schema(self):
        """Test validation of invalid document schemas."""
        from app.utils.validation import validate_document_schema

        invalid_document = {"content": "test"}  # Missing required fields
        result = validate_document_schema(invalid_document)

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.unit
    def test_validate_query_schema(self):
        """Test query schema validation."""
        from app.utils.validation import validate_query_schema

        valid_query = create_query_data()
        result = validate_query_schema(valid_query)

        assert result["valid"] is True
        assert result["errors"] == []

    @pytest.mark.unit
    def test_sanitize_input_data(self):
        """Test input data sanitization."""
        from app.utils.validation import sanitize_input

        malicious_input = "<script>alert('xss')</script> normal text"
        sanitized = sanitize_input(malicious_input)

        assert "<script>" not in sanitized
        assert "normal text" in sanitized


class TestUtilityFunctions:
    """Test utility functions and helpers."""

    @pytest.mark.unit
    def test_text_normalization(self):
        """Test text normalization utilities."""
        from app.utils.text_processing import normalize_text

        text = "  EXTRA   spaces   and  weird  casing  "
        normalized = normalize_text(text)

        assert normalized == "extra spaces and weird casing"
        assert "  " not in normalized  # No double spaces

    @pytest.mark.unit
    def test_extract_keywords(self):
        """Test keyword extraction from text."""
        from app.utils.text_processing import extract_keywords

        text = """
        Machine learning is a subset of artificial intelligence that enables
        computers to learn without being explicitly programmed. Deep learning
        uses neural networks to process data.
        """

        keywords = extract_keywords(text, max_keywords=5)

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert "machine learning" in [k.lower() for k in keywords]

    @pytest.mark.unit
    def test_calculate_text_similarity(self):
        """Test text similarity calculation."""
        from app.utils.text_processing import calculate_similarity

        text1 = "machine learning artificial intelligence"
        text2 = "artificial intelligence machine learning"

        similarity = calculate_similarity(text1, text2)

        assert 0.8 <= similarity <= 1.0  # Should be very similar

    @pytest.mark.unit
    def test_format_timestamp(self):
        """Test timestamp formatting utilities."""
        from app.utils.datetime_helpers import format_timestamp
        import datetime

        dt = datetime.datetime(2024, 1, 15, 10, 30, 45)
        formatted = format_timestamp(dt)

        assert "2024-01-15" in formatted
        assert "10:30:45" in formatted


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.unit
    def test_handle_network_timeout(self, mock_external_dependencies):
        """Test handling of network timeouts."""
        from app.services.api_client import APIClient

        client = APIClient()

        # Mock a timeout
        with patch.object(client, '_make_request', side_effect=TimeoutError):
            with pytest.raises(TimeoutError):
                client.make_request("http://example.com")

    @pytest.mark.unit
    def test_handle_invalid_json_response(self, mock_external_dependencies):
        """Test handling of invalid JSON responses."""
        from app.services.api_client import APIClient

        client = APIClient()

        # Mock invalid JSON response
        with patch.object(client, '_make_request', return_value="invalid json"):
            with pytest.raises(json.JSONDecodeError):
                client.make_request("http://example.com")

    @pytest.mark.unit
    def test_handle_rate_limiting(self, mock_external_dependencies):
        """Test handling of rate limiting."""
        from app.services.api_client import APIClient

        client = APIClient()

        # Mock rate limit response
        with patch.object(client, '_make_request', return_value='{"error": "rate limited"}'):
            result = client.make_request("http://example.com")
            assert "rate_limited" in result
            assert result["retry_after"] > 0

    @pytest.mark.unit
    def test_edge_case_documents(self):
        """Test processing of edge case documents."""
        from app.services.document_processor import DocumentProcessor

        processor = DocumentProcessor()
        edge_cases = create_edge_case_documents()

        for doc in edge_cases:
            result = processor.process(doc)
            assert result["status"] in ["processed", "skipped"]
            assert "edge_case_handled" in result