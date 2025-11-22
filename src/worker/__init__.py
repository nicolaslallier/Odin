"""Worker module for background task processing.

This module provides Celery-based background task processing capabilities
including scheduled tasks, batch processing, and event-driven tasks.
"""

from src.worker.celery_app import get_celery_app

__all__ = ["get_celery_app"]

