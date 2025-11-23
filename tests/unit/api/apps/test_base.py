"""Unit tests for base microservice app factory.

This module tests the base application factory used by all microservices.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from src.api.apps.base import create_base_app, get_container
from src.api.config import APIConfig


class TestCreateBaseApp:
    """Test suite for create_base_app function."""

    @pytest.fixture
    def mock_config(self) -> APIConfig:
        """Create a mock configuration."""
        return APIConfig(
            host="localhost",
            port=8001,
            postgres_dsn="postgresql+asyncpg://user:pass@localhost/db",
            minio_endpoint="localhost:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            rabbitmq_url="amqp://user:pass@localhost/",
            vault_addr="http://localhost:8200",
            vault_token="token",
            ollama_base_url="http://localhost:11434",
        )

    def test_creates_fastapi_app(self, mock_config: APIConfig):
        """Test function creates a FastAPI app."""
        app = create_base_app("test-service", config=mock_config)
        
        assert isinstance(app, FastAPI)
        assert "Test-Service" in app.title
        assert app.state.config == mock_config

    def test_app_has_correct_metadata(self, mock_config: APIConfig):
        """Test app has correct title and description."""
        app = create_base_app("confluence", version="1.0.0", config=mock_config)
        
        assert "Confluence" in app.title
        assert "confluence" in app.description.lower()
        assert app.version == "1.0.0"

    def test_app_has_inactivity_tracking(self, mock_config: APIConfig):
        """Test app includes inactivity tracking."""
        app = create_base_app("test-service", config=mock_config)
        
        # Check middleware was added (inactivity tracking adds middleware)
        assert len(app.user_middleware) > 0

    def test_app_uses_default_config_if_none_provided(self):
        """Test app uses default config when none provided."""
        with patch("src.api.apps.base.get_config") as mock_get_config:
            mock_get_config.return_value = MagicMock()
            
            app = create_base_app("test-service")
            
            mock_get_config.assert_called_once()

    def test_app_stores_config_in_state(self, mock_config: APIConfig):
        """Test app stores config in state."""
        app = create_base_app("test-service", config=mock_config)
        
        assert hasattr(app.state, "config")
        assert app.state.config == mock_config


class TestGetContainer:
    """Test suite for get_container function."""

    def test_returns_container_from_app_state(self):
        """Test function returns container from app state."""
        app = FastAPI()
        mock_container = MagicMock()
        app.state.container = mock_container
        
        mock_request = MagicMock()
        mock_request.app = app
        
        container = get_container(mock_request)
        
        assert container is mock_container

    def test_raises_error_if_container_not_initialized(self):
        """Test function raises error if container not in app state."""
        app = FastAPI()
        mock_request = MagicMock()
        mock_request.app = app
        
        with pytest.raises(RuntimeError, match="Service container not initialized"):
            get_container(mock_request)

