"""Unit tests for data CRUD routes."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.data import router, _data_store, _next_id


class TestDataRoutes:
    """Test suite for data CRUD routes."""

    @pytest.fixture
    def mock_config(self) -> APIConfig:
        """Create a mock configuration."""
        return APIConfig(
            host="0.0.0.0",
            port=8001,
            postgres_dsn="postgresql://test:test@localhost:5432/test",
            minio_endpoint="minio:9000",
            minio_access_key="minioadmin",
            minio_secret_key="minioadmin",
            rabbitmq_url="amqp://test:test@localhost:5672/",
            vault_addr="http://vault:8200",
            vault_token="test-token",
            ollama_base_url="http://ollama:11434",
        )

    @pytest.fixture
    def app(self, mock_config: APIConfig) -> FastAPI:
        """Create a test FastAPI app."""
        app = FastAPI()
        app.state.config = mock_config
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture(autouse=True)
    def clear_data_store(self) -> None:
        """Clear data store before each test."""
        _data_store.clear()
        # Reset next_id
        import src.api.routes.data as data_module
        data_module._next_id = 1

    def test_create_data_item(self, client: TestClient) -> None:
        """Test creating a data item."""
        response = client.post(
            "/data/",
            json={"name": "Test Item", "description": "Test description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Item"
        assert data["description"] == "Test description"
        assert data["id"] == 1

    def test_read_data_item_success(self, client: TestClient) -> None:
        """Test reading an existing data item."""
        # Create item first
        create_response = client.post(
            "/data/",
            json={"name": "Test Item", "description": "Test description"},
        )
        item_id = create_response.json()["id"]

        # Read item
        response = client.get(f"/data/{item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["name"] == "Test Item"

    def test_read_data_item_not_found(self, client: TestClient) -> None:
        """Test reading a non-existent data item."""
        response = client.get("/data/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_data_item_success(self, client: TestClient) -> None:
        """Test updating an existing data item."""
        # Create item first
        create_response = client.post(
            "/data/",
            json={"name": "Test Item", "description": "Test description"},
        )
        item_id = create_response.json()["id"]

        # Update item
        response = client.put(
            f"/data/{item_id}",
            json={"id": item_id, "name": "Updated Item", "description": "Updated description"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Item"
        assert data["description"] == "Updated description"

    def test_update_data_item_not_found(self, client: TestClient) -> None:
        """Test updating a non-existent data item."""
        response = client.put(
            "/data/999",
            json={"id": 999, "name": "Updated Item", "description": "Updated description"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_data_item_success(self, client: TestClient) -> None:
        """Test deleting an existing data item."""
        # Create item first
        create_response = client.post(
            "/data/",
            json={"name": "Test Item", "description": "Test description"},
        )
        item_id = create_response.json()["id"]

        # Delete item
        response = client.delete(f"/data/{item_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify item is gone
        get_response = client.get(f"/data/{item_id}")
        assert get_response.status_code == 404

    def test_delete_data_item_not_found(self, client: TestClient) -> None:
        """Test deleting a non-existent data item."""
        response = client.delete("/data/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_list_data_items_empty(self, client: TestClient) -> None:
        """Test listing data items when store is empty."""
        response = client.get("/data/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_data_items_with_data(self, client: TestClient) -> None:
        """Test listing data items with multiple items."""
        # Create multiple items
        client.post("/data/", json={"name": "Item 1", "description": "Desc 1"})
        client.post("/data/", json={"name": "Item 2", "description": "Desc 2"})
        client.post("/data/", json={"name": "Item 3", "description": "Desc 3"})

        # List items
        response = client.get("/data/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

