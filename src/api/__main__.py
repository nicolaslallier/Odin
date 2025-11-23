"""Entry point for the Odin API service.

This module starts the FastAPI application using uvicorn in development mode
with auto-reload support.
"""

from __future__ import annotations

import uvicorn

from src.api.config import get_config


def main() -> None:
    """Start the API server with configuration from environment."""
    config = get_config()

    uvicorn.run(
        "src.api.app:create_app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level,
        factory=True,
    )


if __name__ == "__main__":
    main()
