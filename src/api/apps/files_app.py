"""Files microservice application.

This module provides the FastAPI application for file/storage operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Files microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("files", config=config)

    # Register Files routes
    from src.api.routes.files import router as files_router

    app.include_router(files_router)

    return app

