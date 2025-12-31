# Linear Webhook Ingestion - Operational Runbook

## Overview

This runbook provides operational procedures for managing the Linear webhook ingestion pipeline, including monitoring, troubleshooting, and maintenance tasks.

## Version

- **Version**: 1.0.0
- **Phase**: TN-LINEAR-06 - Webhook Ingestion
- **Last Updated**: 2025-12-29

---

## 1. Service Architecture

### 1.1 Components

```
Linear → Forwarder Shim (InGest-LLM.as) → Ingest-LLM Service
                                                    ↓
                                            Circuit Breaker
                                                    ↓
                                            Webhook Processor
                                                    ↓
                                            Neo4j Database
                                                    ↓
                                            DLQ (PostgreSQL)
```

### 1.2 Services

| Service | Port | Purpose |
|---------|-------|---------|
| InGest-LLM.as (Forwarder) | 8000 | Temporary proxy for Linear webhooks |
| Ingest-llm | 8000 | Main webhook processing service |
| PostgreSQL | 5432 | DLQ persistence |
| Neo4j | 7687 | Graph database |

---

## 2. Startup Procedures

### 2.1 Initial Deployment

**Prerequisites**:
- PostgreSQL database running
- Neo4j database running
- Environment variables configured
- Linear webhook secret configured

**Steps**:

1. **Verify Environment Variables**:
   ```bash
   # Check required variables
   echo $POSTGRES_DSN
   echo $LINEAR_WEBHOOK_SECRET
   echo $FORWARDER_INGEST_LLM_URL
   ```

2. **Start PostgreSQL**:
   ```bash
   docker-compose up -d postgres
   ```

3. **Start Neo4j**:
   ```bash
   docker-compose up -d neo4j
   ```

4. **Create DLQ Table**:
   ```bash
   # Run DLQ table creation
   poetry run python -c "
   import asyncio
   from ingest_llm.core.dlq_handler import create_dlq_table
   from ingest_llm.config import settings

   asyncio.run(create_dlq_table(settings.POSTGRES_DSN))
   "
   ```

5. **Start Ingest-LLM Service**:
   ```bash
   poetry run ingest-llm
   ```

6. **Start Forwarder Shim**:
   ```bash
   poetry run ingest-llm-as
   ```

7. **Verify Health**:
   ```bash
   # Check ingest-llm health
   curl http://localhost:8000/health

   # Check forwarder health
   curl http://localhost:8000/webhook/health
   ```

8. **Configure Linear Webhook**:
   - Set webhook URL to: `https://your-domain.com/webhook/linear`
   - Set webhook secret to match `LINEAR_WEBHOOK_SECRET`
   - Enable webhook events

### 2.2 Docker Compose Deployment

**Steps**:

1. **Build Images**:
   ```bash
   docker-compose build
   ```

2. **Start Services**:
   ```bash
   docker-compose up -d
   ```

3. **Verify Services**:
   ```bash
   docker-compose ps
   ```

4. **Check Logs**:
   ```bash
   docker-compose logs -f ingest-llm
   ```

---

## 3. Monitoring Procedures

### 3.1 Health Checks

**Ingest-LLM Health Check**:
```bash
curl http://localhost:8000/health
```

Expected response:
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

**Forwarder Health Check**:
```bash
curl http://localhost:8000/webhook/health
```

Expected response:
```json
{
  "service": "webhook-forwarder",
  "status": "healthy",
  "target_url": "http://ingest-llm:8000",
  "timeout_seconds": 5
}
```

### 3.2 Prometheus Metrics

**Scrape Metrics**:
```bash
curl http://localhost:8000/metrics
```

**Key Metrics to Monitor**:

