"""FastAPI application factory for the API service.

This module provides the application factory pattern for creating FastAPI
instances, following the Open/Closed Principle (OCP) from SOLID.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI

from src.api.config import APIConfig, get_config
from src.api.services.container import ServiceContainer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    This context manager handles initialization and cleanup of services
    during application startup and shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Configure structured logging with database handler
    from src.api.logging_config import configure_logging_with_db
    import os

    config = app.state.config
    configure_logging_with_db(
        level=config.log_level.upper(),
        use_json=True,
        db_dsn=config.postgres_dsn,
        service_name="api",
        db_min_level=os.environ.get("LOG_LEVEL_DB_MIN", "INFO"),
        db_buffer_size=int(os.environ.get("LOG_BUFFER_SIZE", "100")),
        db_buffer_timeout=float(os.environ.get("LOG_BUFFER_TIMEOUT", "5.0")),
    )

    # Startup: Initialize services
    container = ServiceContainer(config)
    await container.initialize()
    app.state.container = container

    # Initialize database tables
    from src.api.repositories.data_repository import create_tables
    from src.api.repositories.image_repository import create_tables as create_image_tables

    engine = container.database.get_engine()
    await create_tables(engine)
    await create_image_tables(engine)

    yield

    # Shutdown: Cleanup services
    await container.shutdown()


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

    # Create FastAPI application with lifespan manager
    app = FastAPI(
        title="Odin API Service",
        version="0.4.0",
        description="Internal API service for the Odin project, "
        "providing endpoints for data management, file storage, messaging, "
        "secret management, and LLM operations.",
        lifespan=lifespan,
    )

    # Global error handler for ResourceNotFoundError
    from src.api.exceptions import ResourceNotFoundError
    from fastapi.responses import JSONResponse
    from fastapi import Request
    @app.exception_handler(ResourceNotFoundError)
    async def not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    # Store configuration in app state
    app.state.config = config

    # Register routes
    from src.api.routes.data import router as data_router
    from src.api.routes.files import router as files_router
    from src.api.routes.health import router as health_router
    from src.api.routes.image_analysis import router as image_analysis_router
    from src.api.routes.llm import router as llm_router
    from src.api.routes.logs import router as logs_router
    from src.api.routes.messages import router as messages_router
    from src.api.routes.secrets import router as secrets_router

    app.include_router(health_router)
    app.include_router(data_router)
    app.include_router(files_router)
    app.include_router(messages_router)
    app.include_router(secrets_router)
    app.include_router(llm_router)
    app.include_router(image_analysis_router)
    app.include_router(logs_router)

    return app


def get_container(app: FastAPI) -> ServiceContainer:
    """Get the service container from app state.

    This function provides dependency injection for accessing services.

    Args:
        app: FastAPI application instance

    Returns:
        Service container instance

    Raises:
        RuntimeError: If container not initialized
    """
    if not hasattr(app.state, "container"):
        raise RuntimeError("Service container not initialized")
    return app.state.container

