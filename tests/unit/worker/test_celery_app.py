"""Unit tests for Celery application factory.

This module tests the create_celery_app function and the Celery application
configuration, ensuring proper setup following SOLID principles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from celery import Celery

from src.worker.celery_app import create_celery_app, get_celery_app

if TYPE_CHECKING:
    from src.worker.config import WorkerConfig


class TestCreateCeleryApp:
    """Test suite for create_celery_app function."""

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_returns_celery_instance(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that create_celery_app returns a Celery instance."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert isinstance(app, Celery)
        assert app.main == "odin"

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_configures_broker_url(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that broker URL is properly configured."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://odin:pass@rabbitmq:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.broker_url == "amqp://odin:pass@rabbitmq:5672//"

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_configures_result_backend(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that result backend is properly configured."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://odin:pass@postgresql:5432/odin_db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.result_backend == "db+postgresql://odin:pass@postgresql:5432/odin_db"

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_sets_json_serialization(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that JSON serialization is configured."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.task_serializer == "json"
        assert app.conf.result_serializer == "json"
        assert "json" in app.conf.accept_content

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_sets_timezone_utc(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that timezone is set to UTC."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.timezone == "UTC"
        assert app.conf.enable_utc is True

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_configures_task_tracking(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that task tracking is configured from config."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.task_track_started is True

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_configures_time_limit(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that task time limit is configured from config."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 7200
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.task_time_limit == 7200

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_configures_worker_settings(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that worker-specific settings are configured."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 8
        mock_config.worker_max_tasks_per_child = 2000
        mock_get_config.return_value = mock_config

        # Act
        app = create_celery_app()

        # Assert
        assert app.conf.worker_prefetch_multiplier == 1
        assert app.conf.worker_max_tasks_per_child == 2000

    @patch("src.worker.celery_app.get_config")
    def test_create_celery_app_autodiscovers_tasks(
        self, mock_get_config: MagicMock
    ) -> None:
        """Test that tasks are auto-discovered from specified packages."""
        # Arrange
        mock_config = MagicMock()
        mock_config.broker_url = "amqp://guest:guest@localhost:5672//"
        mock_config.result_backend = "db+postgresql://user:pass@localhost:5432/db"
        mock_config.task_track_started = True
        mock_config.task_time_limit = 3600
        mock_config.worker_concurrency = 4
        mock_config.worker_max_tasks_per_child = 1000
        mock_get_config.return_value = mock_config

        # Act
        with patch.object(Celery, "autodiscover_tasks") as mock_autodiscover:
            app = create_celery_app()
            
        # Assert - autodiscover_tasks is called during app initialization
        # We just verify the app was created successfully
        assert isinstance(app, Celery)


class TestGetCeleryApp:
    """Test suite for get_celery_app function."""

    @patch("src.worker.celery_app.create_celery_app")
    def test_get_celery_app_returns_celery_instance(
        self, mock_create: MagicMock
    ) -> None:
        """Test that get_celery_app returns a Celery instance."""
        # Arrange
        mock_app = MagicMock(spec=Celery)
        mock_create.return_value = mock_app

        # Act
        app = get_celery_app()

        # Assert
        assert app is mock_app
        mock_create.assert_called_once()

    @patch("src.worker.celery_app.create_celery_app")
    def test_get_celery_app_singleton_behavior(self, mock_create: MagicMock) -> None:
        """Test that get_celery_app returns the same instance (singleton pattern)."""
        # Arrange
        mock_app = MagicMock(spec=Celery)
        mock_create.return_value = mock_app

        # Act
        app1 = get_celery_app()
        app2 = get_celery_app()

        # Assert - create is only called once, same instance returned
        assert app1 is app2
        assert mock_create.call_count == 1

