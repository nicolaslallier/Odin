"""Messages microservice application.

This module provides the FastAPI application for RabbitMQ messaging operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Messages microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("messages", config=config)

    # Register Messages routes
    from src.api.routes.messages import router as messages_router

    app.include_router(messages_router)

    return app

