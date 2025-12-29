# Linear Webhook Integration

This document describes the Linear webhook integration for InGest-LLM.as service.

## Overview

The Linear webhook integration provides a production-ready endpoint for receiving and processing Linear issue events with the following features:

- **HMAC-SHA256 Signature Verification**: Validates webhook authenticity
- **Circuit Breaker Pattern**: Prevents cascading failures with automatic recovery
- **Dead Letter Queue (DLQ)**: Persists failed payloads to PostgreSQL for retry
- **Correlation IDs**: Enables end-to-end request tracing
- **Health Monitoring**: Exposes circuit breaker state and metrics

## Architecture

```
Linear → POST /webhook/linear → Signature Verification → Circuit Breaker → Process Issue → Neo4j
                                                              ↓ (on failure)
                                                        Dead Letter Queue (PostgreSQL)
```

## Configuration

Add the following environment variables to your `.env` file:

```bash
# Linear webhook secret (from Linear webhook settings)
LINEAR_WEBHOOK_SECRET=your-secret-key-here

# PostgreSQL connection for Dead Letter Queue
POSTGRES_DSN=postgresql://user:password@localhost:5432/database

# Circuit breaker settings (optional, defaults shown)
CIRCUIT_BREAKER_THRESHOLD=3        # Number of failures before opening
CIRCUIT_BREAKER_TIMEOUT=300        # Seconds to wait before retry (5 minutes)
```

## API Endpoints

### POST /webhook/linear

Receives and processes Linear webhook events.

**Headers:**
- `Linear-Signature`: HMAC-SHA256 signature (required if `LINEAR_WEBHOOK_SECRET` is configured)
- `Content-Type`: application/json

**Request Body:**
```json
{
  "action": "create",
  "data": {
    "id": "ISS-123",
    "title": "Example Issue",
    "description": "Issue description"
  }
}
```

**Response (202 Accepted):**
```json
{
  "status": "processed",
  "issue_id": "ISS-123",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses:**

- `400 Bad Request`: Invalid JSON payload
- `401 Unauthorized`: Missing or invalid signature
- `500 Internal Server Error`: Processing failed (payload written to DLQ)
- `503 Service Unavailable`: Circuit breaker is open

### GET /webhook/health

Returns webhook health status including circuit breaker state.

**Response (200 OK):**
```json
{
  "linear_circuit_breaker": {
    "name": "linear_webhook",
    "state": "CLOSED",
    "failure_count": 0,
    "failure_threshold": 3,
    "recovery_timeout": 300
  }
}
```

## Circuit Breaker States

The circuit breaker has three states:

1. **CLOSED** (Normal): All requests are processed
2. **OPEN** (Failing): Requests are rejected with 503 after threshold failures
3. **HALF_OPEN** (Testing): After timeout, allows test requests to check recovery

### State Transitions

```
CLOSED --[threshold failures]--> OPEN --[timeout elapsed]--> HALF_OPEN
   ↑                                                              |
   └-------------------[success]-----------------------------------┘
```

## Dead Letter Queue

Failed webhook payloads are written to the `ingest_failures` PostgreSQL table:

```sql
CREATE TABLE ingest_failures (
    id SERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    error_message TEXT NOT NULL,
    correlation_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

Query failed payloads:
```sql
SELECT * FROM ingest_failures ORDER BY created_at DESC;
```

## Monitoring

### Health Checks

Check the circuit breaker state:
```bash
curl http://localhost:8000/webhook/health
```

Check overall service health (includes circuit breaker):
```bash
curl http://localhost:8000/health
```

### Metrics

The webhook endpoint exposes Prometheus metrics (available at `/metrics` endpoint):

- `webhook_requests_total`: Total webhook requests by status
- `webhook_processing_duration_seconds`: Request processing latency
- `circuit_breaker_state`: Current circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
- `circuit_breaker_transitions_total`: State transition count
- `dlq_messages_total`: Dead letter queue writes

## Testing

### Manual Testing

Test webhook endpoint without signature (for development):
```bash
curl -X POST http://localhost:8000/webhook/linear \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "data": {
      "id": "TEST-001",
      "title": "Test Issue"
    }
  }'
```

Test with signature:
```bash
# Generate signature (replace SECRET with your LINEAR_WEBHOOK_SECRET)
PAYLOAD='{"action":"create","data":{"id":"TEST-001"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "SECRET" | cut -d' ' -f2)

curl -X POST http://localhost:8000/webhook/linear \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

### Running Tests

Run all webhook tests:
```bash
poetry run pytest tests/test_circuit_breaker.py \
                 tests/test_webhook_signature.py \
                 tests/test_linear_processor.py \
                 tests/test_webhook_integration.py \
                 tests/test_dlq_handler.py \
                 -v
```

Run with coverage:
```bash
poetry run pytest tests/test_*.py \
                 --cov=src/ingest_llm_as/core \
                 --cov=src/ingest_llm_as/routers/webhook \
                 --cov-report=term-missing
```

## Troubleshooting

### Circuit Breaker is Open

1. Check the health endpoint to see failure count
2. Wait for recovery timeout (default 5 minutes) or restart service
3. Check DLQ for failed payloads: `SELECT * FROM ingest_failures ORDER BY created_at DESC LIMIT 10`
4. Fix underlying issues and retry failed payloads

### Signature Verification Failing

1. Verify `LINEAR_WEBHOOK_SECRET` matches Linear webhook settings
2. Check webhook signature header: `Linear-Signature`
3. Ensure payload is sent exactly as signed (no modifications)

### DLQ Not Working

1. Verify `POSTGRES_DSN` is configured correctly
2. Check PostgreSQL connection: `psql $POSTGRES_DSN`
3. Verify table exists: `\dt ingest_failures`
4. Create table if needed: Run the table creation SQL above

## Security Considerations

1. **Always configure `LINEAR_WEBHOOK_SECRET`** in production
2. Use HTTPS/TLS for webhook endpoints
3. Rotate webhook secrets periodically
4. Monitor DLQ for sensitive data before logging/debugging
5. Implement rate limiting at reverse proxy level

## Production Deployment

1. Configure all environment variables
2. Create DLQ table in PostgreSQL
3. Set up monitoring for:
   - Circuit breaker state
   - DLQ growth rate
   - Webhook latency
4. Configure alerts for:
   - Circuit breaker opens
   - High DLQ message count
   - Signature verification failures
5. Plan DLQ retry strategy

## Future Enhancements

- [ ] Automated DLQ retry mechanism
- [ ] Neo4j integration implementation
- [ ] Webhook payload validation schemas
- [ ] Rate limiting per webhook source
- [ ] Webhook event filtering
- [ ] Batch processing for high-volume events
