"""
Main FastAPI application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.deps import ensure_collection, get_qdrant_client
from app.api.routes import documents, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    ensure_collection()
    yield
    # Shutdown
    get_qdrant_client().close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Safety Hazard Detection using VLM + RAG",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(documents.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")

    return app


app = create_app()
