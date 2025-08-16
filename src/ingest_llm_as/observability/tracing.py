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

from ..config import settings


def setup_tracing(app: FastAPI) -> Optional[trace.Tracer]:
    """
    Setup OpenTelemetry distributed tracing for the application.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        Optional[trace.Tracer]: Configured tracer instance
    """
    # Check if tracing is enabled
    if not os.getenv("ENABLE_TRACING", "true").lower() == "true":
        return None
    
    # Configure resource information
    resource = Resource.create({
        "service.name": settings.app_name,
        "service.version": settings.app_version,
        "service.namespace": "apexsigma",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Configure tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "localhost"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", "6831")),
        collector_endpoint=os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces"),
    )
    
    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(span_processor)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics,/docs,/openapi.json",
        tracer_provider=provider
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
    Decorator to trace ingestion operations.
    
    Args:
        operation_name: Name of the operation being traced
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(
                operation_name,
                attributes={
                    "operation.type": "ingestion",
                    "service.name": settings.app_name,
                }
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
    Decorator to trace requests to memOS.as.
    
    Args:
        endpoint: memOS.as endpoint being called
        method: HTTP method
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(
                f"memos.{method.lower()}.{endpoint}",
                attributes={
                    "http.method": method,
                    "http.url": f"{settings.memos_base_url}{endpoint}",
                    "service.name": "memOS.as",
                    "operation.type": "http_request",
                }
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    if hasattr(result, 'status_code'):
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
    """Add an event to the current span."""
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes or {})