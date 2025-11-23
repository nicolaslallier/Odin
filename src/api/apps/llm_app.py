"""LLM microservice application.

This module provides the FastAPI application for LLM operations.
"""

from __future__ import annotations

from fastapi import FastAPI

from src.api.apps.base import create_base_app
from src.api.config import APIConfig


def create_app(config: APIConfig | None = None) -> FastAPI:
    """Create and configure the LLM microservice application.

    Args:
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    app = create_base_app("llm", config=config)

    # Register LLM routes
    from src.api.routes.llm import router as llm_router

    app.include_router(llm_router)

    return app

