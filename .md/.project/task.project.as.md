# Project Tasks: InGest-LLM.as

This file tracks the specific, actionable tasks for the current development cycle, derived from the project plan.

## Milestone 1: Foundational Ingestion Pipeline

### Bootstrap InGest-LLM.as Service ✅ COMPLETED

- [x] **Scaffold:** Project scaffolded using Poetry with Modern Python Toolchain Standard.
- [x] **Repository:** Repository created and initial scaffold committed.
- [x] **Toolchain Setup:** Poetry, Ruff, mypy, pytest, and pre-commit configured.
- [x] **FastAPI Service:** Basic FastAPI application with health endpoints implemented.

### Set Up Docker Configuration ✅ COMPLETED

- [x] **Dockerfile:** Multi-stage Dockerfile created with Python 3.13-slim, Poetry, and FastAPI setup.
- [x] **Container Testing:** Docker build and run tested successfully with working endpoints.
- [x] **Documentation:** Docker commands added to CLAUDE.md for development reference.
- [ ] **Docker Compose:** Add the `ingest-llm.as` service to the primary `docker-compose.yml` and configure its network to connect with `memOS.as`.

### Create the Core Ingestion Pipeline 🎯 PRIORITY

- [x] **Request Models:** Comprehensive Pydantic models implemented with validation, error handling, and memOS.as integration.
- [x] **Configuration:** Settings model with environment-based configuration for service and memOS.as integration.
- [x] **Health Enhancement:** Updated health endpoint with structured response model.
- [x] **Foundational Endpoint:** Complete `POST /ingest/text` endpoint with async/sync processing modes.
- [x] **Core Logic:** Full ingestion pipeline with content processing, chunking, and error handling.
- [x] **Integration:** memOS.as HTTP client with health checks and memory tier storage.
- [x] **Content Processing:** Intelligent content chunking with boundary detection and metadata extraction.

### Integrate Local Embedding Model

- [ ] **Dependencies:** Add `sentence-transformers` and `torch` to pyproject.toml via Poetry.
- [ ] **Model Selection:** Research and select a sentence-transformer model from Hugging Face suitable for code and text.
- [ ] **Service:** Create `src/ingest_llm_as/services/embedding_service.py` to load the model and provide a `generate_embedding(text)` function.

### Develop Python Codebase Parser

- [ ] **AST Parser:** Create `src/ingest_llm_as/parsers/python_ast_parser.py`.
- [ ] **Logic:** Implement the function to traverse a Python file's Abstract Syntax Tree (AST) and extract function/class definitions and docstrings.
- [ ] **Output:** Ensure the parser returns a structured list of JSON objects.
- [ ] **Endpoint:** Create `POST /ingest/python-repo` endpoint.

## Milestone 2: Command Suite & Expanded Sources

### Develop Web Scraper Parser

- [ ] **Dependencies:** Add `beautifulsoup4` and `httpx` to pyproject.toml via Poetry.
- [ ] **Parser:** Create `src/ingest_llm_as/parsers/web_parser.py`.
- [ ] **Logic:** Implement `parse_url(url)` function to fetch and clean main article text from a webpage.
- [ ] **Endpoint:** Create `POST /ingest/url` to orchestrate the web scraping pipeline.

### Develop Git Repository Parser

- [ ] **Dependencies:** Add `GitPython` to pyproject.toml via Poetry.
- [ ] **Parser:** Create `src/ingest_llm_as/parsers/git_parser.py`.
- [ ] **Logic:** Implement a function to clone a remote git repository.
- [ ] **Routing Logic:** Add logic to the git parser to route files to the correct sub-parser based on file extension (`.py`, `.md`, etc.).

## Development Standards

This project follows the **ApexSigma Modern Python Toolchain Standard**:
- **Python 3.13+** required
- **Poetry** for dependency management and packaging
- **Ruff** for linting and formatting (replaces Black, isort, Flake8)
- **mypy** for static type checking
- **pytest** for testing framework
- **pre-commit** hooks for automated quality assurance
- **src-layout** project structure for better packaging

## Progress Log

### 🎯 Milestone 1 Progress: 98% Complete ✅ NEARLY COMPLETE

**✅ Completed (August 16, 2025):**
- **Project Scaffolding:** Modern Python toolchain setup with Poetry, Ruff, mypy, pytest, pre-commit
- **FastAPI Foundation:** Basic service with health endpoints (`/` and `/health`)
- **Docker Containerization:** Production-ready Dockerfile with successful build/run testing
- **Documentation:** CLAUDE.md created with development commands and Docker instructions
- **Data Models:** Comprehensive Pydantic models with validation, error handling, and memOS.as integration
- **Configuration:** Environment-based settings with memOS.as connection parameters
- **Core Ingestion Pipeline:** Complete `POST /ingest/text` endpoint with sync/async processing
- **memOS.as Integration:** HTTP client with health checks, error handling, and memory tier routing
- **Content Processing:** Intelligent chunking with boundary detection and metadata extraction
- **Error Handling:** Comprehensive validation, logging, and error response patterns
- **Observability Stack:** Complete metrics (Prometheus), tracing (Jaeger), structured logging (Loki), and LLM observability (Langfuse) integration

**✅ Integration Ready:**
- memOS.as Graph API (`POST /graph/query`) confirmed working
- memOS.as Memory Store (`POST /memory/store`) confirmed working  
- Services running on different ports (InGest: 8000, memOS: 8091)
- **Langfuse LLM Observability:** Fully integrated with API keys and tracing instrumentation

**🔄 Next Priority:**
- End-to-end integration testing between InGest-LLM.as and memOS.as
- Implement `/memory/{tier}/store` endpoints in memOS.as for tier-specific storage
- Docker Compose integration with proper service networking

**📊 Latest Achievement (August 16, 2025):**
- **Langfuse Integration:** Complete LLM observability with trace creation, quality scoring, and metadata enrichment
- **Environment Configuration:** `.env.example` created with API key examples
- **Service Testing:** Confirmed startup with all observability components (Prometheus, Jaeger, Loki, Langfuse)
- **Documentation Update:** Task file updated to reflect 98% completion

**⏳ Future Enhancements:**
- LM Studio embedding integration (Devstral/Phi4 model switching)
- Python AST parser development (`POST /ingest/python-repo`)
- Web scraping capabilities (`POST /ingest/url`)
- Advanced content relationship detection

## Current Priority

The foundational ingestion pipeline is **98% complete** with comprehensive observability integration. The immediate next steps focus on **end-to-end integration testing** and deployment optimization.

### Next Development Session Goals
1. ✅ **COMPLETED**: Create Pydantic models for ingestion requests/responses
2. ✅ **COMPLETED**: Implement `POST /ingest/text` endpoint 
3. ✅ **COMPLETED**: Add basic validation and error handling
4. ✅ **COMPLETED**: Test integration with memOS.as endpoints
5. ✅ **COMPLETED**: Add comprehensive observability (Prometheus, Jaeger, Loki, Langfuse)
6. **NEXT**: End-to-end integration testing between services
7. **NEXT**: Docker Compose integration with proper service networking