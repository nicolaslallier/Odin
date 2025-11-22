"""Unit tests for API configuration management.

This module tests the configuration loading and validation for the API service,
ensuring all service connection parameters are properly loaded from environment.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.api.config import APIConfig, get_config


class TestAPIConfig:
    """Test suite for APIConfig configuration management."""

    def test_config_default_values(self) -> None:
        """Test that APIConfig has sensible defaults."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.host == "0.0.0.0"
            assert config.port == 8001
            assert config.log_level == "info"
            assert config.reload is False

    def test_config_from_environment(self) -> None:
        """Test that configuration is loaded from environment variables."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "127.0.0.1",
                "API_PORT": "9000",
                "API_LOG_LEVEL": "debug",
                "API_RELOAD": "true",
                "POSTGRES_DSN": "postgresql://odin:pass@pg:5432/odin",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "minioadmin",
                "MINIO_SECRET_KEY": "minioadmin",
                "MINIO_SECURE": "false",
                "RABBITMQ_URL": "amqp://odin:pass@rabbitmq:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "dev-token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.host == "127.0.0.1"
            assert config.port == 9000
            assert config.log_level == "debug"
            assert config.reload is True

    def test_config_postgres_dsn(self) -> None:
        """Test PostgreSQL DSN configuration."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://odin:password@postgresql:5432/odin_db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.postgres_dsn == "postgresql://odin:password@postgresql:5432/odin_db"

    def test_config_minio_settings(self) -> None:
        """Test MinIO configuration settings."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "minioadmin",
                "MINIO_SECRET_KEY": "minioadmin",
                "MINIO_SECURE": "false",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.minio_endpoint == "minio:9000"
            assert config.minio_access_key == "minioadmin"
            assert config.minio_secret_key == "minioadmin"
            assert config.minio_secure is False

    def test_config_rabbitmq_url(self) -> None:
        """Test RabbitMQ URL configuration."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://odin:odin_password@rabbitmq:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.rabbitmq_url == "amqp://odin:odin_password@rabbitmq:5672/"

    def test_config_vault_settings(self) -> None:
        """Test Vault configuration settings."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "dev-root-token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.vault_addr == "http://vault:8200"
            assert config.vault_token == "dev-root-token"

    def test_config_ollama_base_url(self) -> None:
        """Test Ollama base URL configuration."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            assert config.ollama_base_url == "http://ollama:11434"

    def test_config_is_frozen(self) -> None:
        """Test that configuration is immutable after creation."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = APIConfig()
            with pytest.raises(ValidationError):
                config.host = "1.2.3.4"  # type: ignore

    def test_config_invalid_port(self) -> None:
        """Test that invalid port raises validation error."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "invalid",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            with pytest.raises(ValidationError):
                APIConfig()

    def test_get_config_singleton(self) -> None:
        """Test that get_config returns a configuration instance."""
        with patch.dict(
            os.environ,
            {
                "API_HOST": "0.0.0.0",
                "API_PORT": "8001",
                "POSTGRES_DSN": "postgresql://user:pass@host:5432/db",
                "MINIO_ENDPOINT": "minio:9000",
                "MINIO_ACCESS_KEY": "admin",
                "MINIO_SECRET_KEY": "password",
                "RABBITMQ_URL": "amqp://user:pass@host:5672/",
                "VAULT_ADDR": "http://vault:8200",
                "VAULT_TOKEN": "token",
                "OLLAMA_BASE_URL": "http://ollama:11434",
            },
            clear=True,
        ):
            config = get_config()
            assert isinstance(config, APIConfig)
            assert config.host == "0.0.0.0"
            assert config.port == 8001

