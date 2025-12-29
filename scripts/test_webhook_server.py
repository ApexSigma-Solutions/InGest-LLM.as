#!/usr/bin/env python3
"""
Simple test server for webhook endpoint only.
This bypasses the main app's langfuse import issue for testing purposes.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import uvicorn
from fastapi import FastAPI
from ingest_llm_as.routers.webhook import router
from ingest_llm_as.observability.logging import get_logger

logger = get_logger(__name__)

# Create minimal app with just webhook router
app = FastAPI(
    title="InGest-LLM.as Webhook Test Server",
    description="Isolated webhook endpoint for testing",
    version="0.1.0"
)

# Include webhook router
app.include_router(router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Webhook Test Server",
        "endpoints": {
            "webhook": "POST /webhook/linear",
            "health": "GET /webhook/health"
        }
    }


if __name__ == "__main__":
    print("Starting webhook test server on http://localhost:8001")
    print("Endpoints:")
    print("  - POST http://localhost:8001/webhook/linear")
    print("  - GET  http://localhost:8001/webhook/health")
    print("\nPress Ctrl+C to stop")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
