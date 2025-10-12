"""
Observability setup and initialization for InGest-LLM.as.

Coordinates the setup of metrics, tracing, and logging for comprehensive
observability integration with the ApexSigma ecosystem.
"""

import os
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from prometheus_fastapi_instrumentator import Instrumentator

from .metrics import setup_metrics, init_service_metrics
from .tracing import setup_tracing
from .logging import setup_logging, get_logger
from .langfuse_client import get_langfuse_client
from ..config import settings

logger = get_logger(__name__)


class ObservabilityManager:
    """Manages all observability components for the application."""

    def __init__(self):
        """
        Initialize the observability manager's runtime state and feature flags.
        
        Sets instance attributes for Prometheus Instrumentator and OpenTelemetry tracer (initially None), captures a Langfuse client, and determines which observability features are enabled by reading environment variables: ENABLE_METRICS, ENABLE_TRACING, and ENABLE_STRUCTURED_LOGGING (each treated as true when set to "true", case-insensitive). Also records whether Langfuse observability is enabled from the retrieved client.
        """
        self.instrumentator: Optional[Instrumentator] = None
        self.tracer: Optional[trace.Tracer] = None
        self.langfuse_client = get_langfuse_client()
        self.metrics_enabled = os.getenv("ENABLE_METRICS", "true").lower() == "true"
        self.tracing_enabled = os.getenv("ENABLE_TRACING", "true").lower() == "true"
        self.logging_enabled = (
            os.getenv("ENABLE_STRUCTURED_LOGGING", "true").lower() == "true"
        )
        self.langfuse_enabled = self.langfuse_client.enabled

    def setup_all(self, app: FastAPI) -> None:
        """
        Initialize and configure all observability components for the given FastAPI application.
        
        Enables structured logging, Prometheus metrics, distributed tracing, and Langfuse LLM observability according to this manager's enabled flags and relevant environment variables. Metrics and tracing are attached to the provided FastAPI app when enabled.
        
        Parameters:
            app (FastAPI): FastAPI application instance to which metrics and tracing integrations are attached.
        """
        logger.info(
            "Initializing observability stack",
            metrics_enabled=self.metrics_enabled,
            tracing_enabled=self.tracing_enabled,
            logging_enabled=self.logging_enabled,
            langfuse_enabled=self.langfuse_enabled,
        )

        # Setup structured logging
        if self.logging_enabled:
            setup_logging(
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                enable_json=os.getenv("LOG_JSON", "true").lower() == "true",
            )
            logger.info("Structured logging initialized")

        # Setup metrics
        if self.metrics_enabled:
            self.instrumentator = setup_metrics(app)
            init_service_metrics(
                version=settings.app_version,
                environment=os.getenv("ENVIRONMENT", "development"),
            )
            logger.info("Prometheus metrics initialized", endpoint="/metrics")

        # Setup distributed tracing
        if self.tracing_enabled:
            self.tracer = setup_tracing(app)
            if self.tracer:
                logger.info(
                    "Distributed tracing initialized",
                    jaeger_endpoint=os.getenv(
                        "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
                    ),
                )
            else:
                logger.warning("Tracing setup skipped")

        # Setup Langfuse LLM observability
        if self.langfuse_enabled:
            logger.info(
                "Langfuse LLM observability initialized",
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
        else:
            logger.info(
                "Langfuse LLM observability disabled",
                reason="Missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY environment variables",
            )

    def get_health_status(self) -> dict:
        """
        Report current health status of observability components.
        
        Returns:
            dict: Mapping with the following keys:
                - "metrics_enabled": `True` if metrics are enabled.
                - "tracing_enabled": `True` if tracing is enabled and a tracer is present.
                - "logging_structured": `True` if structured logging is enabled.
                - "langfuse_enabled": `True` if Langfuse observability is enabled.
        """
        return {
            "metrics_enabled": self.metrics_enabled,
            "tracing_enabled": self.tracing_enabled and self.tracer is not None,
            "logging_structured": self.logging_enabled,
            "langfuse_enabled": self.langfuse_enabled,
        }

    def get_integrations_status(self) -> dict:
        """
        Return the enabled status of external observability integrations.
        
        Returns:
            dict: Mapping where keys are integration names (e.g., "prometheus", "grafana", "jaeger", "loki", "langfuse") and values are `True` for integrations that are currently enabled; integrations that are not enabled are omitted from the mapping.
        """
        integrations = {}

        if self.metrics_enabled:
            integrations["prometheus"] = True
            integrations["grafana"] = True  # Assumes Grafana reads from Prometheus

        if self.tracing_enabled and self.tracer:
            integrations["jaeger"] = True

        if self.logging_enabled:
            integrations["loki"] = True  # Assumes Loki ingests structured logs

        if self.langfuse_enabled:
            integrations["langfuse"] = True

        return integrations


# Global observability manager instance
observability = ObservabilityManager()


def setup_observability(app: FastAPI) -> ObservabilityManager:
    """
    Initialize and configure observability components for the given FastAPI application.
    
    Parameters:
        app (FastAPI): FastAPI application instance to attach observability components to.
    
    Returns:
        ObservabilityManager: The configured global ObservabilityManager instance.
    """
    observability.setup_all(app)
    return observability


def get_observability_status() -> dict:
    """
    Provide combined observability health and integrations status.
    
    Returns:
        status (dict): Dictionary with keys:
            - "observability": health status dict from ObservabilityManager.get_health_status()
            - "integrations": integrations status dict from ObservabilityManager.get_integrations_status()
    """
    return {
        "observability": observability.get_health_status(),
        "integrations": observability.get_integrations_status(),
    }