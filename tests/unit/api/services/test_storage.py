"""Unit tests for MinIO storage service.

This module tests the storage service client for file operations,
bucket management, and metadata handling.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.api.services.storage import StorageService


class TestStorageService:
    """Test suite for StorageService."""

    @pytest.fixture
    def mock_minio_client(self) -> MagicMock:
        """Create a mock MinIO client."""
        return MagicMock()

    @pytest.fixture
    def storage_service(self) -> StorageService:
        """Create a StorageService instance."""
        return StorageService(
            endpoint="minio:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )

    def test_storage_service_initialization(self) -> None:
        """Test that StorageService initializes with credentials."""
        service = StorageService(
            endpoint="minio:9000",
            access_key="admin",
            secret_key="password",
            secure=True,
        )
        assert service.endpoint == "minio:9000"
        assert service.access_key == "admin"
        assert service.secret_key == "password"
        assert service.secure is True

    def test_get_client_creates_client(self, storage_service: StorageService) -> None:
        """Test that get_client creates a MinIO client."""
        with patch("src.api.services.storage.Minio") as mock_minio:
            mock_client = MagicMock()
            mock_minio.return_value = mock_client
            
            client = storage_service.get_client()
            
            assert client == mock_client
            mock_minio.assert_called_once_with(
                endpoint="minio:9000",
                access_key="minioadmin",
                secret_key="minioadmin",
                secure=False,
            )

    def test_bucket_exists_returns_true(self, storage_service: StorageService) -> None:
        """Test bucket_exists returns True when bucket exists."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.bucket_exists.return_value = True
            mock_get_client.return_value = mock_client
            
            result = storage_service.bucket_exists("test-bucket")
            
            assert result is True
            mock_client.bucket_exists.assert_called_once_with("test-bucket")

    def test_bucket_exists_returns_false(self, storage_service: StorageService) -> None:
        """Test bucket_exists returns False when bucket does not exist."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.bucket_exists.return_value = False
            mock_get_client.return_value = mock_client
            
            result = storage_service.bucket_exists("test-bucket")
            
            assert result is False

    def test_create_bucket_success(self, storage_service: StorageService) -> None:
        """Test create_bucket creates a new bucket."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            # Mock bucket_exists to return False so create_bucket will actually call make_bucket
            with patch.object(storage_service, "bucket_exists", return_value=False):
                storage_service.create_bucket("test-bucket")
            
            mock_client.make_bucket.assert_called_once_with("test-bucket")

    def test_upload_file_success(self, storage_service: StorageService) -> None:
        """Test upload_file uploads a file to bucket."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            file_data = BytesIO(b"test content")
            
            storage_service.upload_file("bucket", "key.txt", file_data, len(b"test content"))
            
            mock_client.put_object.assert_called_once()
            call_args = mock_client.put_object.call_args
            assert call_args[0][0] == "bucket"
            assert call_args[0][1] == "key.txt"
            assert call_args[0][3] == len(b"test content")

    def test_download_file_success(self, storage_service: StorageService) -> None:
        """Test download_file retrieves a file from bucket."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.read.return_value = b"file content"
            mock_client.get_object.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = storage_service.download_file("bucket", "key.txt")
            
            assert result == b"file content"
            mock_client.get_object.assert_called_once_with("bucket", "key.txt")

    def test_delete_file_success(self, storage_service: StorageService) -> None:
        """Test delete_file removes a file from bucket."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            
            storage_service.delete_file("bucket", "key.txt")
            
            mock_client.remove_object.assert_called_once_with("bucket", "key.txt")

    def test_list_files_success(self, storage_service: StorageService) -> None:
        """Test list_files returns list of files in bucket."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_object1 = MagicMock()
            mock_object1.object_name = "file1.txt"
            mock_object2 = MagicMock()
            mock_object2.object_name = "file2.txt"
            mock_client.list_objects.return_value = [mock_object1, mock_object2]
            mock_get_client.return_value = mock_client
            
            result = storage_service.list_files("bucket")
            
            assert result == ["file1.txt", "file2.txt"]
            mock_client.list_objects.assert_called_once_with("bucket", prefix="")

    def test_health_check_success(self, storage_service: StorageService) -> None:
        """Test health check returns True when MinIO is accessible."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_buckets.return_value = []
            mock_get_client.return_value = mock_client
            
            result = storage_service.health_check()
            
            assert result is True
            mock_client.list_buckets.assert_called_once()

    def test_health_check_failure(self, storage_service: StorageService) -> None:
        """Test health check returns False when MinIO is not accessible."""
        with patch.object(storage_service, "get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.list_buckets.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client
            
            result = storage_service.health_check()
            
            assert result is False

