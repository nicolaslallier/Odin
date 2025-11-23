"""Health microservice application.

This module provides the FastAPI application for health checks and monitoring.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Health microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("health", config=config)

    # Register Health routes
    from src.api.routes.health import router as health_router

    app.include_router(health_router)

    # Mount micro-frontend static files
    mfe_dir = Path(__file__).parent.parent.parent.parent / "frontend" / "microservices" / "health" / "dist"
    if mfe_dir.exists():
        app.mount("/health/mfe", StaticFiles(directory=str(mfe_dir)), name="health-mfe")

    # Add micro-frontend manifest endpoint
    @app.get("/health/manifest")
    async def get_manifest() -> dict[str, any]:
        """Get micro-frontend manifest.

        Returns:
            Manifest information for the health micro-frontend
        """
        return {
            "name": "health",
            "version": "2.0.0",
            "remoteEntry": "/mfe/health/remoteEntry.js",
            "exposedModules": ["./HealthApp", "./routes"],
            "routes": [
                {"path": "/health", "title": "Health Monitoring", "icon": "health"}
            ],
        }

    return app


# Create module-level app instance for uvicorn import string
app = create_app()

