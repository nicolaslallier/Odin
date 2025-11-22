"""Worker configuration management.

This module provides configuration management for the Celery worker service,
loading settings from environment variables and validating them using Pydantic.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    """Configuration for the Celery worker service.

    This class loads configuration from environment variables and provides
    type-safe access to all worker settings including broker and result backend.

    Attributes:
        broker_url: The message broker URL (RabbitMQ)
        result_backend: The result backend URL (PostgreSQL)
        task_track_started: Whether to track when tasks start
        task_time_limit: Maximum execution time for tasks in seconds
        worker_concurrency: Number of concurrent worker processes
        worker_max_tasks_per_child: Maximum tasks per worker before restart
        minio_endpoint: MinIO server endpoint
        minio_access_key: MinIO access key
        minio_secret_key: MinIO secret key
        minio_secure: Whether to use HTTPS for MinIO connection
    """

    # Broker and Backend Settings
    broker_url: str = Field(alias="CELERY_BROKER_URL")
    result_backend: str = Field(alias="CELERY_RESULT_BACKEND")

    # Task Settings
    task_track_started: bool = Field(default=True, alias="CELERY_TASK_TRACK_STARTED")
    task_time_limit: int = Field(default=3600, alias="CELERY_TASK_TIME_LIMIT")

    # Worker Settings
    worker_concurrency: int = Field(default=4, alias="CELERY_WORKER_CONCURRENCY")
    worker_max_tasks_per_child: int = Field(
        default=1000, alias="CELERY_WORKER_MAX_TASKS_PER_CHILD"
    )

    # MinIO Settings (for batch tasks)
    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        frozen=True,
        extra="ignore",
    )

    @field_validator("task_time_limit")
    @classmethod
    def validate_task_time_limit(cls, v: int) -> int:
        """Validate that task time limit is positive.

        Args:
            v: The task time limit value

        Returns:
            The validated task time limit

        Raises:
            ValueError: If task time limit is not positive
        """
        if v <= 0:
            raise ValueError("task_time_limit must be greater than 0")
        return v

    @field_validator("worker_concurrency")
    @classmethod
    def validate_worker_concurrency(cls, v: int) -> int:
        """Validate that worker concurrency is positive.

        Args:
            v: The worker concurrency value

        Returns:
            The validated worker concurrency

        Raises:
            ValueError: If worker concurrency is not positive
        """
        if v <= 0:
            raise ValueError("worker_concurrency must be greater than 0")
        return v

    @field_validator("worker_max_tasks_per_child")
    @classmethod
    def validate_worker_max_tasks(cls, v: int) -> int:
        """Validate that max tasks per child is positive.

        Args:
            v: The max tasks per child value

        Returns:
            The validated max tasks per child

        Raises:
            ValueError: If max tasks per child is not positive
        """
        if v <= 0:
            raise ValueError("worker_max_tasks_per_child must be greater than 0")
        return v


def get_config() -> WorkerConfig:
    """Get the worker configuration.

    This function creates and returns a WorkerConfig instance loaded from
    environment variables. It can be used as a dependency injection point.

    Returns:
        Configured WorkerConfig instance

    Example:
        >>> config = get_config()
        >>> print(f"Broker: {config.broker_url}")
    """
    return WorkerConfig()

