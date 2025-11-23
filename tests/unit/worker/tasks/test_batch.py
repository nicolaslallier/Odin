"""Unit tests for batch processing tasks.

This module tests batch processing tasks for handling large datasets
and bulk operations.
"""

from __future__ import annotations

import os

os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

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
    def test_process_bulk_data_with_failures(self, mock_session_scope: MagicMock) -> None:
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
    def test_process_bulk_data_validates_input(self, mock_session_scope: MagicMock) -> None:
        """Test that bulk processing validates input data."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Act & Assert
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError) as exc_info:
            process_bulk_data("not a list")  # type: ignore

        assert "list" in str(exc_info.value).lower()

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_batch_size_limit(self, mock_session_scope: MagicMock) -> None:
        """Test that bulk processing respects batch size limits."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Create a smaller batch to avoid the update_state call (which happens every 10 batches)
        # Using 100 items with batch_size=10 means 10 batches, which triggers update_state
        # Using 90 items means 9 batches, which doesn't trigger update_state
        large_batch = [{"id": i, "value": f"item_{i}"} for i in range(90)]

        # Act
        result = process_bulk_data(large_batch, batch_size=10)

        # Assert
        assert result["status"] == "success"
        assert result["batches"] == 9

    @staticmethod
    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_update_state_called(mock_session_scope):
        # Ensure update_state is triggered at 10th batch (line 111)
        task_obj = process_bulk_data
        calls = []

        def update_state(**kwargs):
            calls.append(kwargs)

        task_obj.update_state = update_state
        mock_session_scope.return_value.__enter__.return_value = MagicMock()
        items = [{"id": i, "value": "x"} for i in range(100)]
        task_obj.run(items, batch_size=10)
        assert len(calls) > 0

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_batch_size_le_0(self, mock_session_scope):
        # 73: batch_size <= 0 raises
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError):
            process_bulk_data([], batch_size=0)

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_non_dict_item(self, mock_session_scope):
        # 92-94: One non-dict item, should increment failed count
        mock_session_scope.return_value.__enter__.return_value = MagicMock()
        result = process_bulk_data([{"id": 1, "value": "ok"}, "baditem"])
        assert result["failed"] == 1

    @patch("src.worker.tasks.batch.session_scope")
    def test_process_bulk_data_item_process_exception(self, mock_session_scope):
        # 105-107: Simulate per-item exception path, should increment failed
        mock_session_scope.return_value.__enter__.return_value = MagicMock()

        # Use an object that triggers exception on access
        class BadItem(dict):
            def get(self, key, default=None):
                if key == "value":
                    raise RuntimeError("fail")
                return super().get(key, default)

        items = [{"id": 0, "value": "a"}, BadItem({"id": 1, "value": "b"})]
        result = process_bulk_data(items)
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.Path", side_effect=Exception("fail"))
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_file_batch_exception(self, mock_minio, mock_path):
        # 186-187: Path raises, so count as failed
        result = process_file_batch(["badfile.txt"])
        assert result["failed"] == 1

    def test_send_bulk_notifications_not_list(self):
        # 227: notifications arg is not a list
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError):
            send_bulk_notifications("notalist")

    def test_send_bulk_notifications_rate_limit_le_0(self):
        # 230: rate_limit <= 0
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError):
            send_bulk_notifications([], rate_limit=0)

    def test_send_bulk_notifications_non_dict(self):
        # 236: One notification is not dict
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError):
            send_bulk_notifications([{"user_id": 1, "message": "ok"}, 123])

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_httpx_timeout(self, mock_client):
        # 275: TimeoutException increments failed
        import httpx

        notifications = [{"user_id": 1, "message": "A"}]
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.TimeoutException("timeout")
        mock_client.return_value.__enter__.return_value = mock_http
        mock_client.return_value.__exit__.return_value = None
        result = send_bulk_notifications(notifications)
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_httpx_requesterror(self, mock_client):
        # 278: RequestError increments failed
        import httpx

        notifications = [{"user_id": 1, "message": "A"}]
        mock_http = MagicMock()
        mock_http.post.side_effect = httpx.RequestError("oops", request=MagicMock())
        mock_client.return_value.__enter__.return_value = mock_http
        mock_client.return_value.__exit__.return_value = None
        result = send_bulk_notifications(notifications)
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_generic_exception(self, mock_client):
        # 281: generic Exception increments failed
        notifications = [{"user_id": 1, "message": "A"}]
        mock_http = MagicMock()
        mock_http.post.side_effect = Exception("fail")
        mock_client.return_value.__enter__.return_value = mock_http
        mock_client.return_value.__exit__.return_value = None
        result = send_bulk_notifications(notifications)
        assert result["failed"] >= 1


