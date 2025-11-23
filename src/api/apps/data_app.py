"""Data microservice application.

This module provides the FastAPI application for data CRUD operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Data microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("data", config=config)

    # Register Data routes
    from src.api.routes.data import router as data_router

    app.include_router(data_router)

    return app

