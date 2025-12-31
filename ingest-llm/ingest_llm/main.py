"""
Ingest-LLM FastAPI Application

Main entry point for ingest-llm service that handles LLM data ingestion
and integration with OmegaKG services.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.saga_orchestrator import SagaOrchestrator
from .routers import health, webhook

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Ingest-LLM Service",
    description="Service for ingesting and processing LLM data for OmegaKG",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(webhook.router, prefix="/api/v1", tags=["webhook"])


@app.on_event("startup")
async def init_saga_table():
    """
    Initialize the Saga transactions table on service startup.

    This ensures the ingest_transactions table exists before the service
    starts accepting webhook requests. Part of TN-100.5 implementation.
    """
    postgres_dsn = os.getenv("POSTGRES_DSN")
    if postgres_dsn:
        saga = SagaOrchestrator(postgres_dsn=postgres_dsn)
        try:
            await saga.create_saga_table()
            logger.info("Saga transactions table initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize saga table: {e}")
            # Don't fail startup - table may already exist or DB may be temporarily unavailable
    else:
        logger.warning("POSTGRES_DSN not set - skipping saga table initialization")


@app.get("/")
async def root():
    """Root endpoint providing basic service information."""
    return {
        "service": "ingest-llm",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/v1/health",
            "metrics": "/api/v1/metrics",
            "webhook": "/api/v1/webhook/linear",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
