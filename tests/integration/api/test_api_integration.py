"""Integration tests for API service.

This module tests the full API application with all routes integrated.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.config import APIConfig


class TestAPIIntegration:
    """Integration test suite for full API application."""

    @pytest.fixture
    def app_config(self) -> APIConfig:
        """Create test configuration."""
        return APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            minio_secure=False,
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="dev-root-token",
            ollama_base_url="http://ollama:11434",
        )

    @pytest.fixture
    def client(self, app_config: APIConfig) -> TestClient:
        """Create test client with test config."""
        app = create_app(app_config)
        return TestClient(app)

    def test_app_health_endpoint(self, client: TestClient) -> None:
        """Test that health endpoint is accessible."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "odin-api"

    def test_data_crud_operations(self, client: TestClient) -> None:
        """Test CRUD operations for data endpoints."""
        # Create
        create_response = client.post(
            "/data/",
            json={"name": "Test Item", "description": "Test description"},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["name"] == "Test Item"
        assert created["id"] is not None
        
        item_id = created["id"]
        
        # Read
        read_response = client.get(f"/data/{item_id}")
        assert read_response.status_code == 200
        read_item = read_response.json()
        assert read_item["id"] == item_id
        assert read_item["name"] == "Test Item"
        
        # Update
        update_response = client.put(
            f"/data/{item_id}",
            json={"name": "Updated Item", "description": "Updated"},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["name"] == "Updated Item"
        
        # List
        list_response = client.get("/data/")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] >= 1
        
        # Delete
        delete_response = client.delete(f"/data/{item_id}")
        assert delete_response.status_code == 200

    def test_app_includes_all_routes(self, client: TestClient) -> None:
        """Test that all expected routes are registered."""
        openapi_schema = client.app.openapi()
        paths = openapi_schema["paths"]
        
        # Check key endpoints exist
        assert "/health" in paths
        assert "/data/" in paths or any("/data" in path for path in paths)
        assert any("/files" in path for path in paths)
        assert any("/llm" in path for path in paths)

