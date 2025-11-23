"""Unit tests for secrets management routes."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.secrets import router


class TestSecretsRoutes:
    """Test suite for secrets routes."""

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

    def test_write_secret_success(self, client: TestClient, app: FastAPI) -> None:
        """Test writing a secret to vault."""
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.write_secret = MagicMock()

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.post(
                "/secrets/",
                json={"path": "test/secret", "data": {"key": "value"}},
            )

            assert response.status_code == 200
            assert "written" in response.json()["message"].lower()
            mock_vault.write_secret.assert_called_once_with("test/secret", {"key": "value"})
        finally:
            app.dependency_overrides.clear()

    def test_write_secret_error(self, client: TestClient, app: FastAPI) -> None:
        """Test writing a secret with error."""
        from src.api.exceptions import VaultError
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.write_secret = MagicMock(side_effect=VaultError("Vault error"))

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.post(
                "/secrets/",
                json={"path": "test/secret", "data": {"key": "value"}},
            )

            assert response.status_code == 500
            assert "Vault error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_read_secret_success(self, client: TestClient, app: FastAPI) -> None:
        """Test reading a secret from vault."""
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.read_secret = MagicMock(return_value={"key": "value"})

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.get("/secrets/test/secret")

            assert response.status_code == 200
            assert response.json()["path"] == "test/secret"
            assert response.json()["data"] == {"key": "value"}
            mock_vault.read_secret.assert_called_once_with("test/secret")
        finally:
            app.dependency_overrides.clear()

    def test_read_secret_not_found(self, client: TestClient, app: FastAPI) -> None:
        """Test reading a non-existent secret."""
        from src.api.exceptions import ResourceNotFoundError
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.read_secret = MagicMock(side_effect=ResourceNotFoundError("Secret not found"))

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.get("/secrets/test/secret")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_read_secret_error(self, client: TestClient, app: FastAPI) -> None:
        """Test reading a secret with error."""
        from src.api.exceptions import VaultError
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.read_secret = MagicMock(side_effect=VaultError("Vault error"))

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.get("/secrets/test/secret")

            assert response.status_code == 500
            assert "Vault error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_delete_secret_success(self, client: TestClient, app: FastAPI) -> None:
        """Test deleting a secret from vault."""
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.delete_secret = MagicMock()

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.delete("/secrets/test/secret")

            assert response.status_code == 200
            assert "deleted" in response.json()["message"].lower()
            mock_vault.delete_secret.assert_called_once_with("test/secret")
        finally:
            app.dependency_overrides.clear()

    def test_delete_secret_error(self, client: TestClient, app: FastAPI) -> None:
        """Test deleting a secret with error."""
        from src.api.exceptions import VaultError
        from src.api.routes.secrets import get_vault_service

        mock_vault = MagicMock()
        mock_vault.delete_secret = MagicMock(side_effect=VaultError("Vault error"))

        app.dependency_overrides[get_vault_service] = lambda: mock_vault

        try:
            response = client.delete("/secrets/test/secret")

            assert response.status_code == 500
            assert "Vault error" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()
