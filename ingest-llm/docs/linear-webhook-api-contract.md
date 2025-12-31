# Linear Webhook API Contract

## Overview

This document defines the API contract for the Linear webhook ingestion pipeline, including the webhook receiver endpoint, circuit breaker behavior, dead letter queue (DLQ) persistence, and the temporary forwarder shim.

## Version

- **Version**: 1.0.0
- **Phase**: TN-LINEAR-06 - Webhook Ingestion
- **Last Updated**: 2025-12-29

---

## 1. Webhook Receiver Endpoint

### 1.1 POST /webhook/linear

**Service**: ingest-llm

**Description**: Receives Linear webhook payloads, validates signatures, processes events, and writes to Neo4j database.

**Request**:

```http
POST /webhook/linear
Content-Type: application/json
Linear-Signature: <hmac-sha256-signature>
X-Correlation-ID: <correlation-id>
```

**Request Body**: Linear webhook payload (JSON)

Example payload:
```json
{
  "action": "IssueCreated",
  "data": {
    "id": "LIN-123",
    "title": "Test Issue",
    "description": "Test description",
    "state": "Backlog",
    "priority": 1,
    "labelIds": ["LABEL-1", "LABEL-2"],
    "createdAt": "2025-12-29T12:00:00Z",
    "updatedAt": "2025-12-29T12:00:00Z",
    "creatorId": "USER-123",
    "teamId": "TEAM-456"
  },
  "url": "https://linear.app/webhook",
  "triggerId": "TRIGGER-789"
  "createdAt": "2025-12-29T12:00:00Z"
}
```

**Response**:

**Success (HTTP 202 Accepted)**:
```json
{
  "status": "accepted",
  "correlation_id": "<correlation-id>",
  "message": "Webhook processed successfully"
}
```

**Error Responses**:

**HTTP 401 Unauthorized**:
```json
{
  "detail": "Invalid webhook signature"
}
```

**HTTP 503 Service Unavailable** (Circuit Breaker Open):
```json
{
  "detail": "Circuit breaker is OPEN. Service temporarily unavailable. State: OPEN, Failures: 3, Last Failure: 2025-12-29T12:00:00Z"
}
```

**HTTP 500 Internal Server Error**:
```json
{
  "detail": "Internal server error processing webhook"
}
```

---

## 2. Circuit Breaker Behavior

### 2.1 States

The circuit breaker has three states:

- **CLOSED**: Normal operation, requests are allowed
- **OPEN**: Circuit has tripped, requests are blocked
- **HALF_OPEN**: Recovery mode, one trial request is allowed

### 2.2 State Transitions

| Current State | Condition | Next State | Description |
|--------------|-----------|-------------|-------------|
| CLOSED | Failure count < threshold | CLOSED | Continue normal operation |
| CLOSED | Failure count >= threshold | OPEN | Circuit trips, block requests |
| OPEN | Timeout expired | HALF_OPEN | Allow one trial request |
| HALF_OPEN | Success | CLOSED | Trial succeeded, return to normal |
| HALF_OPEN | Failure | OPEN | Trial failed, return to blocked |

### 2.3 Configuration

- **Failure Threshold**: 3 consecutive failures
- **Timeout Period**: 300 seconds (5 minutes)
- **Recovery**: Automatic after timeout expires

### 2.4 Behavior

- **CLOSED State**:
  - All requests are processed normally
  - Failures are counted
  - Success resets failure count to 0

- **OPEN State**:
  - All requests return HTTP 503
  - Failures are not counted (already tripped)
  - After timeout, transitions to HALF_OPEN

- **HALF_OPEN State**:
  - First request is processed normally
  - Success transitions to CLOSED
  - Failure transitions back to OPEN

---

## 3. Dead Letter Queue (DLQ)

### 3.1 DLQ Table Schema

