# Tunnel and Webhook Verification Guide

This guide provides step-by-step instructions for verifying the Cloudflare tunnel and Linear webhook integration.

## Prerequisites

- Cloudflared tunnel agent installed (see [Infrastructure Setup](infrastructure.md))
- InGest-LLM.as service running
- Linear workspace with API access
- DNS configured: `ingest.apexsigmasolutions.co.za` → Cloudflare tunnel

## Architecture Overview

```
Linear Webhook → Cloudflare Network → cloudflared tunnel → InGest-LLM.as (/webhook/linear)
```

The webhook flow:
1. Linear fires webhook to `https://ingest.apexsigmasolutions.co.za/webhook/linear`
2. Cloudflare routes request through the tunnel to local service
3. InGest-LLM.as receives webhook at `/webhook/linear` endpoint
4. Request is forwarded to `ingest-llm` service for processing
5. Service validates signature and processes payload

## Environment Configuration

### Required Environment Variables

Add these to your `.env` file:

```bash
# Webhook Configuration
LINEAR_WEBHOOK_SECRET=your_webhook_secret_from_linear
FORWARDER_INGEST_LLM_URL=http://ingest-llm:8000
FORWARDER_TIMEOUT=5

# Circuit Breaker (optional)
CIRCUIT_BREAKER_THRESHOLD=3
CIRCUIT_BREAKER_TIMEOUT=300

# Dead Letter Queue (optional)
POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
```

### Getting the Linear Webhook Secret

1. Go to Linear Settings → API → Webhooks
2. Click "Create webhook"
3. Copy the webhook secret
4. Add it to your `.env` file as `LINEAR_WEBHOOK_SECRET`

## Step 1: Start the Cloudflare Tunnel

### Verify Tunnel Configuration

Check that your tunnel is configured correctly:

```bash
# View tunnel info
cloudflared tunnel info valhalla-gateway

# View tunnel configuration
type %USERPROFILE%\.cloudflared\config.yml  # Windows
cat ~/.cloudflared/config.yml               # Linux/Mac
```

Expected configuration:
```yaml
tunnel: valhalla-gateway
credentials-file: /path/to/credentials.json

ingress:
  - hostname: ingest.apexsigmasolutions.co.za
    service: http://localhost:8000
  - service: http_status:404
```

### Start the Tunnel

```bash
# Start tunnel in foreground (for testing)
cloudflared tunnel run valhalla-gateway

# Start as background service (for production)
cloudflared service install
net start cloudflared  # Windows
```

### Verify Tunnel is Running

Expected output:
```
INF Starting tunnel tunnel=valhalla-gateway
INF Connection registered connIndex=0
INF Connection registered connIndex=1
INF Connection registered connIndex=2
INF Connection registered connIndex=3
```

All 4 connections should register successfully.

## Step 2: Start the InGest-LLM.as Service

### Local Development

```bash
# Using Poetry
poetry install
poetry run uvicorn src.ingest_llm_as.main:app --reload --host 0.0.0.0 --port 8000

# Using Docker
docker build -t ingest-llm-as .
docker run -p 8000:8000 --env-file .env ingest-llm-as
```

### Verify Service is Running

```bash
# Check health endpoint
curl http://localhost:8000/health

# Check webhook forwarder health
curl http://localhost:8000/webhook/health
```

Expected responses:
```json
{
  "service": "InGest-LLM.as",
  "version": "0.1.0",
  "dependencies": {
    "memOS.as": "configured: http://localhost:8091"
  }
}
```

```json
{
  "service": "webhook-forwarder",
  "status": "healthy",
  "target_url": "http://ingest-llm:8000",
  "timeout_seconds": 5
}
```

## Step 3: Configure Linear Webhook

1. **Navigate to Linear Settings**
   - Go to Settings → API → Webhooks

2. **Create New Webhook**
   - Click "Create webhook"
   - Name: "InGest-LLM.as Ingestion"
   - URL: `https://ingest.apexsigmasolutions.co.za/webhook/linear`
   
3. **Select Events**
   - Check "Issues" events:
     - Issue created
     - Issue updated
     - Issue deleted

4. **Copy Webhook Secret**
   - Copy the webhook secret shown
   - Add to `.env` as `LINEAR_WEBHOOK_SECRET`
   - Restart the service

5. **Save Webhook**

## Step 4: Test the Webhook

### Test via Linear UI

1. Create a test issue in Linear
2. Watch the local terminal for webhook delivery logs

Expected log output in InGest-LLM.as:
```
INFO: Linear webhook received correlation_id=xxx signature_present=True
INFO: Forwarding Linear webhook target_url=http://ingest-llm:8000
INFO: Webhook forwarded successfully status_code=202
```

Expected log output in cloudflared tunnel:
```
INF POST /webhook/linear HTTP/1.1 status=202
```

### Test via cURL (Manual)

Generate a test signature and payload:

```bash
# Generate HMAC signature
echo -n '{"type":"Issue","action":"create","data":{"id":"TEST-123"}}' | \
  openssl dgst -sha256 -hmac "your_webhook_secret" | \
  awk '{print "sha256="$2}'

# Send test request
curl -X POST https://ingest.apexsigmasolutions.co.za/webhook/linear \
  -H "Content-Type: application/json" \
  -H "Linear-Signature: sha256=GENERATED_SIGNATURE" \
  -d '{"type":"Issue","action":"create","data":{"id":"TEST-123"}}'
```

