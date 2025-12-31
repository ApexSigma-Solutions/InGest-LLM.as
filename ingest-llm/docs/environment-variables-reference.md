# Linear Webhook Ingestion - Environment Variables Reference

## Overview

This document describes all environment variables used by Linear webhook ingestion pipeline, including ingest-llm service and temporary forwarder shim.

## Version

- **Version**: 1.0.0
- **Phase**: TN-LINEAR-06 - Webhook Ingestion
- **Last Updated**: 2025-12-29

---

## 1. Ingest-LLM Service Variables

### 1.1 Core Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `INGEST_APP_NAME` | InGest-LLM.as | Application name | No |
| `INGEST_APP_VERSION` | 0.1.0 | Application version | No |
| `INGEST_DEBUG` | False | Debug mode | No |
| `INGEST_HOST` | 0.0.0.0 | Server host | No |
| `INGEST_PORT` | 8000 | Server port | No |

### 1.2 Database Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `POSTGRES_DSN` | postgresql://user:password@localhost:5432/ingest_db | PostgreSQL connection string | Yes |
| `INGEST_LOG_LEVEL` | INFO | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | No |

### 1.3 Circuit Breaker Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `CIRCUIT_BREAKER_THRESHOLD` | 3 | Number of consecutive failures before tripping | No |
| `CIRCUIT_BREAKER_TIMEOUT` | 300 | Timeout in seconds before attempting recovery | No |

### 1.4 Linear Webhook Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `LINEAR_WEBHOOK_SECRET` | <set-in-environment> | Shared secret for Linear webhook signature verification | Yes |

### 1.5 Service Integration Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `INGEST_BASE_URL` | http://localhost:8000 | Base URL for this service | No |
| `INGEST_MEMOS_BASE_URL` | http://memos:8090 | memOS API base URL | No |
| `INGEST_MEMOS_API_KEY` | <set-in-environment> | memOS API key | No |
| `INGEST_MEMOS_TIMEOUT` | 30 | memOS API timeout in seconds | No |

### 1.6 Processing Limits

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `INGEST_MAX_CONTENT_SIZE` | 1000000 | Max content size in bytes (1MB) | No |
| `INGEST_DEFAULT_CHUNK_SIZE` | 1000 | Default chunk size | No |
| `INGEST_MAX_CHUNKS_PER_REQUEST` | 100 | Max chunks per request | No |

### 1.7 Embedding Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `INGEST_EMBEDDING_ENABLED` | True | Enable embedding generation | No |
| `INGEST_EMBEDDING_BATCH_SIZE` | 10 | Embedding batch size | No |
| `INGEST_EMBEDDING_DIMENSION` | 768 | Embedding dimension (default for nomic-embed) | No |

### 1.8 Async Processing Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `INGEST_ENABLE_ASYNC_PROCESSING` | True | Enable async processing | No |
| `INGEST_ASYNC_QUEUE_MAX_SIZE` | 1000 | Async queue max size | No |

---

## 2. Forwarder Shim Variables (InGest-LLM.as)

### 2.1 Forwarder Configuration

| Variable Name | Default Value | Description | Required |
|--------------|---------------|-------------|----------|
| `FORWARDER_INGEST_LLM_URL` | http://ingest-llm:8000 | URL of ingest-llm service to forward webhooks to | Yes |
| `FORWARDER_FORWARDER_TIMEOUT` | 5 | Timeout in seconds for forwarding requests | No |

---

## 3. Security Variables

### 3.1 Webhook Secret

| Variable Name | Description | Required | Security Notes |
|--------------|---------------|-------------|----------|
| `LINEAR_WEBHOOK_SECRET` | Shared secret for Linear webhook HMAC-SHA256 signature verification | Yes | - Never log or expose to logs<br>- Store in secure secret manager<br>- Rotate regularly<br>- Use strong random string (32+ characters)<br>- Never commit to version control |

### 3.2 Database Credentials

| Variable Name | Description | Required | Security Notes |
|--------------|---------------|-------------|----------|
| `POSTGRES_DSN` | PostgreSQL connection string with credentials | Yes | - Never log or expose to logs<br>- Store in secure secret manager<br>- Use strong password<br>- Use SSL/TLS in production<br>- Limit database user permissions |

