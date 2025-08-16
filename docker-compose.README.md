# Docker Compose Integration for InGest-LLM.as

This document describes how to run InGest-LLM.as as part of the ApexSigma DevEnviro ecosystem using Docker Compose.

## Prerequisites

1. **DevEnviro Ecosystem Running**: Ensure the main DevEnviro services are running:
   ```bash
   cd ../devenviro.as
   docker-compose up -d
   ```

2. **memOS.as Service Running**: Ensure memOS.as is running and connected to the DevEnviro network:
   ```bash
   cd ../memos.as
   docker-compose up -d
   ```

3. **LM Studio (Optional)**: For embedding generation, install and run LM Studio locally:
   - Download from https://lmstudio.ai/
   - Install embedding models: `nomic-embed-text-v1.5`, `nomic-embed-code-v1`
   - Start server on http://localhost:1234

## Service Architecture

### Network Configuration
- **Network**: `devenviroas_default` (shared across all ApexSigma services)
- **Port**: 8000 (InGest-LLM.as API)
- **Dependencies**: Explicit dependency on memOS.as service

### Service Endpoints
- **InGest-LLM.as**: http://localhost:8000
- **memOS.as**: http://localhost:8091 (container: devenviro_memos_api:8090)
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:8080

## Quick Start

### 1. Basic Startup
```bash
# Start InGest-LLM.as service
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f ingest-llm-api
```

### 2. With Integration Testing
```bash
# Start with test runner
docker-compose --profile testing up -d

# Run integration tests only
docker-compose run --rm test-runner
```

### 3. Development Mode
```bash
# Start with live reloading (modify docker-compose.yml first)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Environment Configuration

### Local Development (.env)
```bash
# memOS.as Integration (local)
INGEST_MEMOS_BASE_URL=http://localhost:8091

# LM Studio (local)
INGEST_LM_STUDIO_BASE_URL=http://localhost:1234/v1

# Observability (local)
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### Docker Compose (.env for containers)
```bash
# memOS.as Integration (Docker networking)
INGEST_MEMOS_BASE_URL=http://devenviro_memos_api:8090

# LM Studio (host access from container)
INGEST_LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1

# Observability (Docker networking)
JAEGER_ENDPOINT=http://devenviro_jaeger:14268/api/traces
```

## Service Integration

### memOS.as Communication
The InGest-LLM.as service communicates with memOS.as using:
- **Container Network**: Internal communication via `devenviro_memos_api:8090`
- **Health Checks**: Validates memOS.as availability before processing
- **Error Handling**: Graceful degradation when memOS.as is unavailable

### LM Studio Integration
For local embedding generation:
- **Host Access**: Container accesses host LM Studio via `host.docker.internal:1234`
- **Model Selection**: Automatic switching between text and code embedding models
- **Graceful Degradation**: Service continues without embeddings if LM Studio unavailable

### Observability Integration
Full integration with DevEnviro observability stack:
- **Metrics**: Prometheus metrics exposed at `/metrics`
- **Tracing**: Jaeger distributed tracing with correlation IDs
- **Logging**: Structured JSON logs for Loki ingestion
- **Langfuse**: LLM-specific observability (when configured)

## Troubleshooting

### Common Issues

1. **Network Connection Issues**
   ```bash
   # Check if DevEnviro network exists
   docker network ls | grep devenviroas_default
   
   # If missing, start DevEnviro first
   cd ../devenviro.as && docker-compose up -d
   ```

2. **memOS.as Dependency**
   ```bash
   # Check memOS.as is running
   curl http://localhost:8091/health
   
   # Start memOS.as if needed
   cd ../memos.as && docker-compose up -d
   ```

3. **LM Studio Connection**
   ```bash
   # Check LM Studio is accessible from container
   docker exec devenviro_ingest_llm_api curl -f http://host.docker.internal:1234/v1/models
   ```

### Service Logs
```bash
# InGest-LLM.as logs
docker-compose logs -f ingest-llm-api

# All DevEnviro ecosystem logs
cd ../devenviro.as && docker-compose logs -f

# memOS.as logs
cd ../memos.as && docker-compose logs -f
```

### Health Checks
```bash
# InGest-LLM.as health
curl http://localhost:8000/health

# memOS.as health
curl http://localhost:8091/health

# Check service status
docker-compose ps
```

## Development Workflow

### 1. Code Changes
```bash
# Rebuild after code changes
docker-compose build ingest-llm-api

# Restart with new image
docker-compose up -d ingest-llm-api
```

### 2. Integration Testing
```bash
# Run full integration test suite
docker-compose --profile testing up --abort-on-container-exit

# Run specific test
docker-compose run --rm test-runner pytest tests/test_ingestion_e2e.py -v
```

### 3. Debugging
```bash
# Enter container for debugging
docker exec -it devenviro_ingest_llm_api bash

# Check container environment
docker exec devenviro_ingest_llm_api env | grep INGEST
```

## Production Considerations

### Resource Limits
Consider adding resource limits for production:
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### Security
- Use secrets management for API keys
- Configure proper network isolation
- Enable container scanning
- Implement health check alerts

### Monitoring
- Set up Grafana dashboards for InGest-LLM.as metrics
- Configure Prometheus alerts for service availability
- Monitor embedding generation performance
- Track memOS.as integration health