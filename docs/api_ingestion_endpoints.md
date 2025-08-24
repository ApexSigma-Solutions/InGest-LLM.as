# Ingestion API Endpoints

This document provides a formal specification for the InGest-LLM.as ingestion API endpoints.

## Endpoints

### POST /ingest/text

Ingests text content into the memory system.

**Request Body:**

```json
{
  "content": "string",
  "metadata": {
    "source": "manual" | "api" | "upload" | "web_scrape" | "repository",
    "content_type": "text" | "code" | "documentation" | "markdown" | "json",
    "source_url": "string",
    "author": "string",
    "title": "string",
    "tags": [
      "string"
    ],
    "custom_fields": {}
  },
  "chunk_size": integer,
  "process_async": boolean
}
```

**Response:**

```json
{
  "ingestion_id": "string",
  "status": "pending" | "processing" | "completed" | "failed",
  "total_chunks": integer,
  "results": [
    {
      "chunk_id": "string",
      "memory_id": "string",
      "memory_tier": "working" | "episodic" | "semantic" | "procedural",
      "content_hash": "string",
      "chunk_size": integer,
      "status": "pending" | "processing" | "completed" | "failed",
      "error_message": "string"
    }
  ],
  "processing_time_ms": integer,
  "created_at": "string",
  "message": "string"
}
```

### POST /ingest/python-repo

Ingests a Python repository for comprehensive code analysis.

**Request Body:**

```json
{
  "repository_source": "local_path" | "git_url" | "github_url" | "uploaded_zip",
  "source_path": "string",
  "include_patterns": [
    "string"
  ],
  "exclude_patterns": [
    "string"
  ],
  "max_file_size": integer,
  "max_files": integer,
  "process_async": boolean,
  "metadata": {
    "source": "manual" | "api" | "upload" | "web_scrape" | "repository",
    "content_type": "text" | "code" | "documentation" | "markdown" | "json",
    "source_url": "string",
    "author": "string",
    "title": "string",
    "tags": [
      "string"
    ],
    "custom_fields": {}
  }
}
```

**Response:**

```json
{
  "ingestion_id": "string",
  "repository_path": "string",
  "status": "pending" | "processing" | "completed" | "failed",
  "files_discovered": integer,
  "files_to_process": integer,
  "files_processed": [
    {
      "file_path": "string",
      "relative_path": "string",
      "file_size": integer,
      "status": "pending" | "processing" | "completed" | "failed",
      "elements_extracted": integer,
      "chunks_created": integer,
      "embeddings_generated": integer,
      "processing_time_ms": integer,
      "complexity_score": number,
      "error_message": "string",
      "memory_ids": [
        "string"
      ]
    }
  ],
  "processing_summary": {
    "total_files_found": integer,
    "total_files_processed": integer,
    "total_files_skipped": integer,
    "total_files_failed": integer,
    "total_elements_extracted": integer,
    "total_chunks_created": integer,
    "total_embeddings_generated": integer,
    "total_processing_time_ms": integer,
    "average_complexity": number,
    "file_type_distribution": {},
    "element_type_distribution": {},
    "largest_files": [
      {}
    ],
    "most_complex_files": [
      {}
    ],
    "processing_errors": [
      "string"
    ]
  },
  "discovery_time_ms": integer,
  "processing_time_ms": integer,
  "total_time_ms": integer,
  "created_at": "string",
  "completed_at": "string",
  "message": "string"
}
```
