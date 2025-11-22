"""FastAPI application factory for the API service.

This module provides the application factory pattern for creating FastAPI
instances, following the Open/Closed Principle (OCP) from SOLID.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI

from src.api.config import APIConfig, get_config


def create_app(config: Optional[APIConfig] = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    This factory function creates a new FastAPI application with all necessary
    configuration, routes, middleware, and dependencies. It follows the Factory
    pattern and ensures proper separation of concerns.

    Args:
        config: Optional APIConfig instance. If not provided, configuration
                will be loaded from environment variables.

    Returns:
        Configured FastAPI application instance

    Example:
        >>> app = create_app()
        >>> # Or with custom config:
        >>> custom_config = APIConfig(host="127.0.0.1", port=9000, ...)
        >>> app = create_app(config=custom_config)
    """
    # Use provided config or load from environment
    if config is None:
        config = get_config()

    # Create FastAPI application
    app = FastAPI(
        title="Odin API Service",
        version="0.3.0",
        description="Internal API service for the Odin project, "
        "providing endpoints for data management, file storage, messaging, "
        "secret management, and LLM operations.",
    )

    # Store configuration in app state
    app.state.config = config

    # Register routes
    from src.api.routes.data import router as data_router
    from src.api.routes.files import router as files_router
    from src.api.routes.health import router as health_router
    from src.api.routes.llm import router as llm_router
    from src.api.routes.messages import router as messages_router
    from src.api.routes.secrets import router as secrets_router

    app.include_router(health_router)
    app.include_router(data_router)
    app.include_router(files_router)
    app.include_router(messages_router)
    app.include_router(secrets_router)
    app.include_router(llm_router)

    return app

