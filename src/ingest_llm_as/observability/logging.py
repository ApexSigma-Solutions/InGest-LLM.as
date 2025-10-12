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

from ..config import get_settings


def setup_logging(log_level: str = "INFO", enable_json: bool = True) -> None:
    """
    Configure application structured logging and the standard library logger.
    
    Sets up structlog with a processor pipeline (contextvars, log level, ISO timestamps,
    service and trace context) and chooses a JSON or console renderer based on
    `enable_json`. Also configures the standard library logging to write to stdout at
    the given `log_level` and reduces verbosity for known noisy third-party loggers.
    
    Parameters:
        log_level (str): Logging level name (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
        enable_json (bool): If true, render logs as JSON; otherwise use a console renderer.
    """
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_service_context,
            add_trace_context,
            (
                structlog.dev.ConsoleRenderer(colors=not enable_json)
                if not enable_json
                else structlog.processors.JSONRenderer()
            ),
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
    """
    Attach service metadata to a log event dictionary.
    
    Parameters:
        logger: The logger instance (passed by structlog processors; not modified).
        method_name: The name of the processor method (passed by structlog; not used).
        event_dict (dict): The log event mapping to augment.
    
    Returns:
        dict: The same `event_dict` augmented with keys `service`, `version`, `environment`, and `namespace`.
    """
    event_dict.update(
        {
            "service": get_settings().app_name,
            "version": get_settings().app_version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "namespace": "apexsigma",
        }
    )
    return event_dict


def add_trace_context(logger, method_name, event_dict):
    """
    Add OpenTelemetry trace identifiers to the provided log event dictionary.
    
    If a current OpenTelemetry span with a valid context exists, this processor adds
    "trace_id" (32-character hexadecimal) and "span_id" (16-character hexadecimal)
    entries to event_dict and returns the same dictionary.
    
    Parameters:
        logger: The logger instance invoking this processor (unused).
        method_name: The logging method name invoking this processor (unused).
        event_dict (dict): Log event dictionary to augment.
    
    Returns:
        dict: The input event_dict, possibly augmented with `trace_id` and `span_id`.
    """
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context.is_valid:
            event_dict.update(
                {
                    "trace_id": format(span_context.trace_id, "032x"),
                    "span_id": format(span_context.span_id, "016x"),
                }
            )
    return event_dict


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Return a structlog logger bound to the provided name.
    
    Parameters:
        name (str): Name to bind to the logger (commonly `__name__`).
    
    Returns:
        structlog.BoundLogger: Configured structlog logger bound to `name`.
    """
    return structlog.get_logger(name)


def log_ingestion_start(
    logger: structlog.BoundLogger,
    ingestion_id: str,
    content_type: str,
    content_size: int,
    metadata: Dict[str, Any] = None,
):
    """
    Log the start of an ingestion operation with identifying and contextual fields.
    
    Parameters:
        logger (structlog.BoundLogger): Logger to emit the event.
        ingestion_id (str): Unique identifier for the ingestion run.
        content_type (str): MIME type or descriptor of the ingested content.
        content_size (int): Size of the content in bytes.
        metadata (Dict[str, Any], optional): Additional arbitrary metadata to attach; treated as an empty dict if not provided.
    """
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
    error_message: Optional[str] = None,
):
    """
    Log the completion of an ingestion operation with structured metadata.
    
    Parameters:
        logger: A configured structlog bound logger (omitted from generated docs normally).
        ingestion_id (str): Unique identifier for the ingestion run.
        status (str): Final status of the ingestion; use "completed" for success and other values to indicate failure.
        duration_ms (int): Total time taken by the ingestion in milliseconds.
        chunks_processed (int): Number of chunks produced or processed during ingestion.
        memory_tier (str): Logical memory tier used for the ingestion (e.g., "semantic").
        error_message (Optional[str]): Error message to include when the ingestion failed; omitted when None.
    """
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
    error_message: Optional[str] = None,
):
    """
    Log a memOS.as HTTP request outcome with structured metadata.
    
    Parameters:
        endpoint (str): The request path or URL target.
        method (str): HTTP method used (e.g., "GET", "POST").
        status_code (int): HTTP response status code.
        duration_ms (int): Round-trip duration in milliseconds.
        request_size (Optional[int]): Size of the request payload in bytes, if available.
        response_size (Optional[int]): Size of the response payload in bytes, if available.
        error_message (Optional[str]): Error message or description when the request failed, if available.
    """
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
    metadata: Dict[str, Any] = None,
):
    """
    Log details about a content processing operation.
    
    Parameters:
        logger (structlog.BoundLogger): Logger to emit the event.
        operation (str): Name of the processing operation performed.
        content_size (int): Size of the processed content in bytes.
        chunks_created (int): Number of chunks produced from the content.
        processing_time_ms (int): Time taken to process the content in milliseconds.
        metadata (Dict[str, Any] | None): Optional additional context to include in the log.
    
    Notes:
        Emits an event with `event_type` set to `"content.processing"` and fields for
        `operation`, `content_size`, `chunks_created`, `processing_time_ms`, and `metadata`.
    """
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
    details: Dict[str, Any] = None,
):
    """
    Record a health-check event for a service.
    
    Parameters:
    	service (str): Name of the target service being checked.
    	status (str): Health status of the service (for example, "ok", "degraded", or "down").
    	response_time_ms (int): Observed response time in milliseconds.
    	details (Dict[str, Any], optional): Additional metadata about the health check; defaults to an empty dict.
    """
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
        """
        Initialize the context manager with the ingestion identifier to bind to the logging context.
        
        Parameters:
            ingestion_id (str): Unique identifier for the ingestion operation to bind into structlog contextvars.
        """
        self.ingestion_id = ingestion_id

    def __enter__(self):
        """
        Bind this context manager's ingestion_id to structlog's context variables and return the manager.
        
        Returns:
            self (IngestionContextFilter): The context manager instance with `ingestion_id` bound to structlog contextvars.
        """
        structlog.contextvars.bind_contextvars(ingestion_id=self.ingestion_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Remove the bound `ingestion_id` from structlog's context when exiting the context manager.
        
        Parameters:
            exc_type (type | None): Exception type if one was raised inside the context, otherwise `None`.
            exc_val (BaseException | None): Exception instance if one was raised inside the context, otherwise `None`.
            exc_tb (types.TracebackType | None): Traceback object if an exception was raised inside the context, otherwise `None`.
        """
        structlog.contextvars.unbind_contextvars("ingestion_id")


# Initialize logging on module import
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_json=os.getenv("LOG_JSON", "true").lower() == "true",
)