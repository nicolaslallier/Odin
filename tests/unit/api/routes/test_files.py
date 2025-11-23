"""Unit tests for file management routes."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.config import APIConfig
from src.api.routes.files import router


class TestFileRoutes:
    """Test suite for file routes."""

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
        from src.api.services.container import ServiceContainer

        app = FastAPI()
        app.state.config = mock_config

        # Create a mock container with mock services
        mock_container = MagicMock(spec=ServiceContainer)
        mock_container.storage = MagicMock()
        app.state.container = mock_container

        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_upload_file_success(self, client: TestClient, app: FastAPI) -> None:
        """Test file upload endpoint."""
        from src.api.routes.files import get_storage_service

        mock_storage = MagicMock()
        mock_storage.bucket_exists.return_value = True
        mock_storage.upload_file = MagicMock()

        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
            response = client.post(
                "/files/upload?bucket=test-bucket&key=test.txt",
                files=files,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["bucket"] == "test-bucket"
            assert data["key"] == "test.txt"
        finally:
            app.dependency_overrides.clear()

    def test_list_files_success(self, client: TestClient, app: FastAPI) -> None:
        """Test file listing endpoint."""
        from src.api.routes.files import get_storage_service

        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["file1.txt", "file2.txt"]

        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            response = client.get("/files/?bucket=test-bucket")

            assert response.status_code == 200
            data = response.json()
            assert data["bucket"] == "test-bucket"
            assert data["files"] == ["file1.txt", "file2.txt"]
        finally:
            app.dependency_overrides.clear()

    def test_delete_file_success(self, client: TestClient, app: FastAPI) -> None:
        """Test file deletion endpoint."""
        from src.api.routes.files import get_storage_service

        mock_storage = MagicMock()
        mock_storage.delete_file = MagicMock()

        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            response = client.delete("/files/test.txt?bucket=test-bucket")

            assert response.status_code == 200
            data = response.json()
            assert "deleted" in data["message"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_upload_file_with_bucket_creation(self, client: TestClient, app: FastAPI) -> None:
        """Test file upload when bucket doesn't exist."""
        from src.api.routes.files import get_storage_service

        mock_storage = MagicMock()
        mock_storage.bucket_exists.return_value = False
        mock_storage.create_bucket = MagicMock()
        mock_storage.upload_file = MagicMock()

        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
            response = client.post(
                "/files/upload?bucket=test-bucket&key=test.txt",
                files=files,
            )

            assert response.status_code == 200
            mock_storage.create_bucket.assert_called_once_with("test-bucket")
            mock_storage.upload_file.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_list_files_with_prefix(self, client: TestClient, app: FastAPI) -> None:
        """Test file listing with prefix."""
        from src.api.routes.files import get_storage_service

        mock_storage = MagicMock()
        mock_storage.list_files.return_value = ["prefix/file1.txt"]

        app.dependency_overrides[get_storage_service] = lambda: mock_storage

        try:
            response = client.get("/files/?bucket=test-bucket&prefix=prefix/")

            assert response.status_code == 200
            data = response.json()
            assert data["bucket"] == "test-bucket"
            assert "prefix/file1.txt" in data["files"]
        finally:
            app.dependency_overrides.clear()