---

## 4. Configuration Examples

### 4.1 Development Environment (.env)

```bash
# Core Configuration
INGEST_APP_NAME=InGest-LLM.as
INGEST_APP_VERSION=0.1.0
INGEST_DEBUG=true
INGEST_HOST=0.0.0.0
INGEST_PORT=8000

# Database Configuration
POSTGRES_DSN=postgresql://ingest_user:ingest_password@localhost:5432/ingest_db
INGEST_LOG_LEVEL=DEBUG

# Circuit Breaker Configuration
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_BREAKER_TIMEOUT=300

# Linear Webhook Configuration
LINEAR_WEBHOOK_SECRET=your-linear-webhook-secret-here

# Service Integration
INGEST_BASE_URL=http://localhost:8000
INGEST_MEMOS_BASE_URL=http://memos:8090
INGEST_MEMOS_API_KEY=your-memos-api-key-here
INGEST_MEMOS_TIMEOUT=30

# Processing Limits
INGEST_MAX_CONTENT_SIZE=1000000
INGEST_DEFAULT_CHUNK_SIZE=1000
INGEST_MAX_CHUNKS_PER_REQUEST=100

# Embedding Configuration
INGEST_EMBEDDING_ENABLED=true
INGEST_EMBEDDING_BATCH_SIZE=10
INGEST_EMBEDDING_DIMENSION=768

# Async Processing
INGEST_ENABLE_ASYNC_PROCESSING=true
INGEST_ASYNC_QUEUE_MAX_SIZE=1000
```

### 4.2 Production Environment

```bash
# Core Configuration
INGEST_APP_NAME=InGest-LLM.as
INGEST_APP_VERSION=0.1.0
INGEST_DEBUG=false
INGEST_HOST=0.0.0.0
INGEST_PORT=8000

# Database Configuration
POSTGRES_DSN=postgresql://prod_user:${POSTGRES_PASSWORD}@prod-db-host:5432/prod_db
INGEST_LOG_LEVEL=INFO

# Circuit Breaker Configuration
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_BREAKER_TIMEOUT=300

# Linear Webhook Configuration
LINEAR_WEBHOOK_SECRET=${LINEAR_WEBHOOK_SECRET}  # Load from secret manager

# Service Integration
INGEST_BASE_URL=https://ingest-llm.example.com
INGEST_MEMOS_BASE_URL=https://memos.example.com
INGEST_MEMOS_API_KEY=${MEMOS_API_KEY}  # Load from secret manager
INGEST_MEMOS_TIMEOUT=30

# Processing Limits
INGEST_MAX_CONTENT_SIZE=1000000
INGEST_DEFAULT_CHUNK_SIZE=1000
INGEST_MAX_CHUNKS_PER_REQUEST=100

# Embedding Configuration
INGEST_EMBEDDING_ENABLED=true
INGEST_EMBEDDING_BATCH_SIZE=10
INGEST_EMBEDDING_DIMENSION=768

# Async Processing
INGEST_ENABLE_ASYNC_PROCESSING=true
INGEST_ASYNC_QUEUE_MAX_SIZE=1000

# Forwarder Configuration
FORWARDER_INGEST_LLM_URL=http://ingest-llm:8000
FORWARDER_FORWARDER_TIMEOUT=5
```

### 4.3 Docker Compose Example

```yaml
version: '3.8'

services:
  ingest-llm:
    build: .
    environment:
      - INGEST_APP_NAME=InGest-LLM.as
      - INGEST_APP_VERSION=0.1.0
      - INGEST_DEBUG=false
      - INGEST_HOST=0.0.0.0
      - INGEST_PORT=8000
      - POSTGRES_DSN=postgresql://ingest_user:${POSTGRES_PASSWORD}@postgres:5432/ingest_db
      - INGEST_LOG_LEVEL=INFO
      - CIRCUIT_BREAKER_THRESHOLD=3
      - CIRCUIT_BREAKER_TIMEOUT=300
      - LINEAR_WEBHOOK_SECRET=${LINEAR_WEBHOOK_SECRET}
      - INGEST_BASE_URL=http://ingest-llm:8000
      - INGEST_MEMOS_BASE_URL=http://memos:8090
      - INGEST_MEMOS_API_KEY=${MEMOS_API_KEY}
      - INGEST_MEMOS_TIMEOUT=30
      - INGEST_MAX_CONTENT_SIZE=1000000
      - INGEST_DEFAULT_CHUNK_SIZE=1000
      - INGEST_MAX_CHUNKS_PER_REQUEST=100
      - INGEST_EMBEDDING_ENABLED=true
      - INGEST_EMBEDDING_BATCH_SIZE=10
      - INGEST_EMBEDDING_DIMENSION=768
      - INGEST_ENABLE_ASYNC_PROCESSING=true
      - INGEST_ASYNC_QUEUE_MAX_SIZE=1000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
```

