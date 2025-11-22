"""Unit tests for API app factory.

This module tests the FastAPI application creation and configuration.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import APIConfig


class TestAppFactory:
    """Test suite for API app factory."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI application."""
        mock_config = APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="admin",
            minio_secret_key="password",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="token",
            ollama_base_url="http://ollama:11434",
        )
        
        app = create_app(mock_config)
        
        assert isinstance(app, FastAPI)
        assert app.title == "Odin API Service"

    def test_app_has_health_endpoint(self) -> None:
        """Test that app includes health check endpoint."""
        mock_config = APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="admin",
            minio_secret_key="password",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="token",
            ollama_base_url="http://ollama:11434",
        )
        
        app = create_app(mock_config)
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_app_includes_all_routers(self) -> None:
        """Test that app includes all route modules."""
        mock_config = APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="admin",
            minio_secret_key="password",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="token",
            ollama_base_url="http://ollama:11434",
        )
        
        app = create_app(mock_config)
        
        # Check routes are registered
        routes = [route.path for route in app.routes]
        assert any("/health" in route for route in routes)
        assert any("/files" in route for route in routes)
        assert any("/llm" in route for route in routes)

    def test_create_app_with_custom_config(self) -> None:
        """Test creating app with custom configuration."""
        config = APIConfig(
            host="127.0.0.1",
            port=9000,
            postgres_dsn="postgresql://custom:pass@localhost:5432/custom",
            minio_endpoint="minio:9000",
            minio_access_key="admin",
            minio_secret_key="password",
            rabbitmq_url="amqp://custom:pass@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="custom-token",
            ollama_base_url="http://ollama:11434",
        )
        
        app = create_app(config)
        
        assert isinstance(app, FastAPI)
        assert app.state.config == config

    def test_create_app_without_config(self) -> None:
        """Test create_app loads config from environment when not provided."""
        with patch("src.api.app.get_config") as mock_get_config:
            mock_config = APIConfig(
                host="0.0.0.0",
                port=8001,
                postgres_dsn="postgresql://test:test@localhost:5432/test",
                minio_endpoint="minio:9000",
                minio_access_key="admin",
                minio_secret_key="password",
                rabbitmq_url="amqp://test:test@localhost:5672/",
                vault_addr="http://vault:8200",
                vault_token="token",
                ollama_base_url="http://ollama:11434",
            )
            mock_get_config.return_value = mock_config
            
            app = create_app()
            
            assert isinstance(app, FastAPI)
            mock_get_config.assert_called_once()

