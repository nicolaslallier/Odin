"""Health microservice application.

This module provides the FastAPI application for health checks and monitoring.
"""

from __future__ import annotations

from fastapi import FastAPI

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

    return app