| Metric | Type | Description | Alert Threshold |
|---------|------|-------------|------------------|
| `webhook_requests_total` | Counter | Total webhook requests | N/A |
| `webhook_processing_duration_seconds` | Histogram | Request processing duration | > 5s (warning), > 10s (critical) |
| `circuit_breaker_state` | Gauge | Current circuit breaker state | 1 (OPEN) |
| `circuit_breaker_transitions_total` | Counter | Total state transitions | N/A |
| `dlq_messages_total` | Counter | Total DLQ messages | > 10/min (warning) |

**Grafana Dashboard Queries**:

- **Webhook Request Rate**:
  ```
  rate(webhook_requests_total[5m])
  ```

- **Circuit Breaker State**:
  ```
  circuit_breaker_state{service="ingest-llm"}
  ```

- **DLQ Message Rate**:
  ```
  rate(dlq_messages_total[5m])
  ```

- **Processing Duration**:
  ```
  histogram_quantile(0.95, rate(webhook_processing_duration_seconds_bucket[5m]))
  ```

### 3.3 Log Monitoring

**Structured Log Format**:
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

**Log Levels**:
- **CRITICAL**: Fatal startup failures
- **ERROR**: Exceptions with stack traces
- **WARNING**: Non-fatal issues
- **INFO**: Successful operations
- **DEBUG**: Detailed debugging information

**Log Aggregation**:
- Configure log aggregation (e.g., ELK, Splunk, CloudWatch)
- Set up alerts for ERROR and CRITICAL logs
- Monitor log volume and patterns

---

## 4. Troubleshooting Procedures

### 4.1 Circuit Breaker Issues

**Symptom**: Circuit breaker stuck in OPEN state

**Diagnosis**:
```bash
# Check circuit breaker state
curl http://localhost:8000/health | jq '.circuit_breaker'
```

**Possible Causes**:
1. Persistent failures causing circuit trips
2. Downstream service unavailable
3. Network connectivity issues
4. Database connection issues

**Resolution Steps**:

1. **Check Downstream Services**:
   ```bash
   # Check Neo4j connectivity
   curl http://localhost:7474

   # Check PostgreSQL connectivity
   psql $POSTGRES_DSN -c "SELECT 1"
   ```

2. **Review Error Logs**:
   ```bash
   # Check recent errors
   docker-compose logs --tail=100 ingest-llm | grep ERROR
   ```

3. **Check Failure Count**:
   ```bash
   # Check failure count
   curl http://localhost:8000/health | jq '.circuit_breaker.failure_count'
   ```

4. **Wait for Timeout**:
   - Circuit breaker will automatically transition to HALF_OPEN after 5 minutes
   - Monitor for successful request to transition back to CLOSED

5. **Manual Reset (if needed)**:
   - Restart ingest-llm service
   - Circuit breaker will reset to CLOSED state

### 4.2 DLQ Issues

**Symptom**: High DLQ message rate

**Diagnosis**:
```bash
# Check DLQ message count
psql $POSTGRES_DSN -c "SELECT COUNT(*) FROM ingest_failures"

# Check recent DLQ messages
psql $POSTGRES_DSN -c "SELECT * FROM ingest_failures ORDER BY created_at DESC LIMIT 10"
```

**Possible Causes**:
1. Webhook payload processing failures
2. Database connectivity issues
3. Invalid webhook signatures
4. Payload size exceeding limits

**Resolution Steps**:

1. **Review DLQ Messages**:
   ```bash
   # Check error messages
   psql $POSTGRES_DSN -c "SELECT error_message, COUNT(*) FROM ingest_failures GROUP BY error_message ORDER BY COUNT DESC"
   ```

2. **Check Database Connectivity**:
   ```bash
   # Test PostgreSQL connection
   psql $POSTGRES_DSN -c "SELECT 1"
   ```

3. **Check Webhook Signatures**:
   ```bash
   # Verify webhook secret is correct
   echo $LINEAR_WEBHOOK_SECRET
   ```

4. **Check Payload Size**:
   ```bash
   # Check max content size
   echo $INGEST_MAX_CONTENT_SIZE
   ```

