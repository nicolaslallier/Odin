"""Unit tests for microservice application factories.

This module tests that each microservice app is correctly configured.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from src.api.config import APIConfig


class TestMicroserviceApps:
    """Test suite for all microservice app factories."""

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

    @pytest.mark.parametrize(
        "app_module,service_name,router_module",
        [
            ("confluence_app", "confluence", "confluence"),
            ("files_app", "files", "files"),
            ("llm_app", "llm", "llm"),
            ("health_app", "health", "health"),
            ("logs_app", "logs", "logs"),
            ("data_app", "data", "data"),
            ("secrets_app", "secrets", "secrets"),
            ("messages_app", "messages", "messages"),
            ("image_analysis_app", "image-analysis", "image_analysis"),
        ],
    )
    def test_microservice_app_creation(
        self,
        app_module: str,
        service_name: str,
        router_module: str,
        mock_config: APIConfig,
    ):
        """Test each microservice app can be created."""
        # Import the app module dynamically
        module = __import__(f"src.api.apps.{app_module}", fromlist=["create_app"])
        create_app = module.create_app
        
        # Create the app
        app = create_app(config=mock_config)
        
        # Verify it's a FastAPI instance
        assert isinstance(app, FastAPI)
        
        # Verify title contains service name
        assert service_name in app.title.lower() or service_name.replace("-", " ") in app.title.lower()

    @pytest.mark.parametrize(
        "app_module",
        [
            "confluence_app",
            "files_app",
            "llm_app",
            "health_app",
            "logs_app",
            "data_app",
            "secrets_app",
            "messages_app",
            "image_analysis_app",
        ],
    )
    def test_microservice_has_routes(self, app_module: str, mock_config: APIConfig):
        """Test each microservice has registered routes."""
        # Import the app module dynamically
        module = __import__(f"src.api.apps.{app_module}", fromlist=["create_app"])
        create_app = module.create_app
        
        # Create the app
        app = create_app(config=mock_config)
        
        # Verify it has routes (more than just internal/activity)
        assert len(app.routes) > 1

    def test_all_apps_have_activity_endpoint(self, mock_config: APIConfig):
        """Test all microservice apps have the /internal/activity endpoint."""
        app_modules = [
            "confluence_app",
            "files_app",
            "llm_app",
            "health_app",
            "logs_app",
            "data_app",
            "secrets_app",
            "messages_app",
            "image_analysis_app",
        ]
        
        for app_module in app_modules:
            # Import the app module dynamically
            module = __import__(f"src.api.apps.{app_module}", fromlist=["create_app"])
            create_app = module.create_app
            
            # Create the app
            app = create_app(config=mock_config)
            
            # Check for activity endpoint
            activity_route = None
            for route in app.routes:
                if hasattr(route, "path") and route.path == "/internal/activity":
                    activity_route = route
                    break
            
            assert activity_route is not None, f"{app_module} missing /internal/activity endpoint"