Expected response:
```json
{
  "status": "forwarded",
  "correlation_id": "xxx-xxx-xxx",
  "message": "Webhook forwarded to ingest-llm service"
}
```

## Step 5: Verify Success

### Success Criteria

- ✅ Tunnel is running without errors
- ✅ All 4 tunnel connections registered
- ✅ Service is running on port 8000
- ✅ Health endpoints return 200 OK
- ✅ Linear webhook configured with correct URL
- ✅ Test webhook sent from Linear
- ✅ Terminal shows `POST /webhook/linear 202 OK`

### Check Logs

**InGest-LLM.as logs:**
```bash
# Docker
docker logs <container-id> --tail 100 --follow

# Local
# Output appears in terminal where uvicorn is running
```

**Cloudflared logs:**
```bash
# Windows Service
Get-EventLog -LogName Application -Source cloudflared -Newest 50

# Linux systemd
journalctl -u cloudflared -n 50 -f

# Foreground process
# Output appears in terminal where cloudflared is running
```

### Common Log Patterns

**Successful webhook:**
```
INF POST /webhook/linear HTTP/1.1 status=202 duration=50ms
INFO: Webhook forwarded successfully correlation_id=xxx
```

**Connection error:**
```
ERROR: Connection error forwarding webhook error=Connection refused
HTTP 503 Service Unavailable
```

**Invalid signature:**
```
WARN: Invalid webhook signature
HTTP 401 Unauthorized
```

**Circuit breaker open:**
```
WARN: Circuit breaker is OPEN, rejecting request
HTTP 503 Service Unavailable
```

## Troubleshooting

### Tunnel Not Connecting

**Symptoms:**
- Tunnel fails to register connections
- "Connection refused" errors

**Solutions:**
```bash
# Verify tunnel exists
cloudflared tunnel list

# Check credentials file
dir %USERPROFILE%\.cloudflared\  # Windows
ls ~/.cloudflared/              # Linux/Mac

# Re-authenticate
cloudflared tunnel login

# Test connectivity
cloudflared tunnel route ip show
```

### Service Not Reachable

**Symptoms:**
- Tunnel connects but webhook returns 502
- "Bad Gateway" errors

**Solutions:**
```bash
# Verify service is running
curl http://localhost:8000/health

# Check port binding
netstat -an | findstr :8000  # Windows
netstat -an | grep :8000     # Linux/Mac

# Check firewall
# Ensure localhost connections are allowed
```

### Invalid Signature Errors

**Symptoms:**
- Webhook returns 401 Unauthorized
- "Invalid webhook signature" in logs

**Solutions:**
1. Verify `LINEAR_WEBHOOK_SECRET` in `.env` matches Linear webhook settings
2. Restart service after changing environment variable
3. Regenerate webhook secret in Linear and update `.env`

### Circuit Breaker Open

**Symptoms:**
- Webhook returns 503 after multiple failures
- "Circuit breaker is OPEN" in logs

**Solutions:**
1. Wait for circuit breaker timeout (default: 300 seconds)
2. Fix underlying issue causing failures
3. Restart service to reset circuit breaker

### Ingest-LLM Service Unavailable

**Symptoms:**
- Forwarder returns 503
- "Cannot connect to ingest-llm service" in logs

**Solutions:**
```bash
# Verify ingest-llm is running
docker ps | grep ingest-llm

# Check FORWARDER_INGEST_LLM_URL in .env
# For Docker Compose: http://ingest-llm:8000
# For local dev: http://localhost:8001

# Test connectivity
curl http://ingest-llm:8000/health  # Docker network
curl http://localhost:8001/health   # Local
```

## Monitoring and Metrics

### Health Checks

```bash
# Service health
curl http://localhost:8000/health

# Webhook forwarder health
curl http://localhost:8000/webhook/health

# Circuit breaker status (included in logs)
```

### Metrics (if enabled)

```bash
# Prometheus metrics
curl http://localhost:8000/metrics | grep webhook

# Key metrics:
# - webhook_request_total
# - webhook_request_duration_seconds
# - circuit_breaker_state
# - dlq_message_total
```

## Security Considerations

1. **Webhook Secret**
   - Keep `LINEAR_WEBHOOK_SECRET` secure
   - Rotate regularly
   - Never commit to version control

2. **Tunnel Security**
   - Tunnel provides encrypted connection
   - No inbound firewall rules needed
   - Managed through Cloudflare dashboard

3. **Signature Verification**
   - All webhooks validated with HMAC-SHA256
   - Constant-time comparison prevents timing attacks
   - Invalid signatures return 401 immediately

4. **Rate Limiting**
   - Circuit breaker prevents overwhelming service
   - DLQ ensures no data loss during outages
   - Consider adding rate limiting at Cloudflare level

## Next Steps

After successful verification:

1. **Configure Monitoring**
   - Set up Prometheus alerts
   - Configure log aggregation
   - Monitor circuit breaker state

2. **Set up DLQ**
   - Configure PostgreSQL for DLQ persistence
   - Set up DLQ replay mechanism
   - Monitor DLQ size

3. **Production Hardening**
   - Run cloudflared as system service
   - Configure service auto-restart
   - Set up log rotation
   - Configure backup tunnel

4. **Documentation**
   - Document runbook procedures
   - Create incident response plan
   - Document rollback procedures

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Linear Webhook Documentation](https://developers.linear.app/docs/graphql/webhooks)
- [Infrastructure Setup Guide](infrastructure.md)
- [Service Status](../STATUS.md)
