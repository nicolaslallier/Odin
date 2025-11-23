"""Secrets microservice application.

This module provides the FastAPI application for vault/secrets management.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the Secrets microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("secrets", config=config)

    # Register Secrets routes
    from src.api.routes.secrets import router as secrets_router

    app.include_router(secrets_router)

    return app

