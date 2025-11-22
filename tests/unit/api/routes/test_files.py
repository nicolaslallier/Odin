"""Unit tests for file management routes."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.files import router


class TestFileRoutes:
    """Test suite for file routes."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app."""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_upload_file_success(self, client: TestClient) -> None:
        """Test file upload endpoint."""
        with patch("src.api.routes.files.get_storage_service") as mock_service:
            mock_storage = MagicMock()
            mock_service.return_value = mock_storage
            
            files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
            response = client.post(
                "/files/upload?bucket=test-bucket&key=test.txt",
                files=files,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["bucket"] == "test-bucket"
            assert data["key"] == "test.txt"

    def test_list_files_success(self, client: TestClient) -> None:
        """Test file listing endpoint."""
        with patch("src.api.routes.files.get_storage_service") as mock_service:
            mock_storage = MagicMock()
            mock_storage.list_files.return_value = ["file1.txt", "file2.txt"]
            mock_service.return_value = mock_storage
            
            response = client.get("/files/?bucket=test-bucket")
            
            assert response.status_code == 200
            data = response.json()
            assert data["bucket"] == "test-bucket"
            assert data["files"] == ["file1.txt", "file2.txt"]

    def test_delete_file_success(self, client: TestClient) -> None:
        """Test file deletion endpoint."""
        with patch("src.api.routes.files.get_storage_service") as mock_service:
            mock_storage = MagicMock()
            mock_service.return_value = mock_storage
            
            response = client.delete("/files/test.txt?bucket=test-bucket")
            
            assert response.status_code == 200
            data = response.json()
            assert "deleted" in data["message"].lower()