5. **Replay DLQ Messages** (if needed):
   - Implement DLQ replay mechanism
   - Manually replay failed messages after fixing issues

### 4.3 Forwarder Timeout Errors

**Symptom**: Forwarder returning HTTP 503

**Diagnosis**:
```bash
# Check forwarder health
curl http://localhost:8000/webhook/health

# Check ingest-llm health
curl http://localhost:8000/health

# Check network connectivity
docker-compose exec forwarder ping ingest-llm
```

**Possible Causes**:
1. Ingest-llm service unavailable
2. Network connectivity issues
3. Timeout configuration too low
4. Circuit breaker open on ingest-llm

**Resolution Steps**:

1. **Check Ingest-LLM Service**:
   ```bash
   # Check if ingest-llm is running
   docker-compose ps ingest-llm

   # Check ingest-llm health
   curl http://localhost:8000/health
   ```

2. **Check Network Connectivity**:
   ```bash
   # Test network connectivity
   docker-compose exec forwarder curl http://ingest-llm:8000/health
   ```

3. **Check Timeout Configuration**:
   ```bash
   # Check timeout setting
   echo $FORWARDER_FORWARDER_TIMEOUT
   ```

4. **Increase Timeout** (if needed):
   ```bash
   # Increase timeout to 10 seconds
   export FORWARDER_FORWARDER_TIMEOUT=10
   ```

5. **Restart Services**:
   ```bash
   docker-compose restart forwarder ingest-llm
   ```

### 4.4 Signature Verification Failures

**Symptom**: HTTP 401 Unauthorized responses

**Diagnosis**:
```bash
# Check webhook secret
echo $LINEAR_WEBHOOK_SECRET

# Check logs for signature errors
docker-compose logs --tail=100 ingest-llm | grep "Invalid webhook signature"
```

**Possible Causes**:
1. Webhook secret mismatch
2. Signature header missing
3. Payload tampering
4. Clock synchronization issues

**Resolution Steps**:

1. **Verify Webhook Secret**:
   ```bash
   # Check secret in Linear dashboard
   # Compare with environment variable
   echo $LINEAR_WEBHOOK_SECRET
   ```

2. **Update Webhook Secret**:
   ```bash
   # Update environment variable
   export LINEAR_WEBHOOK_SECRET=new-secret-here

   # Restart service
   docker-compose restart ingest-llm
   ```

3. **Check Signature Header**:
   ```bash
   # Verify Linear-Signature header is present
   curl -v -H "Linear-Signature: sha256=test" http://localhost:8000/webhook/linear
   ```

4. **Check Clock Synchronization**:
   ```bash
   # Check system time
   date

   # Sync time if needed
   ntpdate pool.ntp.org
   ```

---

## 5. Maintenance Procedures

### 5.1 Regular Maintenance Tasks

**Daily**:
- Review health check endpoints
- Check Prometheus metrics
- Review error logs
- Monitor DLQ message count

**Weekly**:
- Review circuit breaker state transitions
- Analyze webhook processing duration
- Review DLQ messages for patterns
- Check database connection health

**Monthly**:
- Rotate webhook secrets
- Review and update documentation
- Analyze long-term trends
- Perform capacity planning

### 5.2 Secret Rotation

**Steps**:

1. **Generate New Secret**:
   ```bash
   # Generate new webhook secret
   openssl rand -hex 32
   ```

2. **Update Linear Webhook**:
   - Go to Linear dashboard
   - Update webhook secret
   - Save changes

3. **Update Environment Variable**:
   ```bash
   # Update environment variable
   export LINEAR_WEBHOOK_SECRET=new-secret-here

   # Restart service
   docker-compose restart ingest-llm
   ```

4. **Verify Webhook Delivery**:
   - Trigger test webhook
   - Verify successful processing
   - Check logs for errors

### 5.3 Database Maintenance

