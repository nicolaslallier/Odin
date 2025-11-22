"""Task service for dispatching background tasks.

This module provides a service layer for dispatching Celery tasks from the API,
following the Single Responsibility Principle (SRP) from SOLID.
"""

from __future__ import annotations

from typing import Any

from celery.result import AsyncResult

from src.worker.celery_app import get_celery_app


class TaskService:
    """Service for managing background task dispatch and monitoring.

    This class provides methods for dispatching various types of background
    tasks and checking their status, following the Service pattern.
    """

    def __init__(self) -> None:
        """Initialize the task service with Celery app."""
        self.celery_app = get_celery_app()

    def dispatch_bulk_data_processing(
        self, data_items: list[dict[str, Any]]
    ) -> dict[str, str]:
        """Dispatch a bulk data processing task.

        Args:
            data_items: List of data items to process

        Returns:
            Dictionary containing task ID and status

        Example:
            >>> service = TaskService()
            >>> result = service.dispatch_bulk_data_processing([{"id": 1}])
            >>> print(result["task_id"])
        """
        from src.worker.tasks.batch import process_bulk_data

        task = process_bulk_data.delay(data_items)
        return {"task_id": task.id, "status": "dispatched"}

    def dispatch_notification(
        self, notification_data: dict[str, Any]
    ) -> dict[str, str]:
        """Dispatch a notification task.

        Args:
            notification_data: Notification details

        Returns:
            Dictionary containing task ID and status

        Example:
            >>> service = TaskService()
            >>> notif = {"user_id": 123, "type": "email", "message": "Hello"}
            >>> result = service.dispatch_notification(notif)
        """
        from src.worker.tasks.events import send_notification

        task = send_notification.delay(notification_data)
        return {"task_id": task.id, "status": "dispatched"}

    def dispatch_user_registration(self, user_data: dict[str, Any]) -> dict[str, str]:
        """Dispatch a user registration processing task.

        Args:
            user_data: User registration data

        Returns:
            Dictionary containing task ID and status

        Example:
            >>> service = TaskService()
            >>> user = {"user_id": 123, "email": "user@example.com"}
            >>> result = service.dispatch_user_registration(user)
        """
        from src.worker.tasks.events import handle_user_registration

        task = handle_user_registration.delay(user_data)
        return {"task_id": task.id, "status": "dispatched"}

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Get the status of a background task.

        Args:
            task_id: The task ID to check

        Returns:
            Dictionary containing task status and result

        Example:
            >>> service = TaskService()
            >>> status = service.get_task_status("task-123")
            >>> print(status["state"])
        """
        task_result = AsyncResult(task_id, app=self.celery_app)
        return {
            "task_id": task_id,
            "state": task_result.state,
            "result": task_result.result if task_result.ready() else None,
            "ready": task_result.ready(),
            "successful": task_result.successful() if task_result.ready() else None,
        }


def get_task_service() -> TaskService:
    """Get a TaskService instance.

    This function can be used as a dependency injection point.

    Returns:
        TaskService instance

    Example:
        >>> service = get_task_service()
        >>> service.dispatch_notification({...})
    """
    return TaskService()

