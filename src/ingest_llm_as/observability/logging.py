"""
Structured logging configuration for InGest-LLM.as.

Provides structured logging with JSON formatting for integration with
Loki and the existing observability stack.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

import structlog
from opentelemetry import trace

from ..config import settings


def setup_logging(log_level: str = "INFO", enable_json: bool = True) -> None:
    """
    Setup structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_json: Whether to enable JSON formatting
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_service_context,
            add_trace_context,
            structlog.dev.ConsoleRenderer(colors=not enable_json) if not enable_json 
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def add_service_context(logger, method_name, event_dict):
    """Add service context to log events."""
    event_dict.update({
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "namespace": "apexsigma"
    })
    return event_dict


def add_trace_context(logger, method_name, event_dict):
    """Add OpenTelemetry trace context to log events."""
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            event_dict.update({
                "trace_id": format(span_context.trace_id, "032x"),
                "span_id": format(span_context.span_id, "016x"),
            })
    return event_dict


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


def log_ingestion_start(
    logger: structlog.BoundLogger,
    ingestion_id: str,
    content_type: str,
    content_size: int,
    metadata: Dict[str, Any] = None
):
    """Log the start of an ingestion operation."""
    logger.info(
        "Ingestion started",
        event_type="ingestion.start",
        ingestion_id=ingestion_id,
        content_type=content_type,
        content_size=content_size,
        metadata=metadata or {},
    )


def log_ingestion_complete(
    logger: structlog.BoundLogger,
    ingestion_id: str,
    status: str,
    duration_ms: int,
    chunks_processed: int = 0,
    memory_tier: str = "semantic",
    error_message: Optional[str] = None
):
    """Log the completion of an ingestion operation."""
    log_data = {
        "event_type": "ingestion.complete",
        "ingestion_id": ingestion_id,
        "status": status,
        "duration_ms": duration_ms,
        "chunks_processed": chunks_processed,
        "memory_tier": memory_tier,
    }
    
    if error_message:
        log_data["error_message"] = error_message
    
    if status == "completed":
        logger.info("Ingestion completed successfully", **log_data)
    else:
        logger.error("Ingestion failed", **log_data)


def log_memos_request(
    logger: structlog.BoundLogger,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None,
    error_message: Optional[str] = None
):
    """Log a request to memOS.as service."""
    log_data = {
        "event_type": "memos.request",
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "service": "memOS.as",
    }
    
    if request_size:
        log_data["request_size"] = request_size
    if response_size:
        log_data["response_size"] = response_size
    if error_message:
        log_data["error_message"] = error_message
    
    if 200 <= status_code < 400:
        logger.info("memOS.as request successful", **log_data)
    else:
        logger.error("memOS.as request failed", **log_data)


def log_content_processing(
    logger: structlog.BoundLogger,
    operation: str,
    content_size: int,
    chunks_created: int = 0,
    processing_time_ms: int = 0,
    metadata: Dict[str, Any] = None
):
    """Log content processing operations."""
    logger.info(
        f"Content processing: {operation}",
        event_type="content.processing",
        operation=operation,
        content_size=content_size,
        chunks_created=chunks_created,
        processing_time_ms=processing_time_ms,
        metadata=metadata or {},
    )


def log_health_check(
    logger: structlog.BoundLogger,
    service: str,
    status: str,
    response_time_ms: int,
    details: Dict[str, Any] = None
):
    """Log health check results."""
    logger.info(
        f"Health check: {service}",
        event_type="health.check",
        target_service=service,
        status=status,
        response_time_ms=response_time_ms,
        details=details or {},
    )


class IngestionContextFilter:
    """Context filter for ingestion-specific logging."""
    
    def __init__(self, ingestion_id: str):
        self.ingestion_id = ingestion_id
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(ingestion_id=self.ingestion_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars("ingestion_id")


# Initialize logging on module import
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json=os.getenv("LOG_JSON", "true").lower() == "true"
)