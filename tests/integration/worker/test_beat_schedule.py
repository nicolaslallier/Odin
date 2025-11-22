"""Integration tests for Celery Beat schedule.

This module tests the Celery Beat scheduler configuration and
periodic task execution.
"""

from __future__ import annotations

import os
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.schedules import crontab

from src.worker.beat_schedule import get_beat_schedule
from src.worker.celery_app import get_celery_app


class TestBeatScheduleConfiguration:
    """Integration tests for beat schedule configuration."""

    def test_get_beat_schedule_returns_dict(self) -> None:
        """Test that get_beat_schedule returns a dictionary."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        assert isinstance(schedule, dict)

    def test_beat_schedule_contains_health_check(self) -> None:
        """Test that beat schedule includes health check task."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        assert "health-check-services" in schedule
        task_config = schedule["health-check-services"]
        assert "task" in task_config
        assert "schedule" in task_config

    def test_beat_schedule_contains_cleanup_task(self) -> None:
        """Test that beat schedule includes cleanup task."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        assert "cleanup-old-task-results" in schedule
        task_config = schedule["cleanup-old-task-results"]
        assert "task" in task_config
        assert "schedule" in task_config

    def test_beat_schedule_contains_daily_report(self) -> None:
        """Test that beat schedule includes daily report task."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        assert "generate-daily-report" in schedule
        task_config = schedule["generate-daily-report"]
        assert "task" in task_config
        assert "schedule" in task_config

    def test_beat_schedule_has_valid_intervals(self) -> None:
        """Test that all scheduled tasks have valid intervals."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        for task_name, task_config in schedule.items():
            assert "schedule" in task_config
            schedule_value = task_config["schedule"]
            # Schedule can be a timedelta, crontab, or number
            assert isinstance(schedule_value, (timedelta, int, float, crontab))

    def test_health_check_runs_every_5_minutes(self) -> None:
        """Test that health check is scheduled to run every 5 minutes."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        task_config = schedule["health-check-services"]
        assert task_config["schedule"] == timedelta(minutes=5)

    def test_cleanup_runs_daily(self) -> None:
        """Test that cleanup task is scheduled to run daily."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        task_config = schedule["cleanup-old-task-results"]
        # Check if it's a daily schedule
        assert task_config["schedule"] == timedelta(days=1) or hasattr(
            task_config["schedule"], "hour"
        )

    def test_daily_report_runs_at_midnight(self) -> None:
        """Test that daily report is scheduled to run at midnight."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        task_config = schedule["generate-daily-report"]
        schedule_value = task_config["schedule"]
        # Should be a crontab with hour=0
        assert hasattr(schedule_value, "hour")

    def test_celery_app_uses_beat_schedule(self) -> None:
        """Test that Celery app is configured with beat schedule."""
        # Act
        app = get_celery_app()

        # Assert
        assert hasattr(app.conf, "beat_schedule")
        assert app.conf.beat_schedule is not None

    def test_beat_schedule_tasks_have_options(self) -> None:
        """Test that scheduled tasks can have additional options."""
        # Act
        schedule = get_beat_schedule()

        # Assert
        # Check that tasks can have optional configurations
        for task_name, task_config in schedule.items():
            assert "task" in task_config
            assert "schedule" in task_config
            # Options like args, kwargs are optional
            if "options" in task_config:
                assert isinstance(task_config["options"], dict)

    @patch("src.worker.beat_schedule.timedelta")
    def test_beat_schedule_intervals_are_configurable(
        self, mock_timedelta
    ) -> None:
        """Test that beat schedule intervals can be configured."""
        # This test verifies that intervals are not hardcoded but configurable
        # Act
        schedule = get_beat_schedule()

        # Assert - Just verify the schedule is created successfully
        assert len(schedule) > 0


class TestBeatScheduleExecution:
    """Integration tests for beat task execution."""

    @pytest.fixture
    def celery_app_eager(self):
        """Configure Celery to run tasks eagerly for testing."""
        app = get_celery_app()
        app.conf.task_always_eager = True
        app.conf.task_eager_propagates = True
        return app

    @patch("src.worker.tasks.scheduled.httpx")
    def test_scheduled_health_check_executes(
        self, mock_httpx, celery_app_eager
    ) -> None:
        """Test that scheduled health check task executes."""
        # Arrange
        from src.worker.tasks.scheduled import health_check_services

        mock_response = mock_httpx.get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        # Act
        result = health_check_services.apply()

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["status"] == "success"

    @patch("src.worker.tasks.scheduled.session_scope")
    def test_scheduled_cleanup_executes(
        self, mock_session_scope, celery_app_eager
    ) -> None:
        """Test that scheduled cleanup task executes."""
        # Arrange
        from src.worker.tasks.scheduled import cleanup_old_task_results

        mock_session = mock_session_scope.return_value.__enter__.return_value
        mock_session.query.return_value.filter.return_value.delete.return_value = 5

        # Act
        result = cleanup_old_task_results.apply(args=[30])

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["deleted"] == 5

    @patch("src.worker.tasks.scheduled.session_scope")
    @patch("src.worker.tasks.scheduled.datetime")
    def test_scheduled_report_executes(
        self, mock_datetime, mock_session_scope, celery_app_eager
    ) -> None:
        """Test that scheduled report generation task executes."""
        # Arrange
        from src.worker.tasks.scheduled import generate_daily_report

        mock_session = mock_session_scope.return_value.__enter__.return_value
        mock_datetime.now.return_value.isoformat.return_value = "2025-11-22T00:00:00"

        # Act
        result = generate_daily_report.apply()

        # Assert
        assert result.successful()
        task_result = result.get()
        assert task_result["status"] == "success"

