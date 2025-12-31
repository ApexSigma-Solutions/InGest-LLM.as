"""
Ingest-LLM Service

Service for ingesting and processing LLM data for OmegaKG.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""
__version__ = "1.0.0"

from .core.circuit_breaker import CircuitBreaker, CircuitState
