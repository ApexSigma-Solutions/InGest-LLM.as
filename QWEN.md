# QWEN.md - InGest-LLM.as Project

## Project Overview

This project, `InGest-LLM.as`, is a microservice designed for intelligent content ingestion into the ApexSigma ecosystem. It processes various types of content (text, code, documentation), performs intelligent chunking, generates embeddings (using LM Studio), and stores the processed information in the `memOS.as` knowledge management system across different memory tiers (Working, Episodic, Semantic, Procedural).

## Key Technologies & Architecture

- **Core Platform**: Python 3.13, FastAPI
- **Dependency Management**: Poetry
- **Memory System Integration**: `memOS.as` (via HTTP API)
- **Embeddings**: LM Studio integration for local embedding generation
- **Observability**: OpenTelemetry (Jaeger for tracing), Prometheus (metrics), Structlog (logging), Langfuse (LLM observability)
- **Async Processing**: Background tasks for non-blocking ingestion
- **Configuration**: Pydantic Settings with `.env` file support

## Directory Structure

```
InGest-LLM.as/
├── src/
│   └── ingest_llm_as/           # Main application package
│       ├── api/                 # API endpoint definitions
│       │   ├── ingestion.py     # Core ingestion endpoints
│       │   ├── repository.py    # Repository/project analysis endpoints
│       │   ├── ecosystem.py     # Ecosystem-wide analysis endpoints
│       │   ├── analysis.py      # Content analysis endpoints
│       │   └── omega_ingest.py  # Experimental ingestion endpoints
│       ├── models/              # Pydantic data models
│       ├── observability/       # Observability setup and clients (Langfuse, tracing, metrics, logging)
│       ├── services/            # External service clients (e.g., memOS.as)
│       ├── utils/               # Utility functions (content processing)
│       ├── config.py            # Application configuration
│       └── main.py              # FastAPI application entry point
├── tests/                       # Test suite
├── Dockerfile                   # Application Docker image definition
├── docker-compose.yml           # Service definition (intended for unified DevEnviro stack)
├── pyproject.toml               # Poetry project configuration
├── poetry.lock                  # Locked dependencies
└── README.md                    # Project README
```

## Building and Running

### Prerequisites

- Python 3.13
- Poetry
- Docker and Docker Compose (for containerized deployment)
- Access to a running `memOS.as` instance
- Access to a running LM Studio instance (for embeddings)

### Development Setup

1.  Install dependencies:
    ```bash
    poetry install
    ```
2.  Configure environment variables by creating a `.env` file (see `config.py` for required variables).
3.  Run the development server:
    ```bash
    poetry run uvicorn src.ingest_llm_as.main:app --reload
    ```

### Docker Deployment

The service is designed to run within the larger DevEnviro ecosystem using Docker Compose.

1.  Build the image:
    ```bash
    docker build -t ingest-llm-as .
    ```
2.  Run the container:
    ```bash
    docker run -p 8000:8000 ingest-llm-as
    ```
   Or, use the provided `docker-compose.yml` as part of the unified stack.

## Key API Endpoints

- **POST `/ingest/text`**: Main endpoint for ingesting text content. Supports synchronous and asynchronous processing. Generates embeddings and stores content in `memOS.as`.
- **GET `/health`**: Comprehensive health check including dependencies.
- **Other endpoints** in `api/` modules handle repository analysis, ecosystem scanning, and content analysis.

## Development Workflow

1.  **Modify Code**: Edit files in `src/ingest_llm_as/`.
2.  **Run Tests**: Execute tests using `pytest`.
3.  **Build & Deploy**: Use `poetry build` for distribution or `docker build`/`docker-compose` for containerized deployment.
4.  **Interact**: Use the FastAPI docs at `http://localhost:8000/docs` (or the configured port) to interact with the API.

This `QWEN.md` provides the essential context for working with the `InGest-LLM.as` project.
