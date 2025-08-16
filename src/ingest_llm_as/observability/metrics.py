"""
Prometheus metrics configuration for InGest-LLM.as.

Provides metrics collection for ingestion operations, performance monitoring,
and integration with the existing observability stack.
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from fastapi import FastAPI

# Custom metrics registry
registry = CollectorRegistry()

# Custom metrics for ingestion operations
ingestion_requests_total = Counter(
    "ingest_requests_total",
    "Total number of ingestion requests",
    ["endpoint", "content_type", "status"],
    registry=registry
)

ingestion_duration_seconds = Histogram(
    "ingest_duration_seconds",
    "Time spent processing ingestion requests",
    ["endpoint", "content_type"],
    registry=registry,
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0, float("inf"))
)

ingestion_chunks_processed = Counter(
    "ingest_chunks_processed_total",
    "Total number of content chunks processed",
    ["memory_tier", "status"],
    registry=registry
)

ingestion_content_size_bytes = Histogram(
    "ingest_content_size_bytes",
    "Size of content being ingested",
    ["content_type"],
    registry=registry,
    buckets=(100, 1000, 10000, 100000, 1000000, float("inf"))
)

memos_requests_total = Counter(
    "memos_requests_total",
    "Total requests to memOS.as service",
    ["endpoint", "method", "status_code"],
    registry=registry
)

memos_request_duration_seconds = Histogram(
    "memos_request_duration_seconds",
    "Duration of requests to memOS.as",
    ["endpoint", "method"],
    registry=registry
)

active_ingestions = Gauge(
    "ingest_active_operations",
    "Number of currently active ingestion operations",
    registry=registry
)

# Health and system metrics
service_info = Gauge(
    "ingest_service_info",
    "Service information",
    ["version", "environment"],
    registry=registry
)


def setup_metrics(app: FastAPI) -> Instrumentator:
    """
    Setup Prometheus metrics for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Instrumentator: Configured instrumentator instance
    """
    # Configure instrumentator with custom settings
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics", "/docs", "/openapi.json"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="ingest_requests_inprogress",
        inprogress_labels=True,
    )
    
    # Add default HTTP metrics
    instrumentator.instrument(app)
    
    # Add custom metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="ingest",
            metric_subsystem="http"
        )
    )
    
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            metric_namespace="ingest",
            metric_subsystem="http"
        )
    )
    
    # Expose metrics endpoint
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    
    return instrumentator


def record_ingestion_start(endpoint: str, content_type: str, content_size: int):
    """Record the start of an ingestion operation."""
    active_ingestions.inc()
    ingestion_content_size_bytes.labels(content_type=content_type).observe(content_size)


def record_ingestion_complete(
    endpoint: str, 
    content_type: str, 
    duration: float, 
    status: str,
    chunks_processed: int = 0,
    memory_tier: str = "semantic"
):
    """Record the completion of an ingestion operation."""
    active_ingestions.dec()
    ingestion_requests_total.labels(
        endpoint=endpoint, 
        content_type=content_type, 
        status=status
    ).inc()
    ingestion_duration_seconds.labels(
        endpoint=endpoint, 
        content_type=content_type
    ).observe(duration)
    
    if chunks_processed > 0:
        ingestion_chunks_processed.labels(
            memory_tier=memory_tier, 
            status=status
        ).inc(chunks_processed)


def record_memos_request(
    endpoint: str, 
    method: str, 
    status_code: int, 
    duration: float
):
    """Record a request to memOS.as service."""
    memos_requests_total.labels(
        endpoint=endpoint,
        method=method,
        status_code=str(status_code)
    ).inc()
    memos_request_duration_seconds.labels(
        endpoint=endpoint,
        method=method
    ).observe(duration)


def init_service_metrics(version: str, environment: str = "development"):
    """Initialize service-level metrics."""
    service_info.labels(version=version, environment=environment).set(1)