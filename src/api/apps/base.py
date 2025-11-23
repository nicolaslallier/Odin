"""Base application factory for microservices.

This module provides common functionality for all microservice applications.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.config import APIConfig, get_config
from src.api.exceptions import ResourceNotFoundError
from src.api.services.container import ServiceContainer


@asynccontextmanager
async def create_lifespan(service_name: str):
    """Create lifespan context manager for a microservice.

    Args:
        service_name: Name of the microservice (e.g., "confluence", "files")

    Returns:
        Async context manager for FastAPI lifespan
    """

    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application lifespan events.

        Args:
            app: FastAPI application instance

        Yields:
            None
        """
        # Configure structured logging with database handler
        import os

        from src.api.logging_config import configure_logging_with_db

        config = app.state.config
        configure_logging_with_db(
            level=config.log_level.upper(),
            use_json=True,
            db_dsn=config.postgres_dsn,
            service_name=f"api-{service_name}",
            db_min_level=os.environ.get("LOG_LEVEL_DB_MIN", "INFO"),
            db_buffer_size=int(os.environ.get("LOG_BUFFER_SIZE", "100")),
            db_buffer_timeout=float(os.environ.get("LOG_BUFFER_TIMEOUT", "5.0")),
        )

        # Startup: Initialize services
        container = ServiceContainer(config)
        await container.initialize()
        app.state.container = container

        # Initialize database tables (only data and image for now)
        if service_name in ["data", "image-analysis"]:
            if service_name == "data":
                from src.api.repositories.data_repository import create_tables

                engine = container.database.get_engine()
                await create_tables(engine)
            elif service_name == "image-analysis":
                from src.api.repositories.image_repository import (
                    create_tables as create_image_tables,
                )

                engine = container.database.get_engine()
                await create_image_tables(engine)

        yield

        # Shutdown: Cleanup services
        await container.shutdown()

    return lifespan


def create_base_app(
    service_name: str,
    version: str = "0.4.0",
    config: APIConfig | None = None,
) -> FastAPI:
    """Create base FastAPI application for a microservice.

    Args:
        service_name: Name of the microservice (e.g., "confluence", "files")
        version: API version
        config: Optional APIConfig instance

    Returns:
        Configured FastAPI application instance
    """
    # Use provided config or load from environment
    if config is None:
        config = get_config()

    # Create lifespan manager
    lifespan_context = create_lifespan(service_name)

    # Create FastAPI application
    app = FastAPI(
        title=f"Odin API - {service_name.title()} Service",
        version=version,
        description=f"Microservice for {service_name} operations in the Odin project.",
        lifespan=lifespan_context,
    )

    # Global error handler for ResourceNotFoundError
    @app.exception_handler(ResourceNotFoundError)
    async def not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    # Store configuration in app state
    app.state.config = config

    # Add inactivity tracking middleware
    from src.api.middleware.inactivity_tracker import add_inactivity_tracking

    add_inactivity_tracking(app)

    return app


def get_container(request: Request) -> ServiceContainer:
    """Get the service container from app state.

    This function provides dependency injection for accessing services.

    Args:
        request: FastAPI request instance

    Returns:
        Service container instance

    Raises:
        RuntimeError: If container not initialized
    """
    if not hasattr(request.app.state, "container"):
        raise RuntimeError("Service container not initialized")
    return request.app.state.container

