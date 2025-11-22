"""Unit tests for scheduled tasks.

This module tests periodic/scheduled tasks that run on a schedule via Celery Beat.
"""

from __future__ import annotations

import os
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from unittest.mock import MagicMock, patch

import pytest

from src.worker.tasks.scheduled import (
    cleanup_old_task_results,
    health_check_services,
    generate_daily_report,
)


class TestHealthCheckServices:
    """Test suite for health_check_services task."""

    @patch("src.worker.tasks.scheduled.httpx")
    def test_health_check_all_services_healthy(self, mock_httpx: MagicMock) -> None:
        """Test health check when all services are healthy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_httpx.get.return_value = mock_response

        # Act
        result = health_check_services()

        # Assert
        assert result["status"] == "success"
        assert "checked" in result
        assert result["checked"] > 0

    @patch("src.worker.tasks.scheduled.httpx")
    def test_health_check_service_unavailable(self, mock_httpx: MagicMock) -> None:
        """Test health check when a service is unavailable."""
        # Arrange
        mock_httpx.get.side_effect = Exception("Connection refused")

        # Act
        result = health_check_services()

        # Assert
        assert result["status"] == "partial"
        assert "failures" in result
        assert result["failures"] > 0

    @patch("src.worker.tasks.scheduled.httpx")
    def test_health_check_returns_service_details(self, mock_httpx: MagicMock) -> None:
        """Test that health check returns details for each service."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_httpx.get.return_value = mock_response

        # Act
        result = health_check_services()

        # Assert
        assert "services" in result
        assert isinstance(result["services"], dict)


class TestCleanupOldTaskResults:
    """Test suite for cleanup_old_task_results task."""

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_cleanup_removes_old_results(self, mock_session_scope: MagicMock) -> None:
        """Test that cleanup removes task results older than retention period."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_query = MagicMock()
        mock_query.count.return_value = 50
        mock_session.query.return_value.filter.return_value.delete.return_value = 50

        # Act
        result = cleanup_old_task_results(days=30)

        # Assert
        assert result["deleted"] == 50
        assert result["days"] == 30

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_cleanup_with_custom_retention_period(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test cleanup with custom retention period."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.delete.return_value = 100

        # Act
        result = cleanup_old_task_results(days=7)

        # Assert
        assert result["deleted"] == 100
        assert result["days"] == 7

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_cleanup_handles_no_results_to_delete(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test cleanup when there are no old results to delete."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.delete.return_value = 0

        # Act
        result = cleanup_old_task_results(days=30)

        # Assert
        assert result["deleted"] == 0
        assert result["message"] == "No old task results to clean up"


class TestGenerateDailyReport:
    """Test suite for generate_daily_report task."""

    @patch("src.worker.tasks.scheduled.session_scope")
    @patch("src.worker.tasks.scheduled.datetime")
    def test_generate_report_creates_summary(
        self, mock_datetime: MagicMock, mock_session_scope: MagicMock
    ) -> None:
        """Test that daily report generates task summary."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        mock_datetime.now.return_value.isoformat.return_value = "2025-11-22T00:00:00"

        # Act
        result = generate_daily_report()

        # Assert
        assert result["status"] == "success"
        assert "date" in result
        assert "summary" in result

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_generate_report_counts_task_statuses(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test that report counts tasks by status."""
        # Arrange
        mock_session = MagicMock()
        mock_session_scope.return_value.__enter__.return_value = mock_session

        # Act
        result = generate_daily_report()

        # Assert
        assert "summary" in result
        summary = result["summary"]
        assert "total_tasks" in summary
        assert "successful_tasks" in summary
        assert "failed_tasks" in summary

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_generate_report_handles_database_error(
        self, mock_session_scope: MagicMock
    ) -> None:
        """Test that report generation handles database errors gracefully."""
        # Arrange
        mock_session_scope.side_effect = Exception("Database connection failed")

        # Act
        result = generate_daily_report()

        # Assert
        assert result["status"] == "error"
        assert "error" in result