```sql
CREATE TABLE ingest_failures (
    id SERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    error_message TEXT NOT NULL,
    correlation_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 DLQ Record Structure

```json
{
  "id": 123,
  "payload": { ... },
  "error_message": "Failed to process webhook: database connection error",
  "correlation_id": "test-correlation-id-12345",
  "created_at": "2025-12-29T12:00:00Z"
}
```

---

## 4. Forwarder Shim (Temporary)

### 4.1 POST /webhook/linear

**Service**: InGest-LLM.as (Omega service)

**Description**: Temporary proxy that forwards Linear webhooks to ingest-llm service. Will be removed once DNS routing is configured.

**Request**:

```http
POST /webhook/linear
Content-Type: application/json
Linear-Signature: <hmac-sha256-signature>
X-Correlation-ID: <correlation-id>
```

**Request Body**: Linear webhook payload (JSON) - forwarded as-is

**Response**:

**Success (HTTP 202 Accepted)**:
```json
{
  "status": "forwarded",
  "correlation_id": "<correlation-id>",
  "message": "Webhook forwarded to ingest-llm service"
}
```

**Error Responses**:

**HTTP 503 Service Unavailable**:
```json
{
  "detail": "Ingest-llm service timeout. Service may be unavailable."
}
```

**HTTP 503 Service Unavailable** (Connection Error):
```json
{
  "detail": "Cannot connect to ingest-llm service. Service may be unavailable."
}
```

**HTTP 503 Service Unavailable** (HTTP Error):
```json
{
  "detail": "Ingest-llm service returned error: <error details>"
}
```

---

## 5. Health Check Endpoints

### 5.1 GET /health (ingest-llm)

**Service**: ingest-llm

**Response**:
```json
{
  "service": "ingest-llm",
  "version": "0.1.0",
  "status": "healthy",
  "dependencies": {
    "neo4j": "connected",
    "postgres": "connected"
  },
  "circuit_breaker": {
    "name": "linear-webhook",
    "state": "CLOSED",
    "failure_count": 0,
    "failure_threshold": 3,
    "timeout_seconds": 300,
    "last_failure_time": null,
    "is_closed": true
  }
}
```

### 5.2 GET /webhook/health (forwarder)

**Service**: InGest-LLM.as (forwarder)

**Response**:
```json
{
  "service": "webhook-forwarder",
  "status": "healthy",
  "target_url": "http://ingest-llm:8000",
  "timeout_seconds": 5
}
```

---

## 6. Signature Verification

### 6.1 HMAC-SHA256 Algorithm

Linear webhooks use HMAC-SHA256 for signature verification.

**Signature Format**: `sha256=<hex-digest>`

**Verification Process**:
1. Extract signature from `Linear-Signature` header
2. Remove `sha256=` prefix
3. Compute HMAC-SHA256 of request body using shared secret
4. Compare computed digest with provided signature (case-insensitive)

**Security Notes**:
- Shared secret must be kept confidential
- Use constant-time comparison to prevent timing attacks
- Reject requests with invalid signatures immediately (HTTP 401)

---

## 7. Error Handling

### 7.1 Error Response Format

All error responses follow this format:

```json
{
  "detail": "<error message>",
  "correlation_id": "<correlation-id>"
}
```

### 7.2 Error Categories

| Category | HTTP Status | Example |
|-----------|--------------|---------|
| Authentication | 401 | Invalid webhook signature |
| Circuit Breaker | 503 | Circuit is OPEN |
| Service Unavailable | 503 | Ingest-llm timeout/connection error |
| Internal Server Error | 500 | Unexpected processing error |

---

## 8. Logging

### 8.1 Structured Logging Format

All logs use JSON format with these fields:

```json
{
  "timestamp": "2025-12-29T12:00:00Z",
  "level": "INFO",
  "service": "ingest-llm",
  "correlation_id": "test-correlation-id-12345",
  "error": null,
  "error_type": null
}
```

### 8.2 Log Levels

- **CRITICAL**: Fatal startup failures
- **ERROR**: Exceptions with stack traces
- **WARNING**: Non-fatal issues
- **INFO**: Successful operations
- **DEBUG**: Detailed debugging information

---

## 9. Monitoring Metrics

### 9.1 Prometheus Metrics

All metrics are exposed at `/metrics` endpoint.

**Available Metrics**:

| Metric Name | Type | Labels | Description |
|--------------|------|--------|-------------|
| `webhook_requests_total` | Counter | service, endpoint, status | Total webhook requests |
| `webhook_processing_duration_seconds` | Histogram | service, endpoint | Request processing duration |
| `circuit_breaker_state` | Gauge | service, name | Current circuit breaker state |
| `circuit_breaker_transitions_total` | Counter | service, from_state, to_state | Total state transitions |
| `dlq_messages_total` | Counter | service | Total DLQ messages |

### 9.2 Metric Labels

- **service**: Service name (ingest-llm, webhook-forwarder)
- **endpoint**: API endpoint (/webhook/linear)
- **status**: HTTP status code (200, 401, 503, 500)
- **from_state**: Previous circuit breaker state
- **to_state**: New circuit breaker state

---

## 10. Security Considerations

### 10.1 Signature Verification

- Always verify Linear webhook signatures
- Reject requests without valid signatures
- Use constant-time comparison to prevent timing attacks

### 10.2 Rate Limiting

- Circuit breaker provides basic rate limiting
- Consider implementing additional rate limiting for production

### 10.3 Input Validation

- Validate webhook payload structure
- Sanitize input to prevent injection attacks

### 10.4 Secrets Management

- Store webhook secret in environment variable
- Never log or expose the secret
- Rotate secrets regularly

---

## 11. Operational Guidelines

### 11.1 Circuit Breaker Monitoring

- Monitor circuit breaker state transitions
- Investigate frequent circuit trips
- Adjust failure threshold and timeout as needed

### 11.2 DLQ Monitoring

- Monitor DLQ message count
- Investigate high DLQ rates
- Implement DLQ replay mechanism if needed

### 11.3 Performance Monitoring

- Monitor webhook processing duration
- Set up alerts for slow processing
- Track success/failure rates

### 11.4 Forwarder Shim Removal

- Forwarder shim is temporary
- Remove once DNS routing is configured
- Update Linear webhook URL to point directly to ingest-llm

---

## 12. Testing

### 12.1 Test Coverage

- Unit tests for circuit breaker state transitions
- Unit tests for DLQ persistence
- Unit tests for signature verification
- Unit tests for forwarder shim
- Integration tests for webhook endpoint
- Target coverage: >90%

### 12.2 Test Scenarios

- Success path with valid signature
- Invalid signature scenarios
- Circuit breaker state transitions
- DLQ write failures
- Forwarder timeout scenarios
- Forwarder connection errors

---

## 13. Troubleshooting

### 13.1 Common Issues

**Circuit Breaker Stuck in OPEN State**:
- Check for persistent failures causing circuit trips
- Review failure threshold and timeout settings
- Check downstream service health

**High DLQ Message Rate**:
- Investigate webhook payload processing failures
- Check database connectivity
- Review error logs for patterns

**Forwarder Timeout Errors**:
- Check network connectivity to ingest-llm service
- Verify ingest-llm service is running
- Check timeout configuration

### 13.2 Debugging

Enable debug logging by setting `LOG_LEVEL=DEBUG` environment variable.

---

## 14. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-29 | Initial release |
