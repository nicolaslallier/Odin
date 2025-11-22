"""Unit tests for worker configuration module.

This module tests the WorkerConfig class and its validation logic,
ensuring proper configuration management following SOLID principles.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.worker.config import WorkerConfig, get_config


class TestWorkerConfig:
    """Test suite for WorkerConfig class."""

    def test_config_with_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that configuration can be created with required environment variables."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )

        # Act
        config = WorkerConfig()

        # Assert
        assert config.broker_url == "amqp://guest:guest@localhost:5672//"
        assert config.result_backend == "db+postgresql://user:pass@localhost:5432/db"
        assert config.task_track_started is True
        assert config.task_time_limit == 3600
        assert config.worker_concurrency == 4
        assert config.worker_max_tasks_per_child == 1000

    def test_config_with_custom_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that configuration respects custom environment variables."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://odin:pass@rabbitmq:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://odin:pass@postgresql:5432/odin_db"
        )
        monkeypatch.setenv("CELERY_TASK_TRACK_STARTED", "false")
        monkeypatch.setenv("CELERY_TASK_TIME_LIMIT", "7200")
        monkeypatch.setenv("CELERY_WORKER_CONCURRENCY", "8")
        monkeypatch.setenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "2000")

        # Act
        config = WorkerConfig()

        # Assert
        assert config.broker_url == "amqp://odin:pass@rabbitmq:5672//"
        assert config.result_backend == "db+postgresql://odin:pass@postgresql:5432/odin_db"
        assert config.task_track_started is False
        assert config.task_time_limit == 7200
        assert config.worker_concurrency == 8
        assert config.worker_max_tasks_per_child == 2000

    def test_config_missing_broker_url_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing broker URL raises validation error."""
        # Arrange
        monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkerConfig()

        assert "CELERY_BROKER_URL" in str(exc_info.value)

    def test_config_missing_result_backend_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that missing result backend raises validation error."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkerConfig()

        assert "CELERY_RESULT_BACKEND" in str(exc_info.value)

    def test_config_is_immutable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that configuration is frozen and cannot be modified."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )
        config = WorkerConfig()

        # Act & Assert
        with pytest.raises(ValidationError):
            config.broker_url = "amqp://new:url@localhost:5672//"  # type: ignore

    def test_config_validates_time_limit_positive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that task time limit must be positive."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )
        monkeypatch.setenv("CELERY_TASK_TIME_LIMIT", "-100")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkerConfig()

        assert "greater than 0" in str(exc_info.value).lower()

    def test_config_validates_concurrency_positive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that worker concurrency must be positive."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )
        monkeypatch.setenv("CELERY_WORKER_CONCURRENCY", "0")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkerConfig()

        assert "greater than 0" in str(exc_info.value).lower()

    def test_config_validates_max_tasks_positive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that max tasks per child must be positive."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )
        monkeypatch.setenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "-1")

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkerConfig()

        assert "greater than 0" in str(exc_info.value).lower()


class TestGetConfig:
    """Test suite for get_config function."""

    def test_get_config_returns_worker_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_config returns a WorkerConfig instance."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )

        # Act
        config = get_config()

        # Assert
        assert isinstance(config, WorkerConfig)
        assert config.broker_url == "amqp://guest:guest@localhost:5672//"

    def test_get_config_creates_new_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that get_config creates a new instance each time."""
        # Arrange
        monkeypatch.setenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
        monkeypatch.setenv(
            "CELERY_RESULT_BACKEND", "db+postgresql://user:pass@localhost:5432/db"
        )

        # Act
        config1 = get_config()
        config2 = get_config()

        # Assert - configs are equal but not the same instance
        assert config1 == config2
        assert config1 is not config2

