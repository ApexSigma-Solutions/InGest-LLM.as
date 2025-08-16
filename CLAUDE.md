# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InGest-LLM.as is a FastAPI-based microservice designed for data ingestion within the ApexSigma ecosystem. It's part of a larger "Society of Agents" architecture where this service handles data ingestion separately from memory management (handled by memOS.as).

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### Running the Service
```bash
# Development server with auto-reload
poetry run uvicorn src.ingest_llm_as.main:app --reload

# Production server
poetry run uvicorn src.ingest_llm_as.main:app --host 0.0.0.0 --port 8000
```

### Code Quality
```bash
# Lint and format code
poetry run ruff check .
poetry run ruff format .

# Type checking
poetry run mypy src/

# Run all pre-commit hooks
poetry run pre-commit run --all-files
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_filename.py

# Run with coverage
poetry run pytest --cov=src/ingest_llm_as
```

### Docker
```bash
# Build the container
docker build -t ingest-llm-as .

# Run the container
docker run -d -p 8000:8000 --name ingest-llm-as ingest-llm-as

# Test the service
curl http://localhost:8000/
curl http://localhost:8000/health

# Stop and remove container
docker stop ingest-llm-as && docker rm ingest-llm-as
```

## Architecture

### Project Structure
- **src/ingest_llm_as/**: Main application package using src-layout
- **main.py**: FastAPI application entry point with basic health endpoints
- **tests/**: Test suite (currently minimal)

### Key Technologies
- **FastAPI**: Modern Python web framework for building APIs
- **Uvicorn**: ASGI server for running FastAPI applications
- **Pydantic**: Data validation and settings management
- **Poetry**: Dependency management and packaging
- **Ruff**: High-performance linting and formatting (replaces Black, isort, Flake8)
- **mypy**: Static type checking
- **pre-commit**: Automated code quality checks

### Development Standards
This project follows the ApexSigma Modern Python Toolchain Standard:
- Python 3.13+ required
- Poetry for dependency management
- Ruff for linting/formatting
- mypy for type checking
- pytest for testing
- pre-commit hooks for quality assurance

### Current State
The service is scaffolded with basic FastAPI setup including:
- Root endpoint (`/`) returning welcome message
- Health check endpoint (`/health`)
- Minimal structure ready for ingestion endpoint development

### Next Development Phase
The primary next step is implementing the foundational ingestion endpoint - a POST endpoint to accept and process basic text data, establishing the core ingestion logic that will integrate with the broader ApexSigma ecosystem.