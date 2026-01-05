import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import get_settings
from .models import HealthResponse
from .api.ingestion import router as ingestion_router
from .api.repository import router as repository_router
from .api.ecosystem import router as ecosystem_router
from .api.analysis import router as analysis_router

from .api.omega_ingest import router as omega_ingest_router

from .routers.eod_logs import router as eod_logs_router
from .routers.webhook_forwarder import router as webhook_forwarder_router
from .routers.webhook import router as webhook_router
from .observability.logging import get_logger
from ingest_llm_as.processors.conversation_ingestor import ConversationIngestor

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup/shutdown of background tasks and resources.
    """
    # Startup
    logger.info("Initializing InGest-LLM services...")
    
    settings = get_settings()
    logger.info(f"DEBUG: raw_db_url={settings.raw_db_url}")
    logger.info(f"DEBUG: neo4j_uri={settings.neo4j_uri}")
    
    try:
        # Start Conversation Ingestor
        ingestor = ConversationIngestor()
        # Run as background task
        task = asyncio.create_task(ingestor.start())
        pass
    except Exception as e:
        logger.error(f"CRITICAL STARTUP ERROR: {e}", exc_info=True)
        raise e
    
    yield
    
    # Shutdown
    logger.info("Shutting down InGest-LLM services...")
    await ingestor.stop()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Services stopped.")

def create_app() -> FastAPI:
    """Create the FastAPI application.

    Observability integrations are intentionally removed for now.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="A microservice for ingesting data into the ApexSigma ecosystem.",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    # Configure CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(ingestion_router)
    app.include_router(repository_router)
    app.include_router(ecosystem_router)
    app.include_router(analysis_router)
    app.include_router(omega_ingest_router)
    app.include_router(eod_logs_router)
    app.include_router(webhook_forwarder_router)
    app.include_router(webhook_router)

    @app.get("/", response_model=dict)
    def read_root():
        """Root endpoint that returns a welcome message."""
        current = get_settings()
        return {
            "message": f"Welcome to the {current.app_name} service!",
            "version": current.app_version,
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health", response_model=HealthResponse)
    def health_check():
        """Health check endpoint.

        Note: observability fields are intentionally omitted/disabled.
        """
        current = get_settings()
        return HealthResponse(
            service=current.app_name,
            version=current.app_version,
            dependencies={
                "memOS.as": f"configured: {current.memos_base_url}",
            },
        )

    return app


app = create_app()
