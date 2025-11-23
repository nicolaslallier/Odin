"""Image Analysis microservice application.

This module provides the FastAPI application for image analysis operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Image Analysis microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("image-analysis", config=config)

    # Register Image Analysis routes
    from src.api.routes.image_analysis import router as image_analysis_router

    app.include_router(image_analysis_router)

    return app

