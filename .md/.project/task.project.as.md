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

- [ ] **Foundational Endpoint:** Create `POST /ingest/text` endpoint for basic text ingestion.
- [ ] **Request Models:** Define Pydantic models for ingestion requests and responses.
- [ ] **Core Logic:** Implement basic ingestion pipeline structure.
- [ ] **Integration:** Connect with memOS.as memory storage endpoints.

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

### 🎯 Milestone 1 Progress: 60% Complete

**✅ Completed (August 16, 2025):**
- **Project Scaffolding:** Modern Python toolchain setup with Poetry, Ruff, mypy, pytest, pre-commit
- **FastAPI Foundation:** Basic service with health endpoints (`/` and `/health`)
- **Docker Containerization:** Production-ready Dockerfile with successful build/run testing
- **Documentation:** CLAUDE.md created with development commands and Docker instructions

**🔄 In Progress:**
- Core ingestion pipeline development (foundational text endpoint)

**⏳ Remaining:**
- Text ingestion endpoint implementation
- memOS.as integration
- Embedding model integration
- Python AST parser development

## Current Priority

The immediate next step is implementing the **foundational ingestion endpoint** (`POST /ingest/text`) to establish the core ingestion logic that will serve as the foundation for more specialized parsers and data sources.

### Next Development Session Goals
1. Create Pydantic models for ingestion requests/responses
2. Implement `POST /ingest/text` endpoint 
3. Add basic validation and error handling
4. Test integration with memOS.as endpoints