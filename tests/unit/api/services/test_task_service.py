"""Unit tests for task service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.api.services.task_service import TaskService, get_task_service


@pytest.fixture
def mock_celery_app():
    """Create a mock Celery app."""
    app = MagicMock()
    return app


@pytest.fixture
def task_service(mock_celery_app):
    """Create a task service instance with mocked Celery."""
    with patch("src.api.services.task_service.get_celery_app", return_value=mock_celery_app):
        service = TaskService()
    return service


class TestTaskService:
    """Tests for TaskService class."""

    def test_initialization(self, mock_celery_app):
        """Test task service initialization."""
        with patch("src.api.services.task_service.get_celery_app", return_value=mock_celery_app):
            service = TaskService()
            assert service.celery_app == mock_celery_app

    def test_dispatch_bulk_data_processing(self, task_service):
        """Test dispatching bulk data processing task."""
        mock_task = MagicMock()
        mock_task.id = "task-123"

        with patch("src.worker.tasks.batch.process_bulk_data") as mock_process:
            mock_process.delay.return_value = mock_task

            data_items = [{"id": 1, "name": "Test"}]
            result = task_service.dispatch_bulk_data_processing(data_items)

            assert result["task_id"] == "task-123"
            assert result["status"] == "dispatched"
            mock_process.delay.assert_called_once_with(data_items)

    def test_dispatch_notification(self, task_service):
        """Test dispatching notification task."""
        mock_task = MagicMock()
        mock_task.id = "notif-456"

        with patch("src.worker.tasks.events.send_notification") as mock_send:
            mock_send.delay.return_value = mock_task

            notification_data = {
                "user_id": 123,
                "type": "email",
                "message": "Hello World",
            }
            result = task_service.dispatch_notification(notification_data)

            assert result["task_id"] == "notif-456"
            assert result["status"] == "dispatched"
            mock_send.delay.assert_called_once_with(notification_data)

    def test_dispatch_user_registration(self, task_service):
        """Test dispatching user registration task."""
        mock_task = MagicMock()
        mock_task.id = "user-789"

        with patch("src.worker.tasks.events.handle_user_registration") as mock_register:
            mock_register.delay.return_value = mock_task

            user_data = {"user_id": 456, "email": "user@example.com", "name": "John Doe"}
            result = task_service.dispatch_user_registration(user_data)

            assert result["task_id"] == "user-789"
            assert result["status"] == "dispatched"
            mock_register.delay.assert_called_once_with(user_data)

    def test_get_task_status_pending(self, task_service, mock_celery_app):
        """Test getting status of pending task."""
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_result.ready.return_value = False
        mock_result.result = None

        with patch("src.api.services.task_service.AsyncResult", return_value=mock_result):
            status = task_service.get_task_status("task-123")

            assert status["task_id"] == "task-123"
            assert status["state"] == "PENDING"
            assert status["result"] is None
            assert status["ready"] is False
            assert status["successful"] is None

    def test_get_task_status_success(self, task_service, mock_celery_app):
        """Test getting status of successfully completed task."""
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = True
        mock_result.result = {"status": "completed", "count": 10}

        with patch("src.api.services.task_service.AsyncResult", return_value=mock_result):
            status = task_service.get_task_status("task-456")

            assert status["task_id"] == "task-456"
            assert status["state"] == "SUCCESS"
            assert status["result"] == {"status": "completed", "count": 10}
            assert status["ready"] is True
            assert status["successful"] is True

    def test_get_task_status_failure(self, task_service, mock_celery_app):
        """Test getting status of failed task."""
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.ready.return_value = True
        mock_result.successful.return_value = False
        mock_result.result = Exception("Task failed")

        with patch("src.api.services.task_service.AsyncResult", return_value=mock_result):
            status = task_service.get_task_status("task-789")

            assert status["task_id"] == "task-789"
            assert status["state"] == "FAILURE"
            assert status["ready"] is True
            assert status["successful"] is False

    def test_get_task_service(self, mock_celery_app):
        """Test get_task_service dependency injection function."""
        with patch("src.api.services.task_service.get_celery_app", return_value=mock_celery_app):
            service = get_task_service()

            assert isinstance(service, TaskService)
            assert service.celery_app == mock_celery_app

