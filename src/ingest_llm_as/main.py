from fastapi import FastAPI
from .config import settings
from .models import HealthResponse
from .api.ingestion import router as ingestion_router
from .observability.setup import setup_observability, get_observability_status
from .observability.logging import get_logger

# Initialize structured logging
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="A microservice for ingesting data into the ApexSigma ecosystem.",
    version=settings.app_version,
    debug=settings.debug,
)

# Setup observability stack (metrics, tracing, logging)
setup_observability(app)

# Include API routers
app.include_router(ingestion_router)


@app.get("/", response_model=dict)
def read_root():
    """
    Root endpoint that returns a welcome message.
    """
    return {
        "message": f"Welcome to the {settings.app_name} service!",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Comprehensive health check endpoint with observability status.
    """
    # Get observability status
    obs_status = get_observability_status()
    
    # Create dependencies info
    dependencies = {
        "memOS.as": f"configured: {settings.memos_base_url}",
        **obs_status.get("integrations", {})
    }
    
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        dependencies=dependencies,
        **obs_status.get("observability", {})
    )
