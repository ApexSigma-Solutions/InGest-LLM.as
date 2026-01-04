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

- [Service Status](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/00_History/STATUS.md) - Current development status and capabilities
- [Deployment Guide](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/03_Implementation/deployment/infrastructure.md) - Production deployment instructions
- [API Reference](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/03_Implementation/api_ingestion_endpoints.md) - API endpoint documentation

## Infrastructure

The service is configured with the following infrastructure components:

- **Cloudflared Tunnel** (v2025.8.1) - Secure external access via Cloudflare network
- **memOS.as** - Memory storage backend
- **Embedding Service** - LM Studio or Ollama for local embeddings

See the [Deployment Guide](../OmegaVault/ApexSigma/Development/Projects/InGest-LLM/03_Implementation/deployment/infrastructure.md) for details.
