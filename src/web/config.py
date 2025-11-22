"""Web application configuration management.

This module provides configuration management for the web application,
following the Single Responsibility Principle (SRP) from SOLID.
"""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class WebConfig(BaseModel):
    """Web application configuration.

    This class manages all configuration parameters for the web application,
    with validation and default values.

    Attributes:
        host: The host address to bind the server to
        port: The port number to bind the server to
        reload: Whether to enable auto-reload in development mode
        log_level: The logging level for the application
    """

    host: str = Field(default="0.0.0.0", description="Host address to bind to")
    port: int = Field(default=8000, ge=1, le=65535, description="Port to bind to")
    reload: bool = Field(default=False, description="Enable auto-reload for development")
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info", description="Logging level"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = True  # Makes the config immutable

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that log level is one of the allowed values.

        Args:
            v: The log level to validate

        Returns:
            The validated log level

        Raises:
            ValueError: If log level is not valid
        """
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v

    def __str__(self) -> str:
        """Return a string representation of the configuration.

        Returns:
            String representation showing key configuration values
        """
        return (
            f"WebConfig(host={self.host}, port={self.port}, "
            f"reload={self.reload}, log_level={self.log_level})"
        )


def get_config() -> WebConfig:
    """Get web configuration from environment variables.

    This function reads configuration from environment variables and returns
    a validated WebConfig instance. If environment variables are not set,
    default values are used.

    Environment variables:
        WEB_HOST: Host address (default: 0.0.0.0)
        WEB_PORT: Port number (default: 8000)
        WEB_RELOAD: Auto-reload flag (default: false)
        WEB_LOG_LEVEL: Log level (default: info)

    Returns:
        WebConfig instance with values from environment or defaults

    Example:
        >>> config = get_config()
        >>> print(config.host)
        0.0.0.0
    """
    return WebConfig(
        host=os.environ.get("WEB_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_PORT", "8000")),
        reload=os.environ.get("WEB_RELOAD", "false").lower() in ("true", "1", "yes"),
        log_level=os.environ.get("WEB_LOG_LEVEL", "info"),
    )

