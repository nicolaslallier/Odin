"""Entry point for Data microservice.

Run with: python -m src.api.apps.__main__data__
"""

from __future__ import annotations

import uvicorn

from src.api.apps.data_app import create_app
from src.api.config import get_config

if __name__ == "__main__":
    config = get_config()
    app = create_app(config)

    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level,
    )

