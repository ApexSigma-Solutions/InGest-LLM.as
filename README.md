# InGest-LLM.as

A microservice for ingesting data into the ApexSigma ecosystem.

## Quick Start

### Development

```bash
poetry install
poetry run uvicorn src.ingest_llm_as.main:app --reload
```

### Docker

```bash
docker build -t ingest-llm-as .
docker run -p 8000:8000 ingest-llm-as
```

## Documentation

- [Service Status](docs/STATUS.md) - Current development status and capabilities
- [Deployment Guide](docs/deployment/index.md) - Production deployment instructions
- [Infrastructure Setup](docs/deployment/infrastructure.md) - Infrastructure components and configuration
- [API Reference](docs/reference/index.md) - API endpoint documentation

## Infrastructure

The service is configured with the following infrastructure components:

- **Cloudflared Tunnel** (v2025.8.1) - Secure external access via Cloudflare network
- **memOS.as** - Memory storage backend
- **Embedding Service** - LM Studio or Ollama for local embeddings

See the [Infrastructure Setup Guide](docs/deployment/infrastructure.md) for details.