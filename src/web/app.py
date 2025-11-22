"""FastAPI application factory.

This module provides the application factory pattern for creating FastAPI
instances, following the Open/Closed Principle (OCP) from SOLID.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.config import WebConfig, get_config


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

    # Create FastAPI application
    app = FastAPI(
        title="Odin Web Interface",
        version="1.1.0",
        description="A modern web interface for the Odin project, "
        "built with FastAPI and following SOLID principles.",
    )

    # Store configuration in app state
    app.state.config = config

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

    app.include_router(home_router)
    app.include_router(tasks_router)
    app.include_router(health_router)

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
    return app.state.config

