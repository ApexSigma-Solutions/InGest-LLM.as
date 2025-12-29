# InGest-LLM.as

A microservice for ingesting data into the ApexSigma ecosystem.

## Features

- **Linear Webhook Integration**: Production-ready webhook receiver with circuit breaker and DLQ
- **Observability**: Prometheus metrics, OpenTelemetry tracing, Langfuse LLM tracking
- **memOS.as Integration**: Semantic memory storage and retrieval
- **LM Studio Integration**: Local embedding generation

## Documentation

- [Linear Webhook Integration](docs/linear-webhook-integration.md) - Webhook setup, configuration, and troubleshooting
- [API Documentation](http://localhost:8000/docs) - Interactive API documentation (when running)

## Development

```bash
poetry install
poetry run uvicorn src.ingest_llm_as.main:app --reload
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

Key configuration options:
- `LINEAR_WEBHOOK_SECRET`: Linear webhook authentication
- `POSTGRES_DSN`: Database connection for dead letter queue
- `CIRCUIT_BREAKER_THRESHOLD`: Failure threshold before circuit opens
- `CIRCUIT_BREAKER_TIMEOUT`: Recovery timeout in seconds

## Testing

Run all tests:
```bash
poetry run pytest tests/ -v
```

Run with coverage:
```bash
poetry run pytest tests/ --cov=src/ingest_llm_as --cov-report=term-missing
```

## Docker

```bash
docker build -t ingest-llm-as .
docker run -p 8000:8000 ingest-llm-as
```