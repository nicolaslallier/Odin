"""API configuration management.

This module provides configuration management for the API service,
loading settings from environment variables and validating them using Pydantic.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APIConfig(BaseSettings):
    """Configuration for the API service.

    This class loads configuration from environment variables and provides
    type-safe access to all API settings including connections to backend services.

    Attributes:
        host: The host address to bind the API server to
        port: The port number to bind the API server to
        reload: Whether to enable auto-reload in development mode
        log_level: Logging level for the API server
        postgres_dsn: PostgreSQL connection string
        minio_endpoint: MinIO server endpoint
        minio_access_key: MinIO access key
        minio_secret_key: MinIO secret key
        minio_secure: Whether to use HTTPS for MinIO connection
        rabbitmq_url: RabbitMQ connection URL
        vault_addr: Vault server address
        vault_token: Vault authentication token
        ollama_base_url: Ollama API base URL
    """

    # API Server Settings
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8001, alias="API_PORT")
    reload: bool = Field(default=False, alias="API_RELOAD")
    log_level: str = Field(default="info", alias="API_LOG_LEVEL")

    # PostgreSQL Settings
    postgres_dsn: str = Field(alias="POSTGRES_DSN")

    # MinIO Settings
    minio_endpoint: str = Field(alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # RabbitMQ Settings
    rabbitmq_url: str = Field(alias="RABBITMQ_URL")

    # Vault Settings
    vault_addr: str = Field(alias="VAULT_ADDR")
    vault_token: str = Field(alias="VAULT_TOKEN")

    # Ollama Settings
    ollama_base_url: str = Field(alias="OLLAMA_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        frozen=True,
        extra="ignore",
    )


def get_config() -> APIConfig:
    """Get the API configuration.

    This function creates and returns an APIConfig instance loaded from
    environment variables. It can be used as a dependency injection point.

    Returns:
        Configured APIConfig instance

    Example:
        >>> config = get_config()
        >>> print(f"API running on {config.host}:{config.port}")
    """
    return APIConfig()