---

## 5. Variable Validation

### 5.1 Required Variables

All required variables must be set before starting the service:

- `POSTGRES_DSN` - PostgreSQL connection string
- `LINEAR_WEBHOOK_SECRET` - Linear webhook shared secret

### 5.2 Optional Variables

Optional variables have sensible defaults:

- `INGEST_LOG_LEVEL` - Defaults to INFO
- `CIRCUIT_BREAKER_THRESHOLD` - Defaults to 3
- `CIRCUIT_BREAKER_TIMEOUT` - Defaults to 300 seconds (5 minutes)
- `FORWARDER_FORWARDER_TIMEOUT` - Defaults to 5 seconds

### 5.3 Variable Formats

- **PostgreSQL DSN**: `postgresql://[user]:[password]@[host]:[port]/[database]`
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Timeouts**: Integer values in seconds

### 5.4 Security Best Practices

1. Never commit secrets to version control
2. Use environment-specific secrets in production
3. Rotate secrets regularly (recommended: every 90 days)
4. Use strong, unique secrets (minimum 32 characters for webhook secrets)
5. Limit database user permissions to minimum required
6. Enable SSL/TLS for database connections in production
7. Use secret management systems (e.g., HashiCorp Vault, AWS Secrets Manager)

---

## 6. Troubleshooting

### 6.1 Common Issues

**Circuit Breaker Stuck in OPEN State**:
- Check for persistent failures causing circuit trips
- Review failure threshold and timeout settings
- Check downstream service health
- Review error logs for patterns

**High DLQ Message Rate**:
- Investigate webhook payload processing failures
- Check database connectivity
- Review error logs for patterns
- Check webhook payload size and complexity

**Forwarder Timeout Errors**:
- Check network connectivity to ingest-llm service
- Verify ingest-llm service is running
- Check timeout configuration
- Check firewall rules

### 6.2 Debugging

Enable debug logging by setting `INGEST_LOG_LEVEL=DEBUG`:

```bash
# Enable debug logging
export INGEST_LOG_LEVEL=DEBUG

# Run ingest-llm service with debug logging
poetry run ingest-llm
```

### 6.3 Health Checks

Check service health:

```bash
# Check ingest-llm health
curl http://localhost:8000/health

# Check forwarder health
curl http://localhost:8000/webhook/health
```

---

## 7. Migration Guide

### 7.1 From Previous Version

If upgrading from a previous version:

1. Update environment variables in `.env` file
2. Update Docker Compose configuration
3. Restart services
4. Verify health endpoints
5. Monitor logs for errors

### 7.2 Forwarder Shim Removal

Once DNS routing is configured:

1. Update Linear webhook URL to point directly to ingest-llm service
2. Remove forwarder shim code from InGest-LLM.as
3. Remove forwarder configuration from environment
4. Restart services
5. Verify webhooks are received directly

---

## 8. Additional Resources

- [API Contract](./linear-webhook-api-contract.md) - Detailed API contract
- [Operational Runbook](./operational-runbook.md) - Operational procedures
- [Circuit Breaker Documentation](./circuit-breaker-guide.md) - Circuit breaker patterns
- [DLQ Management Guide](./dlq-management-guide.md) - DLQ operations guide

---

## 9. Support

For issues or questions:

1. Check logs in `/var/log/ingest-llm/` or configured log directory
2. Review health check endpoints
3. Check Prometheus metrics at `/metrics`
4. Review this documentation
5. Check error logs for patterns

---

## 10. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-29 | Initial release |