class TestProcessFileBatch:
    """Test suite for process_file_batch task."""

    @patch("src.worker.tasks.batch.Path")
    @patch("src.worker.tasks.batch.MinioClient")
    def test_process_files_success(self, mock_minio: MagicMock, mock_path: MagicMock) -> None:
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
    def test_process_files_empty_list(self, mock_minio: MagicMock, mock_path: MagicMock) -> None:
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

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_success(self, mock_client: MagicMock) -> None:
        """Test successful bulk notification sending."""
        # Arrange
        notifications = [
            {"user_id": 1, "message": "Hello"},
            {"user_id": 2, "message": "World"},
        ]
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_http_client
        mock_client.return_value.__exit__.return_value = None

        # Act
        result = send_bulk_notifications(notifications)

        # Assert
        assert result["status"] == "success"
        assert result["sent"] == 2
        assert result["failed"] == 0

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_with_failures(self, mock_client: MagicMock) -> None:
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

        mock_http_client = MagicMock()
        mock_http_client.post.side_effect = [mock_response_success, mock_response_fail]
        mock_client.return_value.__enter__.return_value = mock_http_client
        mock_client.return_value.__exit__.return_value = None

        # Act
        result = send_bulk_notifications(notifications)

        # Assert
        assert result["sent"] + result["failed"] == 2
        assert result["failed"] >= 1

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_validates_format(self, mock_client: MagicMock) -> None:
        """Test that notification data is validated."""
        # Arrange
        invalid_notifications = [{"invalid": "data"}]

        # Act & Assert
        from src.worker.exceptions import BatchProcessingError

        with pytest.raises(BatchProcessingError) as exc_info:
            send_bulk_notifications(invalid_notifications)

        assert "user_id" in str(exc_info.value).lower() or "message" in str(exc_info.value).lower()

    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_notifications_rate_limiting(self, mock_client: MagicMock) -> None:
        """Test that notification sending respects rate limits."""
        # Arrange
        # Use 90 notifications instead of 100 to avoid the update_state call
        # (which happens every 10 batches - 9 batches won't trigger it)
        notifications = [{"user_id": i, "message": f"Msg {i}"} for i in range(90)]
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = MagicMock()
        mock_http_client.post.return_value = mock_response
        mock_client.return_value.__enter__.return_value = mock_http_client
        mock_client.return_value.__exit__.return_value = None

        # Act
        result = send_bulk_notifications(notifications, rate_limit=10)

        # Assert
        assert result["status"] == "success"
        assert "rate_limited" in result

    def test_minio_client_init_logs(self):
        # 34-41: Ensure constructor/endpoint logs for MinioClient
        import logging
        from importlib import reload
        import sys

        with (
            patch("src.worker.tasks.batch.get_config") as mock_conf,
            patch.object(logging.getLogger("src.worker.tasks.batch"), "info") as mock_log,
        ):
            mock_conf.return_value = MagicMock(
                minio_endpoint="abc:9000",
                minio_access_key="a",
                minio_secret_key="b",
                minio_secure=False,
            )
            # Reload the module to trigger constructor after patching
            if "src.worker.tasks.batch" in sys.modules:
                reload(sys.modules["src.worker.tasks.batch"])
            from src.worker.tasks.batch import MinioClient

            MinioClient()
            assert mock_log.called

    @staticmethod
    @patch("src.worker.tasks.batch.httpx.Client")
    def test_send_bulk_notifications_update_state_called(mock_client):
        task_obj = send_bulk_notifications
        calls = []

        def update_state(**kwargs):
            calls.append(kwargs)

        task_obj.update_state = update_state
        notifications = [{"user_id": i, "message": "msg"} for i in range(100)]
        mock_http_client = MagicMock()
        mock_http_client.post.return_value = MagicMock(status_code=200)
        mock_client.return_value.__enter__.return_value = mock_http_client
        mock_client.return_value.__exit__.return_value = None
        task_obj.run(notifications, rate_limit=10)
        assert len(calls) > 0