**DLQ Cleanup**:
```bash
# Delete DLQ messages older than 30 days
psql $POSTGRES_DSN -c "DELETE FROM ingest_failures WHERE created_at < NOW() - INTERVAL '30 days'"

# Vacuum database
psql $POSTGRES_DSN -c "VACUUM FULL ingest_failures"
```

**Index Maintenance**:
```bash
# Reindex DLQ table
psql $POSTGRES_DSN -c "REINDEX TABLE ingest_failures"
```

### 5.4 Service Updates

**Zero-Downtime Deployment**:

1. **Build New Image**:
   ```bash
   docker-compose build ingest-llm
   ```

2. **Start New Instance**:
   ```bash
   docker-compose up -d --scale ingest-llm=2
   ```

3. **Verify New Instance**:
   ```bash
   # Check health of new instance
   curl http://localhost:8001/health
   ```

4. **Switch Traffic**:
   - Update load balancer configuration
   - Direct traffic to new instance

5. **Stop Old Instance**:
   ```bash
   docker-compose up -d --scale ingest-llm=1
   ```

---

## 6. Incident Response

### 6.1 Incident Severity Levels

| Severity | Description | Response Time |
|-----------|-------------|----------------|
| P1 - Critical | Service completely down | 15 minutes |
| P2 - High | Major functionality degraded | 1 hour |
| P3 - Medium | Partial functionality degraded | 4 hours |
| P4 - Low | Minor issues | 24 hours |

### 6.2 Incident Response Procedure

**Step 1: Detection**:
- Monitor alerts
- Check health endpoints
- Review error logs

**Step 2: Assessment**:
- Determine severity level
- Identify affected components
- Estimate impact

**Step 3: Containment**:
- Isolate affected services
- Prevent further damage
- Implement workarounds

**Step 4: Resolution**:
- Implement fix
- Verify resolution
- Restore services

**Step 5: Recovery**:
- Monitor for stability
- Verify all systems operational
- Close incident

**Step 6: Post-Incident Review**:
- Document incident
- Analyze root cause
- Implement preventive measures

### 6.3 Common Incidents

**Incident: Circuit Breaker Open**
- **Severity**: P2
- **Detection**: Circuit breaker state = OPEN
- **Resolution**: Check downstream services, wait for timeout, restart if needed

**Incident: High DLQ Rate**
- **Severity**: P2
- **Detection**: DLQ message rate > 10/min
- **Resolution**: Investigate processing failures, fix issues, replay DLQ messages

**Incident: Service Unavailable**
- **Severity**: P1
- **Detection**: Health check fails
- **Resolution**: Restart services, check dependencies, restore from backup if needed

---

## 7. Performance Tuning

### 7.1 Circuit Breaker Tuning

**Adjust Failure Threshold**:
```bash
# Increase threshold for noisy environments
export CIRCUIT_BREAKER_THRESHOLD=5

# Decrease threshold for strict environments
export CIRCUIT_BREAKER_THRESHOLD=2
```

**Adjust Timeout Period**:
```bash
# Increase timeout for slow recovery
export CIRCUIT_BREAKER_TIMEOUT=600

# Decrease timeout for fast recovery
export CIRCUIT_BREAKER_TIMEOUT=180
```

### 7.2 Database Tuning

**Connection Pooling**:
```bash
# Increase connection pool size
export POSTGRES_DSN="postgresql://user:password@host:5432/db?pool_size=20"
```

**Query Optimization**:
```bash
# Analyze slow queries
psql $POSTGRES_DSN -c "EXPLAIN ANALYZE SELECT * FROM ingest_failures"
```

### 7.3 Processing Tuning

**Adjust Chunk Size**:
```bash
# Increase chunk size for large payloads
export INGEST_DEFAULT_CHUNK_SIZE=2000

# Decrease chunk size for small payloads
export INGEST_DEFAULT_CHUNK_SIZE=500
```

