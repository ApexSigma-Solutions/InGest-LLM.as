"""Webhook endpoints for external integrations."""

from fastapi import APIRouter, Request, HTTPException, Header, status
from typing import Dict, Any, Optional
import uuid
import os

from ..core.circuit_breaker import CircuitBreaker
from ..core.webhook_signature import verify_signature, get_webhook_secret
from ..core.linear_processor import process_linear_issue
from ..core.dlq_handler import write_to_dlq
from ..observability.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhooks"])

# Initialize circuit breaker for Linear webhooks
linear_circuit_breaker = CircuitBreaker(
    failure_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3")),
    recovery_timeout=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "300")),
    name="linear_webhook"
)


@router.post("/linear", status_code=status.HTTP_202_ACCEPTED)
async def receive_linear_webhook(
    request: Request,
    linear_signature: Optional[str] = Header(None, alias="Linear-Signature")
) -> Dict[str, Any]:
    """
    Receive and process Linear webhook events.
    
    This endpoint:
    1. Verifies webhook signature
    2. Checks circuit breaker state
    3. Processes the Linear issue
    4. Records success/failure
    5. Writes failures to DLQ
    
    Args:
        request: FastAPI request object
        linear_signature: HMAC signature from Linear
        
    Returns:
        Processing confirmation with issue ID
        
    Raises:
        HTTPException: For authentication, circuit breaker, or processing errors
    """
    # Generate correlation ID for tracing
    correlation_id = str(uuid.uuid4())
    
    # Read raw body for signature verification
    body = await request.body()
    
    try:
        # Parse JSON payload
        payload = await request.json()
    except Exception as e:
        logger.error("Invalid JSON payload", correlation_id=correlation_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Verify webhook signature
    webhook_secret = get_webhook_secret()
    if webhook_secret:
        if not linear_signature:
            logger.warning("Missing Linear-Signature header", correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Linear-Signature header"
            )
        
        if not verify_signature(body, linear_signature, webhook_secret):
            logger.warning("Invalid webhook signature", correlation_id=correlation_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
    
    # Check circuit breaker state
    if not linear_circuit_breaker.is_closed():
        cb_status = linear_circuit_breaker.get_status()
        logger.warning(
            "Circuit breaker open",
            correlation_id=correlation_id,
            circuit_breaker=cb_status
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Circuit breaker open - service temporarily unavailable"
        )
    
    # Process the webhook
    try:
        result = await process_linear_issue(payload)
        linear_circuit_breaker.record_success()
        
        logger.info(
            "Linear webhook processed successfully",
            correlation_id=correlation_id,
            issue_id=result.get("id")
        )
        
        return {
            "status": "processed",
            "issue_id": result["id"],
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        # Record failure in circuit breaker
        linear_circuit_breaker.record_failure()
        
        # Write to dead letter queue
        postgres_dsn = os.getenv("POSTGRES_DSN")
        if postgres_dsn:
            await write_to_dlq(payload, str(e), correlation_id, postgres_dsn)
            logger.error(
                "Webhook processing failed - written to DLQ",
                correlation_id=correlation_id,
                error=str(e)
            )
        else:
            logger.error(
                "Webhook processing failed - DLQ not configured",
                correlation_id=correlation_id,
                error=str(e)
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing failed: {str(e)}"
        )


@router.get("/health")
async def webhook_health() -> Dict[str, Any]:
    """
    Health check endpoint with circuit breaker status.
    
    Returns:
        Circuit breaker status for all webhook integrations
    """
    return {
        "linear_circuit_breaker": linear_circuit_breaker.get_status()
    }
