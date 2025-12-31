# Deployment Guide

This section provides comprehensive guides for deploying InGest-LLM.as in various environments.

## Quick Links

- [Infrastructure Setup](infrastructure.md) - Core infrastructure components and configuration
- [Tunnel and Webhook Verification](tunnel-verification.md) - Cloudflare tunnel and Linear webhook setup
- [Docker Deployment](../docker-compose.README.md) - Container-based deployment guide

## Deployment Options

### 1. Local Development

For local development and testing:

```bash
# Install dependencies
poetry install

# Run the service
poetry run uvicorn src.ingest_llm_as.main:app --reload
```

The service will be available at `http://localhost:8000`.

### 2. Docker Deployment

For production-ready containerized deployment:

```bash
# Build the image
docker build -t ingest-llm-as .

# Run the container
docker run -p 8000:8000 --env-file .env ingest-llm-as
```

See the [Docker Deployment Guide](../docker-compose.README.md) for detailed instructions.

### 3. Production Deployment with Cloudflare Tunnel

For secure, production deployments with external access:

1. **Set up infrastructure** (see [Infrastructure Setup](infrastructure.md))
   - Install and configure cloudflared tunnel agent
   - Configure supporting services (memOS.as, embedding service)

2. **Deploy the application**
   - Use Docker for consistent deployment
   - Configure environment variables for production

3. **Configure tunnel routing**
   - Map tunnel hostname to localhost:8000
   - Set up DNS routing through Cloudflare
   - See [Tunnel and Webhook Verification](tunnel-verification.md) for detailed steps

4. **Verify webhook integration** (if using Linear)
   - Configure Linear webhook settings
   - Set up webhook secret in environment
   - Test webhook delivery
   - See [Tunnel and Webhook Verification](tunnel-verification.md) for complete guide

5. **Enable monitoring**
   - Configure observability stack (optional)
   - Set up health check monitoring

## Infrastructure Components

The following components are required or recommended for production deployment:

### Required

- **InGest-LLM.as service** - The main FastAPI application
- **memOS.as** - Memory storage backend
- **Python 3.13+** - Runtime environment

### Recommended

- **Cloudflared tunnel** - Secure external access without port forwarding
- **Embedding service** - LM Studio or Ollama for local embeddings
- **Docker** - Containerized deployment
- **Observability stack** - Monitoring and tracing (Langfuse, Prometheus, Jaeger)

## Environment Configuration

Key environment variables for production:

```bash
# Core Service
INGEST_APP_NAME=InGest-LLM.as
INGEST_MEMOS_BASE_URL=http://your-memos-instance:8090
INGEST_MEMOS_API_KEY=your-api-key

# Embedding Service
INGEST_LM_STUDIO_ENABLED=true
INGEST_EMBEDDING_ENABLED=true
INGEST_LM_STUDIO_BASE_URL=http://localhost:1234/v1

# Webhook Configuration (if using Linear integration)
LINEAR_WEBHOOK_SECRET=your-webhook-secret-from-linear
FORWARDER_INGEST_LLM_URL=http://ingest-llm:8000

# Observability (optional)
INGEST_JAEGER_ENDPOINT=http://jaeger:14268/api/traces
INGEST_LOG_LEVEL=INFO
```

See `.env.example` for a complete list of configuration options.

## Security Considerations

- **API Keys:** Store sensitive credentials in environment variables or secret management system
- **Network Security:** Use Cloudflare tunnel to avoid exposing ports directly
- **Service Communication:** Keep internal services on private network
- **HTTPS:** Cloudflare tunnel provides automatic HTTPS termination

## Monitoring and Health Checks

The service provides several endpoints for monitoring:

- `GET /health` - Comprehensive health check with dependency status
- `GET /webhook/health` - Webhook forwarder health check
- `GET /` - Service information and version

Configure your monitoring tools to poll these endpoints regularly.

## Troubleshooting

### Service Won't Start

1. Check environment variables are correctly set
2. Verify memOS.as is accessible
3. Check Docker container logs: `docker logs <container-id>`

### Tunnel Connection Issues

1. Verify cloudflared is running: `cloudflared tunnel info <tunnel-name>`
2. Check tunnel configuration in `~/.cloudflared/config.yml`
3. Ensure service is listening on localhost:8000

### Embedding Generation Failures

1. Verify LM Studio or Ollama is running
2. Check embedding service URL in configuration
3. Test embedding service directly: `curl http://localhost:1234/v1/models`

## Next Steps

After deployment:

1. Review the [API Reference](../reference/index.md) for available endpoints
2. Set up monitoring and alerts
3. Configure backup procedures for memOS.as data
4. Plan scaling strategy if needed

## Support

For additional help:

- Check the [main README](../../README.md)
- Review [service status](../STATUS.md)
- See the [API documentation](../api_ingestion_endpoints.md)
