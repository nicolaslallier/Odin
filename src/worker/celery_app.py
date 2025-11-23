"""Celery application factory.

This module provides the factory function for creating and configuring
a Celery application instance following the Factory pattern and SOLID principles.
"""

from __future__ import annotations

from celery import Celery

from src.worker.config import get_config

# Global Celery app instance (singleton pattern)
_celery_app: Celery | None = None


def create_celery_app() -> Celery:
    """Create and configure a Celery application instance.

    This factory function creates a new Celery application with all necessary
    configuration including broker, result backend, serialization, and task
    discovery. It follows the Factory pattern and ensures proper separation
    of concerns.

    Returns:
        Configured Celery application instance

    Example:
        >>> app = create_celery_app()
        >>> # Use the app to define or execute tasks
    """
    config = get_config()

    # Configure logging with database support

    from src.worker.logging_config import configure_worker_logging

    # Extract PostgreSQL DSN from result_backend (convert from db+postgresql to postgresql+asyncpg)
    db_dsn = None
    if config.result_backend.startswith("db+postgresql://"):
        db_dsn = config.result_backend.replace("db+postgresql://", "postgresql+asyncpg://")

    configure_worker_logging(
        level="INFO",
        use_json=True,
        db_dsn=db_dsn,
    )

    # Create Celery application
    app = Celery("odin")

    # Configure Celery from settings
    app.config_from_object(
        {
            # Broker and result backend
            "broker_url": config.broker_url,
            "result_backend": config.result_backend,
            # Serialization
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            # Timezone
            "timezone": "UTC",
            "enable_utc": True,
            # Task tracking
            "task_track_started": config.task_track_started,
            "task_time_limit": config.task_time_limit,
            # Worker settings
            "worker_prefetch_multiplier": 1,
            "worker_max_tasks_per_child": config.worker_max_tasks_per_child,
            # Result backend settings
            "result_extended": True,
            "result_expires": 86400,  # 24 hours
        }
    )

    # Auto-discover tasks from the tasks module
    app.autodiscover_tasks(["src.worker.tasks"])

    # Import and configure beat schedule
    from src.worker.beat_schedule import get_beat_schedule

    app.conf.beat_schedule = get_beat_schedule()

    return app


def get_celery_app() -> Celery:
    """Get the Celery application instance (singleton).

    This function returns the global Celery application instance, creating it
    if it doesn't exist. This implements the Singleton pattern to ensure only
    one Celery application instance exists.

    Returns:
        The global Celery application instance

    Example:
        >>> app = get_celery_app()
        >>> @app.task
        >>> def my_task():
        >>>     pass
    """
    global _celery_app
    if _celery_app is None:
        _celery_app = create_celery_app()
    return _celery_app


# Create the global celery app instance for use in CLI commands
celery_app = get_celery_app()
