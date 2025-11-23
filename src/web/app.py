"""FastAPI application factory.

This module provides the application factory pattern for creating FastAPI
instances, following the Open/Closed Principle (OCP) from SOLID.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import cast

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.config import WebConfig, get_config

logger = logging.getLogger(__name__)


def create_app(config: WebConfig | None = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    This factory function creates a new FastAPI application with all necessary
    configuration, routes, middleware, and dependencies. It follows the Factory
    pattern and ensures proper separation of concerns.

    Args:
        config: Optional WebConfig instance. If not provided, configuration
                will be loaded from environment variables.

    Returns:
        Configured FastAPI application instance

    Example:
        >>> app = create_app()
        >>> # Or with custom config:
        >>> custom_config = WebConfig(host="127.0.0.1", port=9000)
        >>> app = create_app(config=custom_config)
    """
    # Use provided config or load from environment
    if config is None:
        config = get_config()

    # Configure structured logging with database support
    from src.api.logging_config import configure_logging_with_db

    # Get PostgreSQL DSN from environment
    postgres_dsn = os.environ.get("POSTGRES_DSN")
    if postgres_dsn:
        configure_logging_with_db(
            level=config.log_level.upper(),
            use_json=True,
            db_dsn=postgres_dsn,
            service_name="web",
            db_min_level=os.environ.get("LOG_LEVEL_DB_MIN", "INFO"),
            db_buffer_size=int(os.environ.get("LOG_BUFFER_SIZE", "100")),
            db_buffer_timeout=float(os.environ.get("LOG_BUFFER_TIMEOUT", "5.0")),
        )

    # Lifespan startup/shutdown logic
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        from src.api.repositories.query_history_repository import create_tables

        try:
            logger.info("Creating query_history table if it doesn't exist...")
            await create_tables(app.state.db_service.get_engine())
            logger.info("Query history table ready")
        except Exception as e:
            logger.error(f"Failed to create query_history table: {e}")
        yield

    # Create FastAPI application
    app = FastAPI(
        title="Odin Web Interface",
        version="1.6.0",
        description="A modern web interface for the Odin project, "
        "built with FastAPI and following SOLID principles.",
        lifespan=lifespan,
    )

    # Store configuration in app state
    app.state.config = config

    # Create DatabaseService instance
    from src.api.services.database import DatabaseService

    db_service = DatabaseService(dsn=config.postgres_dsn)
    app.state.db_service = db_service

    # Initialize services for Confluence integration
    from src.api.services.vault import VaultService
    from src.api.services.storage import StorageService
    from src.api.services.ollama import OllamaService

    # Vault service
    vault_addr = os.environ.get("VAULT_ADDR", "http://vault:8200")
    vault_token = os.environ.get("VAULT_TOKEN", "dev-only-token")
    vault_service = VaultService(addr=vault_addr, token=vault_token)
    app.state.vault_service = vault_service

    # Storage service (MinIO)
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    minio_access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    storage_service = StorageService(
        endpoint=minio_endpoint,
        access_key=minio_access_key,
        secret_key=minio_secret_key,
        secure=False,
    )
    app.state.storage_service = storage_service

    # Ollama service for LLM
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
    ollama_service = OllamaService(base_url=ollama_base_url)
    app.state.ollama_service = ollama_service

    # Configure templates
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Configure static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register routes
    from src.web.routes.confluence import router as confluence_router
    from src.web.routes.database import router as database_router
    from src.web.routes.files import router as files_router
    from src.web.routes.health import router as health_router
    from src.web.routes.home import router as home_router
    from src.web.routes.image_analyzer import router as image_analyzer_router
    from src.web.routes.logs import router as logs_router
    from src.web.routes.tasks import router as tasks_router

    app.include_router(home_router)
    app.include_router(tasks_router)
    app.include_router(health_router)
    app.include_router(logs_router)
    app.include_router(image_analyzer_router)
    app.include_router(confluence_router)
    app.include_router(files_router)
    app.include_router(database_router)

    # Explicit alias: /health-page -> health_page
    from fastapi.responses import HTMLResponse
    from src.web.routes.health import health_page

    app.add_api_route(
        "/health-page", endpoint=health_page, response_class=HTMLResponse, methods=["GET"]
    )

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Dictionary with status information
        """
        return {"status": "healthy", "service": "odin-web"}

    return app


def get_config_dependency(app: FastAPI) -> WebConfig:
    """Dependency injection function for accessing configuration.

    This function provides FastAPI's dependency injection system access to
    the application configuration, following the Dependency Inversion
    Principle (DIP) from SOLID.

    Args:
        app: The FastAPI application instance

    Returns:
        The application's configuration

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/info")
        >>> async def info(config: WebConfig = Depends(get_config_dependency)):
        >>>     return {"host": config.host, "port": config.port}
    """
    return cast(WebConfig, app.state.config)
