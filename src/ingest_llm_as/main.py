from fastapi import FastAPI
from .config import get_settings
from .models import HealthResponse
from .api.ingestion import router as ingestion_router
from .api.repository import router as repository_router
from .api.ecosystem import router as ecosystem_router
from .api.analysis import router as analysis_router

from .api.omega_ingest import router as omega_ingest_router

# from .routers.eod_logs import router as eod_logs_router  # Temporarily disabled due to missing core modules
from .observability.setup import setup_observability, get_observability_status
from .observability.logging import get_logger

# Initialize structured logging
logger = get_logger(__name__)

app = FastAPI(
    title=get_settings().app_name,
    description="A microservice for ingesting data into the ApexSigma ecosystem.",
    version=get_settings().app_version,
    debug=get_settings().debug,
)

# Setup observability stack (metrics, tracing, logging)
setup_observability(app)

# Include API routers
app.include_router(ingestion_router)
app.include_router(repository_router)
app.include_router(ecosystem_router)
app.include_router(analysis_router)
app.include_router(omega_ingest_router)
# app.include_router(eod_logs_router)  # Temporarily disabled due to missing core modules


@app.get("/", response_model=dict)
def read_root():
    """
    Root endpoint that returns a welcome message.
    """
    return {
        "message": f"Welcome to the {get_settings().app_name} service!",
        "version": get_settings().app_version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """
    Return aggregated health information for the service including observability and dependency details.
    
    This response contains the service name and version from configuration, a dependencies mapping that includes the memOS base URL plus any observability integrations, and observability status fields (metrics/tracing/logging) provided by the observability subsystem.
    
    Returns:
        HealthResponse: Health model containing `service`, `version`, `dependencies`, and observability-related fields.
    """

    try:
        # Get observability status
        obs_status = get_observability_status()

        # Check critical dependencies
        dependencies = {
            "memOS.as": f"configured: {get_settings().memos_base_url}",
            **obs_status.get("integrations", {}),
        }

        # Determine overall health status
        observability = obs_status.get("observability", {})

        # Check if critical services are available
        critical_issues = []

        # Check if memOS is configured
        if not get_settings().memos_base_url or get_settings().memos_base_url == "":
            critical_issues.append("memOS base URL not configured")

        # Check observability components
        if not observability.get("metrics_enabled", False):
            critical_issues.append("metrics not enabled")
        if not observability.get("tracing_enabled", False):
            critical_issues.append("tracing not enabled")
        if not observability.get("logging_structured", False):
            critical_issues.append("structured logging not enabled")

        # Determine status
        status = "error" if critical_issues else "ok"

        response = HealthResponse(
            status=status,
            service=get_settings().app_name,
            version=get_settings().app_version,
            dependencies=dependencies,
            **observability,
        )

        # Return appropriate HTTP status
        if status == "error":
            # Still return 200 for health checks, but with error status in body
            # Some monitoring systems expect 200 even for unhealthy services
            pass

        return response

    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
        dependencies=dependencies,
        **obs_status.get("observability", {}),
    )
    except Exception as e:
        # If health check itself fails, return error status
        return HealthResponse(
            status="error",
            service=get_settings().app_name,
            version=get_settings().app_version,
            dependencies={"error": f"Health check failed: {str(e)}"},
        )
