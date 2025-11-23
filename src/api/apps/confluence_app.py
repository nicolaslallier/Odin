"""Confluence microservice application.

This module provides the FastAPI application for Confluence operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Confluence microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("confluence", config=config)

    # Register Confluence routes
    from src.api.routes.confluence import router as confluence_router

    app.include_router(confluence_router)

    return app

