"""
Distributed tracing configuration for InGest-LLM.as.

Provides OpenTelemetry tracing integration with Jaeger for distributed
tracing across the ApexSigma ecosystem.
"""

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from fastapi import FastAPI

from ..config import get_settings


def setup_tracing(app: FastAPI) -> Optional[trace.Tracer]:
    """
    Initialize OpenTelemetry tracing and instrument the FastAPI app with a Jaeger exporter.
    
    If the ENABLE_TRACING environment variable is not set to "true" (case-insensitive), tracing is disabled and the function returns None.
    
    Returns:
        Configured tracer instance, or `None` if tracing is disabled.
    """
    # Check if tracing is enabled
    if not os.getenv("ENABLE_TRACING", "true").lower() == "true":
        return None

    # Configure resource information
    resource = Resource.create(
        {
            "service.name": get_settings().app_name,
            "service.version": get_settings().app_version,
            "service.namespace": "apexsigma",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Configure tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        collector_endpoint=os.getenv(
            "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
        ),
    )

    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(span_processor)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/openapi.json",
        tracer_provider=provider,
    )

    # Instrument HTTPX for memOS.as calls
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)

    # Get tracer instance
    tracer = trace.get_tracer(__name__)

    return tracer


def get_tracer() -> trace.Tracer:
    """Get the current tracer instance."""
    return trace.get_tracer(__name__)


def trace_ingestion_operation(operation_name: str):
    """
    Wraps a function to create an OpenTelemetry span for an ingestion operation named `operation_name`.
    
    Parameters:
        operation_name (str): Span name to use for the ingestion operation.
    
    Returns:
        decorator: A decorator that, when applied to a callable, starts a span with attributes `operation.type = "ingestion"` and `service.name = settings.app_name`; on success sets `operation.status = "success"`, on exception sets `operation.status = "error"`, records the error message and exception, and re-raises.
    """

    def decorator(func):
        """
        Create a decorator that wraps a function execution in an "ingestion" tracer span named by `operation_name`.
        
        The wrapped function is executed inside a span whose attributes include `operation.type` = "ingestion" and `service.name` = settings.app_name. On successful completion the span is annotated with `operation.status` = "success". If the wrapped function raises an exception the span is annotated with `operation.status` = "error", `error.message` containing the exception message, the exception is recorded on the span, and the exception is re-raised.
        
        Returns:
            callable: A wrapper function that executes the original function within the described span.
        """
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(
                operation_name,
                attributes={
                    "operation.type": "ingestion",
                    "service.name": get_settings().app_name,
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("operation.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("operation.status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def trace_memos_request(endpoint: str, method: str):
    """
    Create a decorator that starts a tracing span for an HTTP request to memOS.as.
    
    Parameters:
        endpoint (str): The memOS.as endpoint path appended to settings.memos_base_url.
        method (str): The HTTP method name used for the traced request (e.g., "GET", "POST").
    
    Returns:
        function: A decorator that wraps a callable and creates a span named "memos.{method}.{endpoint}".
            The span is annotated with request attributes (http.method, http.url, service.name, operation.type).
            On success the span receives `operation.status = "success"` and, if present on the result, `http.status_code`.
            On exception the span receives `operation.status = "error"`, `error.message`, and records the exception before the exception is re-raised.
    """

    def decorator(func):
        """
        Wraps a function to trace an HTTP request to memOS.as by creating a span named "memos.{method}.{endpoint}".
        
        The wrapper starts a span with attributes for HTTP method, URL (constructed from settings.memos_base_url and the endpoint), service name "memOS.as", and operation type "http_request". After calling the wrapped function, if the result has a `status_code` attribute that value is recorded on the span and the operation status is set to "success". If the wrapped function raises an exception, the span is annotated with `operation.status = "error"`, the exception message is recorded under `error.message`, the exception is attached to the span, and the exception is re-raised.
        
        Parameters:
            func (Callable): The function to wrap. The wrapper will call `func(*args, **kwargs)`.
        
        Returns:
            Callable: A wrapper function that executes `func` inside the tracing span.
        
        Raises:
            Exception: Re-raises any exception thrown by the wrapped function after recording it on the span.
        """
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(
                f"memos.{method.lower()}.{endpoint}",
                attributes={
                    "http.method": method,
                    "http.url": f"{get_settings().memos_base_url}{endpoint}",
                    "service.name": "memOS.as",
                    "operation.type": "http_request",
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    if hasattr(result, "status_code"):
                        span.set_attribute("http.status_code", result.status_code)
                    span.set_attribute("operation.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("operation.status", "error")
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def add_span_attributes(**attributes):
    """Add attributes to the current span."""
    current_span = trace.get_current_span()
    if current_span:
        for key, value in attributes.items():
            current_span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict = None):
    """
    Add an event to the currently active span.
    
    Parameters:
        name (str): The event name to add to the current span.
        attributes (dict, optional): Key-value attributes to attach to the event. Defaults to an empty dict if not provided.
    
    Notes:
        If there is no active span, this function has no effect.
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes or {})