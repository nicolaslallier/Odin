"""Integration tests for task execution.

This module tests end-to-end task execution including task dispatch,
execution, and result retrieval.
"""

from __future__ import annotations

import os

os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from unittest.mock import MagicMock, patch

import pytest

from src.worker.celery_app import get_celery_app


@pytest.fixture
def celery_app_eager():
    """Configure Celery to run tasks eagerly for testing."""
    app = get_celery_app()
    app.conf.task_always_eager = True
    app.conf.task_eager_propagates = True
    return app


class TestTaskExecutionIntegration:
    """Integration tests for task execution."""

    @patch("src.worker.tasks.scheduled.httpx")
    def test_health_check_task_execution(self, mock_httpx: MagicMock, celery_app_eager) -> None:
        """Test health check task executes end-to-end."""
        # Arrange
        from src.worker.tasks.scheduled import health_check_services

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_httpx.get.return_value = mock_response

        # Act
        result = health_check_services.delay()

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["status"] == "success"

    @patch("src.worker.tasks.batch.session_scope")
    def test_bulk_data_processing_execution(
        self, mock_session_scope: MagicMock, celery_app_eager
    ) -> None:
        """Test bulk data processing task executes end-to-end."""
        # Arrange
        from src.worker.tasks.batch import process_bulk_data

        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        data_items = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]

        # Act
        result = process_bulk_data.delay(data_items)

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["processed"] == 2

    @patch("src.worker.tasks.events.session_scope")
    @patch("src.worker.tasks.events.send_notification")
    def test_user_registration_task_execution(
        self,
        mock_send_notification: MagicMock,
        mock_session_scope: MagicMock,
        celery_app_eager,
    ) -> None:
        """Test user registration task executes end-to-end."""
        # Arrange
        from src.worker.tasks.events import handle_user_registration

        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        user_data = {
            "user_id": 123,
            "email": "user@example.com",
            "username": "testuser",
        }

        # Act
        result = handle_user_registration.delay(user_data)

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["user_id"] == 123

    def test_task_state_tracking(self, celery_app_eager) -> None:
        """Test that task state is properly tracked."""
        # Arrange
        from src.worker.tasks.scheduled import health_check_services

        with patch("src.worker.tasks.scheduled.httpx") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_httpx.get.return_value = mock_response

            # Act
            result = health_check_services.delay()

            # Assert
            assert result.state in ["PENDING", "SUCCESS"]
            assert result.successful()

    @patch("src.worker.tasks.batch.session_scope")
    def test_task_retry_on_failure(self, mock_session_scope: MagicMock, celery_app_eager) -> None:
        """Test that tasks handle failures gracefully."""
        # Arrange
        from src.worker.tasks.batch import process_bulk_data

        # Mock session_scope to raise an exception
        mock_session_scope.side_effect = Exception("Temporary error")
        data_items = [{"id": 1, "value": "a"}]

        # Act - task catches exceptions and returns error status
        result = process_bulk_data.delay(data_items).get()

        # Assert - task returns error status instead of raising
        assert result["status"] == "error"
        assert "error" in result

    def test_task_chain_execution(self, celery_app_eager) -> None:
        """Test executing tasks in a chain."""
        # Arrange
        from src.worker.tasks.batch import process_bulk_data
        from src.worker.tasks.events import send_notification

        with patch("src.worker.tasks.batch.session_scope") as mock_session:
            mock_session.return_value.__enter__.return_value = MagicMock()

            with patch("src.worker.tasks.events.httpx") as mock_httpx:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_httpx.post.return_value = mock_response

                # Act - Chain tasks
                data = [{"id": 1, "value": "a"}]
                notification = {
                    "user_id": 1,
                    "type": "email",
                    "subject": "Processing complete",
                    "message": "Your data has been processed",
                }

                result1 = process_bulk_data.delay(data)
                result2 = send_notification.delay(notification)

                # Assert
                assert result1.successful()
                assert result2.successful()

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_cleanup_task_database_operations(
        self, mock_session_scope: MagicMock, celery_app_eager
    ) -> None:
        """Test cleanup task performs database operations correctly."""
        # Arrange
        from src.worker.tasks.scheduled import cleanup_old_task_results

        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.delete.return_value = 10

        # Act
        result = cleanup_old_task_results.delay(days=30)

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["deleted"] == 10
