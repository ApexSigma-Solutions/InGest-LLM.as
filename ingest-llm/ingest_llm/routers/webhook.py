"""
Linear Webhook Receiver

Handles Linear webhook events with circuit breaker and DLQ support.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""

import logging
import os
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response, status

from ..core.circuit_breaker import CircuitBreaker
from ..core.dlq_handler import write_to_dlq
from ..core.linear_webhook import get_webhook_secret, verify_signature
from ..core.saga_orchestrator import SagaOrchestrator
from ..core.metrics import (
    record_circuit_breaker_state,
    record_circuit_breaker_transition,
    record_dlq_message,
    record_webhook_request,
    set_service_info,
)

logger = logging.getLogger(__name__)

# Initialize circuit breaker
CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3"))
CIRCUIT_BREAKER_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "300"))
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")

circuit_breaker = CircuitBreaker(
    failure_threshold=CIRCUIT_BREAKER_THRESHOLD,
    timeout_seconds=CIRCUIT_BREAKER_TIMEOUT,
    name="linear_webhook",
)

saga = SagaOrchestrator(postgres_dsn=POSTGRES_DSN)

router = APIRouter(tags=["webhook"])


@router.post("/webhook/linear", status_code=status.HTTP_202_ACCEPTED)
async def receive_linear_webhook(request: Request) -> Dict[str, Any]:
    """
    Receive and process Linear webhook events.

    Validates signature using HMAC-SHA256, checks circuit breaker state,
    processes payload, and writes to DLQ on failure. Returns HTTP 202
    on successful acceptance, 401 on signature failure, and 503 when
    circuit breaker is open.

    Args:
        request: FastAPI Request object

    Returns:
        Dict[str, Any]: Response with correlation ID and status

    Raises:
        HTTPException: 401 for invalid signature, 503 for circuit open
    """
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    # Extract headers
    signature = request.headers.get("Linear-Signature", "")
    request_id = request.headers.get("X-Request-ID", correlation_id)

    logger.info(
        "Linear webhook received",
        extra={
            "correlation_id": correlation_id,
            "request_id": request_id,
            "signature_present": bool(signature),
        },
    )

    # Check circuit breaker state
    if not circuit_breaker.is_closed():
        cb_status = circuit_breaker.get_status()
        logger.warning(
            "Circuit breaker is OPEN, rejecting request",
            extra={
                "correlation_id": correlation_id,
                "circuit_breaker_status": cb_status,
            },
        )

        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="503",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service Unavailable",
                "message": "Circuit breaker is open",
                "correlation_id": correlation_id,
                "circuit_breaker": cb_status,
            },
        )

    # Read payload
    try:
        payload_bytes = await request.body()
        payload = await request.json()
    except Exception as e:
        logger.error(
            "Failed to read webhook payload",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="400",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=400,
            detail={
                "error": "Bad Request",
                "message": "Invalid payload format",
                "correlation_id": correlation_id,
            },
        )

    # Begin saga transaction
    await saga.begin_transaction(payload)

    # Verify signature
    secret = get_webhook_secret()
    if not secret:
        logger.error(
            "LINEAR_WEBHOOK_SECRET not configured",
            extra={"correlation_id": correlation_id},
        )

        circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="500",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": "Webhook secret not configured",
                "correlation_id": correlation_id,
            },
        )

    if not verify_signature(payload_bytes, signature, secret):
        logger.warning(
            "Invalid webhook signature",
            extra={
                "correlation_id": correlation_id,
                "signature": signature[:16] + "...",
            },
        )

        circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="401",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "Invalid webhook signature",
                "correlation_id": correlation_id,
            },
        )

    # Process webhook payload
    try:
        result = await _process_webhook_payload(payload, correlation_id)
        await saga.commit_transaction(payload)

        # Record success
        circuit_breaker.record_success()
        duration_seconds = time.time() - start_time

        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="202",
            duration_seconds=duration_seconds,
        )

        logger.info(
            "Webhook processed successfully",
            extra={
                "correlation_id": correlation_id,
                "duration_seconds": duration_seconds,
            },
        )

        return {
            "status": "accepted",
            "correlation_id": correlation_id,
            "message": "Webhook received and queued for processing",
        }

    except Exception as e:
        logger.error(
            "Failed to process webhook payload",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )

        # Write to DLQ
        if POSTGRES_DSN:
            dlq_id = await write_to_dlq(
                payload=payload,
                error_message=str(e),
                correlation_id=correlation_id,
                postgres_dsn=POSTGRES_DSN,
            )

            if dlq_id:
                record_dlq_message(service="ingest-llm")
                logger.info(
                    "Payload written to DLQ",
                    extra={
                        "correlation_id": correlation_id,
                        "dlq_id": dlq_id,
                    },
                )

        # Record failure
        circuit_breaker.record_failure()
        record_webhook_request(
            service="ingest-llm",
            endpoint="/webhook/linear",
            status="500",
            duration_seconds=time.time() - start_time,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": "Failed to process webhook",
                "correlation_id": correlation_id,
            },
        )


async def _process_webhook_payload(
    payload: Dict[str, Any],
    correlation_id: str,
) -> None:
    """
    Process Linear webhook payload.

    Extracts event type and data, then writes to Neo4j database.
    This is a placeholder for actual processing logic.

    Args:
        payload: Linear webhook payload
        correlation_id: Request correlation ID for tracing

    Raises:
        Exception: If processing fails
    """
    event_type = payload.get("type", "unknown")
    action = payload.get("action", "unknown")
    data = payload.get("data", {})

    logger.info(
        "Processing Linear webhook event",
        extra={
            "correlation_id": correlation_id,
            "event_type": event_type,
            "action": action,
        },
    )

    # TODO: Implement actual Neo4j write logic
    # This will be implemented in TN-100.3
    logger.debug(
        "Webhook payload data",
        extra={
            "correlation_id": correlation_id,
            "event_type": event_type,
            "data_keys": list(data.keys()),
        },
    )
