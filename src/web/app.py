"""FastAPI application factory.

This module provides the application factory pattern for creating FastAPI
instances, following the Open/Closed Principle (OCP) from SOLID.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.config import WebConfig, get_config

logger = logging.getLogger(__name__)


def create_app(config: Optional[WebConfig] = None) -> FastAPI:
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

    # Create FastAPI application
    app = FastAPI(
        title="Odin Web Interface",
        version="1.5.0",
        description="A modern web interface for the Odin project, "
        "built with FastAPI and following SOLID principles.",
    )

    # Store configuration in app state
    app.state.config = config

    # Create DatabaseService instance
    from src.api.services.database import DatabaseService
    db_service = DatabaseService(dsn=config.postgres_dsn)
    app.state.db_service = db_service

    # Configure templates
    templates_dir = Path(__file__).parent / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    app.state.templates = Jinja2Templates(directory=str(templates_dir))

    # Configure static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Register routes
    from src.web.routes.home import router as home_router
    from src.web.routes.tasks import router as tasks_router
    from src.web.routes.health import router as health_router
    from src.web.routes.logs import router as logs_router
    from src.web.routes.image_analyzer import router as image_analyzer_router
    from src.web.routes.files import router as files_router
    from src.web.routes.database import router as database_router

    app.include_router(home_router)
    app.include_router(tasks_router)
    app.include_router(health_router)
    app.include_router(logs_router)
    app.include_router(image_analyzer_router)
    app.include_router(files_router)
    app.include_router(database_router)

    # Add health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint.

        Returns:
            Dictionary with status information
        """
        return {"status": "healthy", "service": "odin-web"}

    # Startup event to initialize database tables
    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize database tables on startup."""
        from src.api.repositories.query_history_repository import create_tables
        
        logger.info("Creating query_history table if it doesn't exist...")
        try:
            # Access db_service from app state
            await create_tables(app.state.db_service.get_engine())
            logger.info("Query history table ready")
        except Exception as e:
            logger.error(f"Failed to create query_history table: {e}")

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
    return app.state.config

