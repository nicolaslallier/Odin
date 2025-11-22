"""Unit tests for batch processing tasks.

This module tests batch processing tasks for handling large datasets
and bulk operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.worker.tasks.batch import (
    process_bulk_data,
    process_file_batch,
    send_bulk_notifications,
)


class TestProcessBulkData:
    """Test suite for process_bulk_data task."""

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_success(self, mock_session_scope: MagicMock) -> None:
        """Test successful bulk data processing."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        data_items = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]

        # Act
        result = process_bulk_data(data_items)

        # Assert
        assert result["status"] == "success"
        assert result["processed"] == 2
        assert result["failed"] == 0

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_with_failures(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test bulk data processing with some failures."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        data_items = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": None},  # Will cause failure
            {"id": 3, "value": "c"},
        ]

        # Act
        result = process_bulk_data(data_items)

        # Assert
        assert "processed" in result
        assert "failed" in result
        assert result["processed"] + result["failed"] == 3

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_empty_list(self, mock_session_scope: MagicMock) -> None:
        """Test processing empty data list."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Act
        result = process_bulk_data([])

        # Assert
        assert result["status"] == "success"
        assert result["processed"] == 0
        assert result["failed"] == 0

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_validates_input(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test that bulk processing validates input data."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            process_bulk_data("not a list")  # type: ignore

        assert "list" in str(exc_info.value).lower()

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_batch_size_limit(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test that bulk processing respects batch size limits."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        large_batch = [{"id": i, "value": f"item_{i}"} for i in range(10000)]

        # Act
        result = process_bulk_data(large_batch, batch_size=1000)

        # Assert
        assert result["status"] == "success"
        assert result["batches"] == 10


class TestProcessFileBatch:
    """Test suite for process_file_batch task."""

    @patch("src.worker.tasks.batch.Path")
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_files_success(
        self, mock_minio: MagicMock, mock_path: MagicMock
    ) -> None:
        """Test successful file batch processing."""
        # Arrange
        file_paths = ["file1.txt", "file2.txt", "file3.txt"]
        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        # Act
        result = process_file_batch(file_paths)

        # Assert
        assert result["status"] == "success"
        assert result["processed"] == 3
        assert result["failed"] == 0

    @patch("src.worker.tasks.batch.Path")
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_files_with_invalid_paths(
        self, mock_minio: MagicMock, mock_path: MagicMock
    ) -> None:
        """Test file processing with invalid paths."""
        # Arrange
        file_paths = ["valid.txt", "", "another.txt"]
        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        # Act
        result = process_file_batch(file_paths)

        # Assert
        assert "failed" in result
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.Path")
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_files_empty_list(
        self, mock_minio: MagicMock, mock_path: MagicMock
    ) -> None:
        """Test processing empty file list."""
        # Arrange
        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        # Act
        result = process_file_batch([])

        # Assert
        assert result["status"] == "success"
        assert result["processed"] == 0

    @patch("src.worker.tasks.batch.Path")
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_files_uploads_to_minio(
        self, mock_minio: MagicMock, mock_path: MagicMock
    ) -> None:
        """Test that files are uploaded to MinIO."""
        # Arrange
        file_paths = ["file1.txt"]
        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        # Act
        result = process_file_batch(file_paths, upload_to_storage=True)

        # Assert
        assert result["uploaded"] == 1


class TestSendBulkNotifications:
    """Test suite for send_bulk_notifications task."""

    @patch("src.worker.tasks.batch.httpx")
    def test_send_notifications_success(self, mock_httpx: MagicMock) -> None:
        """Test successful bulk notification sending."""
        # Arrange
        notifications = [
            {"user_id": 1, "message": "Hello"},
            {"user_id": 2, "message": "World"},
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        # Act
        result = send_bulk_notifications(notifications)

        # Assert
        assert result["status"] == "success"
        assert result["sent"] == 2
        assert result["failed"] == 0

    @patch("src.worker.tasks.batch.httpx")
    def test_send_notifications_with_failures(self, mock_httpx: MagicMock) -> None:
        """Test notification sending with some failures."""
        # Arrange
        notifications = [
            {"user_id": 1, "message": "Hello"},
            {"user_id": 2, "message": "World"},
        ]
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500

        mock_httpx.post.side_effect = [mock_response_success, mock_response_fail]

        # Act
        result = send_bulk_notifications(notifications)

        # Assert
        assert result["sent"] + result["failed"] == 2
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.httpx")
    def test_send_notifications_validates_format(self, mock_httpx: MagicMock) -> None:
        """Test that notification data is validated."""
        # Arrange
        invalid_notifications = [{"invalid": "data"}]

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            send_bulk_notifications(invalid_notifications)

        assert "user_id" in str(exc_info.value).lower() or "message" in str(
            exc_info.value
        ).lower()

    @patch("src.worker.tasks.batch.httpx")
    def test_send_notifications_rate_limiting(self, mock_httpx: MagicMock) -> None:
        """Test that notification sending respects rate limits."""
        # Arrange
        notifications = [{"user_id": i, "message": f"Msg {i}"} for i in range(100)]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx.post.return_value = mock_response

        # Act
        result = send_bulk_notifications(notifications, rate_limit=10)

        # Assert
        assert result["status"] == "success"
        assert "rate_limited" in result

