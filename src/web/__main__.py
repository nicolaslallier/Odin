"""Main entry point for running the web application.

This module provides the entry point for running the web application
using uvicorn server.
"""

from __future__ import annotations

import uvicorn

from src.web.config import get_config


def main() -> None:
    """Run the web application server.

    This function creates the FastAPI application and runs it using
    uvicorn with configuration from environment variables.
    """
    config = get_config()

    # When reload is enabled, uvicorn requires an import string
    # When reload is disabled, we can pass the app instance directly
    if config.reload:
        # Use import string for reload mode
        uvicorn.run(
            "src.web.app:create_app",
            host=config.host,
            port=config.port,
            reload=config.reload,
            log_level=config.log_level,
            factory=True,
        )
    else:
        # Import and create app for production mode
        from src.web.app import create_app

        app = create_app(config)
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_level=config.log_level,
        )


if __name__ == "__main__":
    main()
