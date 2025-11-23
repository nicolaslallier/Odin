"""Entry point for Health microservice.

Run with: python -m src.api.apps.__main__health__
"""

from __future__ import annotations

import uvicorn

from src.api.config import get_config

if __name__ == "__main__":
    config = get_config()
    
    # Use import string for reload support
    if config.reload:
        uvicorn.run(
            "src.api.apps.health_app:app",
            host=config.host,
            port=config.port,
            reload=True,
            log_level=config.log_level,
        )
    else:
        from src.api.apps.health_app import create_app
        app = create_app(config)
        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            reload=False,
            log_level=config.log_level,
        )

