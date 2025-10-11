"""
InGest-LLM.as Test Utilities - Factories

This module provides factory functions for generating test data
with various configurations and edge cases.
"""

from typing import Dict, Any, List, Optional
import uuid
import random
import time
from datetime import datetime, timezone


def create_document_data(
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    doc_id: Optional[str] = None,
    embeddings: Optional[List[float]] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Factory for creating test document data.

    Args:
        content: Document content (generated if None)
        metadata: Document metadata (default generated if None)
        doc_id: Document ID (UUID generated if None)
        embeddings: Document embeddings (random generated if None)
        **overrides: Additional fields to override

    Returns:
        Complete document data dictionary
    """
    if content is None:
        content = f"Test document content generated at {datetime.now().isoformat()}"

    if metadata is None:
        metadata = {
            "source": "test_factory",
            "type": "document",
            "author": "Test Author",
            "tags": ["test", "factory"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "word_count": len(content.split()),
            "language": "en"
        }

    if doc_id is None:
        doc_id = str(uuid.uuid4())

    if embeddings is None:
        # Generate 384-dimensional random embeddings
        embeddings = [random.uniform(-1.0, 1.0) for _ in range(384)]

    document = {
        "id": doc_id,
        "content": content,
        "metadata": metadata,
        "embeddings": embeddings,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    # Apply any overrides
    document.update(overrides)
    return document


def create_batch_documents(
    count: int = 5,
    base_content: Optional[str] = None,
    metadata_variations: Optional[List[Dict]] = None,
    **shared_metadata
) -> List[Dict[str, Any]]:
    """
    Factory for creating batches of test documents.

    Args:
        count: Number of documents to create
        base_content: Base content template (varied if None)
        metadata_variations: List of metadata variations for each document
        **shared_metadata: Metadata shared across all documents

    Returns:
        List of document data dictionaries
    """
    documents = []

    for i in range(count):
        # Generate varied content
        if base_content:
            content = f"{base_content} - Document {i+1}"
        else:
            content = f"""This is test document number {i+1} in a batch of {count}.
            It contains various information for testing purposes.
            Document ID: {i+1}, Timestamp: {datetime.now().isoformat()}"""

        # Generate varied metadata
        metadata = dict(shared_metadata)
        if metadata_variations and i < len(metadata_variations):
            metadata.update(metadata_variations[i])

        # Add default metadata
        metadata.setdefault("batch_id", f"batch-{uuid.uuid4().hex[:8]}")
        metadata.setdefault("sequence", i + 1)
        metadata.setdefault("source", "batch_factory")

        document = create_document_data(
            content=content,
            metadata=metadata,
            doc_id=f"batch-doc-{i+1:03d}"
        )

        documents.append(document)

    return documents


def create_query_data(
    query_text: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    query_embedding: Optional[List[float]] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Factory for creating test query data.

    Args:
        query_text: Query text (generated if None)
        filters: Query filters (empty if None)
        top_k: Number of results to return
        query_embedding: Query embeddings (random generated if None)
        **overrides: Additional fields to override

    Returns:
        Complete query data dictionary
    """
    if query_text is None:
        query_text = f"Test query generated at {datetime.now().isoformat()}"

    if filters is None:
        filters = {}

    if query_embedding is None:
        # Generate 384-dimensional random query embedding
        query_embedding = [random.uniform(-1.0, 1.0) for _ in range(384)]

    query = {
        "query": query_text,
        "filters": filters,
        "top_k": top_k,
        "query_embedding": query_embedding,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": str(uuid.uuid4())
    }

    # Apply any overrides
    query.update(overrides)
    return query


def create_user_data(
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: str = "user",
    preferences: Optional[Dict[str, Any]] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Factory for creating test user data.

    Args:
        user_id: User ID (UUID generated if None)
        username: Username (generated if None)
        email: Email address (generated if None)
        role: User role
        preferences: User preferences (default generated if None)
        **overrides: Additional fields to override

    Returns:
        Complete user data dictionary
    """
    if user_id is None:
        user_id = str(uuid.uuid4())

    if username is None:
        username = f"user_{random.randint(1000, 9999)}"

    if email is None:
        email = f"{username}@test.example.com"

    if preferences is None:
        preferences = {
            "theme": random.choice(["light", "dark"]),
            "language": "en",
            "notifications": random.choice([True, False]),
            "timezone": "UTC"
        }

    user = {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "preferences": preferences,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
        "is_active": True
    }

    # Apply any overrides
    user.update(overrides)
    return user


def create_ingestion_job_data(
    job_id: Optional[str] = None,
    source_type: str = "document",
    source_url: Optional[str] = None,
    status: str = "pending",
    priority: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Factory for creating test ingestion job data.

    Args:
        job_id: Job ID (UUID generated if None)
        source_type: Type of source being ingested
        source_url: Source URL or path (generated if None)
        status: Job status
        priority: Job priority (1-10)
        metadata: Additional job metadata
        **overrides: Additional fields to override

    Returns:
        Complete ingestion job data dictionary
    """
    if job_id is None:
        job_id = str(uuid.uuid4())

    if source_url is None:
        if source_type == "document":
            source_url = f"https://example.com/docs/test-{random.randint(1, 100)}.pdf"
        elif source_type == "webpage":
            source_url = f"https://example.com/articles/test-{random.randint(1, 100)}"
        elif source_type == "repository":
            source_url = f"https://github.com/test/repo-{random.randint(1, 100)}"
        else:
            source_url = f"file:///test/path/{source_type}-{random.randint(1, 100)}"

    if metadata is None:
        metadata = {
            "size_bytes": random.randint(1024, 10485760),  # 1KB to 10MB
            "content_type": f"{source_type}/test",
            "estimated_processing_time": random.randint(1, 300)  # 1-300 seconds
        }

    job = {
        "id": job_id,
        "source_type": source_type,
        "source_url": source_url,
        "status": status,
        "priority": priority,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
        "max_retries": 3
    }

    # Apply any overrides
    job.update(overrides)
    return job


def create_edge_case_documents() -> List[Dict[str, Any]]:
    """
    Factory for creating documents with edge cases for testing.

    Returns:
        List of documents with various edge cases
    """
    return [
        # Empty content
        create_document_data(
            content="",
            metadata={"edge_case": "empty_content"}
        ),
        # Very long content
        create_document_data(
            content="Very long content " * 1000,
            metadata={"edge_case": "long_content", "word_count": 2000}
        ),
        # Special characters
        create_document_data(
            content="Content with special chars: éñüñ 中文 🔥 🚀",
            metadata={"edge_case": "special_chars", "language": "mixed"}
        ),
        # Large metadata
        create_document_data(
            content="Document with large metadata",
            metadata={"edge_case": "large_metadata", **{f"field_{i}": f"value_{i}" for i in range(100)}}
        ),
        # Unicode content
        create_document_data(
            content="🚀 Unicode test: α β γ δ ε ζ η θ ι κ λ μ ν ξ ο π ρ σ τ υ φ χ ψ ω",
            metadata={"edge_case": "unicode", "language": "greek"}
        )
    ]


def create_performance_test_documents(count: int = 1000) -> List[Dict[str, Any]]:
    """
    Factory for creating documents for performance testing.

    Args:
        count: Number of documents to create

    Returns:
        List of documents optimized for performance testing
    """
    return create_batch_documents(
        count=count,
        base_content="Performance test document with standardized content for benchmarking.",
        metadata_variations=[{"performance_test": True, "batch_size": count}] * count
    )


def create_search_test_suite() -> Dict[str, Any]:
    """
    Factory for creating a comprehensive search test suite.

    Returns:
        Dictionary containing documents and test queries
    """
    # Create diverse documents
    documents = [
        create_document_data(
            content="Python programming language tutorial for beginners",
            metadata={"category": "programming", "language": "python", "level": "beginner"}
        ),
        create_document_data(
            content="Advanced machine learning algorithms and neural networks",
            metadata={"category": "ai", "topic": "ml", "level": "advanced"}
        ),
        create_document_data(
            content="Web development with React and JavaScript frameworks",
            metadata={"category": "web", "language": "javascript", "framework": "react"}
        ),
        create_document_data(
            content="Database design and SQL optimization techniques",
            metadata={"category": "database", "language": "sql", "topic": "optimization"}
        ),
        create_document_data(
            content="DevOps practices and continuous integration pipelines",
            metadata={"category": "devops", "topic": "ci_cd", "tools": ["jenkins", "docker"]}
        )
    ]

    # Create corresponding test queries
    queries = [
        create_query_data(
            query_text="python programming tutorial",
            filters={"category": "programming"},
            expected_matches=1
        ),
        create_query_data(
            query_text="machine learning neural networks",
            filters={"level": "advanced"},
            expected_matches=1
        ),
        create_query_data(
            query_text="javascript react web development",
            filters={"framework": "react"},
            expected_matches=1
        ),
        create_query_data(
            query_text="database sql optimization",
            filters={"topic": "optimization"},
            expected_matches=1
        ),
        create_query_data(
            query_text="devops continuous integration",
            filters={"category": "devops"},
            expected_matches=1
        ),
        create_query_data(
            query_text="nonexistent topic search",
            filters={},
            expected_matches=0
        )
    ]

    return {
        "documents": documents,
        "queries": queries,
        "total_documents": len(documents),
        "total_queries": len(queries)
    }