**Adjust Batch Size**:
```bash
# Increase batch size for high throughput
export INGEST_EMBEDDING_BATCH_SIZE=20

# Decrease batch size for low latency
export INGEST_EMBEDDING_BATCH_SIZE=5
```

---

## 8. Backup and Recovery

### 8.1 Database Backups

**PostgreSQL Backup**:
```bash
# Create backup
pg_dump $POSTGRES_DSN > ingest_failures_backup_$(date +%Y%m%d).sql

# Restore backup
psql $POSTGRES_DSN < ingest_failures_backup_20251229.sql
```

**Neo4j Backup**:
```bash
# Create backup
neo4j-admin dump --database=neo4j --to=/backup/neo4j_$(date +%Y%m%d)

# Restore backup
neo4j-admin load --from=/backup/neo4j_20251229 --database=neo4j
```

### 8.2 Configuration Backups

**Backup Environment Variables**:
```bash
# Export environment variables
env | grep INGEST > ingest_env_backup_$(date +%Y%m%d).txt

# Restore environment variables
source ingest_env_backup_20251229.txt
```

### 8.3 Disaster Recovery

**Recovery Steps**:

1. **Restore Database Backups**:
   ```bash
   # Restore PostgreSQL
   psql $POSTGRES_DSN < ingest_failures_backup_latest.sql

   # Restore Neo4j
   neo4j-admin load --from=/backup/neo4j_latest --database=neo4j
   ```

2. **Restore Configuration**:
   ```bash
   # Restore environment variables
   source ingest_env_backup_latest.txt
   ```

3. **Restart Services**:
   ```bash
   docker-compose restart
   ```

4. **Verify Recovery**:
   ```bash
   # Check health endpoints
   curl http://localhost:8000/health

   # Check logs for errors
   docker-compose logs --tail=100
   ```

---

## 9. Security Procedures

### 9.1 Access Control

**Restrict Access**:
- Use firewall rules to restrict access
- Implement IP whitelisting
- Use VPN for remote access

**Audit Access**:
- Enable access logging
- Review access logs regularly
- Implement intrusion detection

### 9.2 Security Audits

**Regular Audits**:
- Review access logs
- Check for unauthorized access
- Verify security configurations
- Update security patches

**Vulnerability Scanning**:
- Run security scans regularly
- Address vulnerabilities promptly
- Keep dependencies updated

### 9.3 Incident Response

**Security Incident Response**:
1. Isolate affected systems
2. Preserve evidence
3. Notify security team
4. Investigate incident
5. Implement fixes
6. Document incident

---

## 10. Appendix

### 10.1 Useful Commands

**Service Management**:
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

**Database Operations**:
```bash
# Connect to PostgreSQL
psql $POSTGRES_DSN

# Run query
psql $POSTGRES_DSN -c "SELECT * FROM ingest_failures"

# Backup database
pg_dump $POSTGRES_DSN > backup.sql

# Restore database
psql $POSTGRES_DSN < backup.sql
```

**Health Checks**:
```bash
# Check ingest-llm health
curl http://localhost:8000/health

# Check forwarder health
curl http://localhost:8000/webhook/health

# Check metrics
curl http://localhost:8000/metrics
```

### 10.2 Contact Information

**Support Team**:
- Email: support@example.com
- Slack: #ingest-llm-support
- Pager: +1-555-123-4567

**On-Call Rotation**:
- Week 1: John Doe
- Week 2: Jane Smith
- Week 3: Bob Johnson

### 10.3 Additional Resources

- [API Contract](./linear-webhook-api-contract.md) - Detailed API contract
- [Environment Variables Reference](./environment-variables-reference.md) - Configuration reference
- [Circuit Breaker Documentation](./circuit-breaker-guide.md) - Circuit breaker patterns
- [DLQ Management Guide](./dlq-management-guide.md) - DLQ operations guide

---

## 11. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-29 | Initial release |
