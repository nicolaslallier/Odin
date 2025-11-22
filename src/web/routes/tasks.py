"""Task management routes for web interface.

This module provides routes for dispatching and monitoring background tasks
from the web interface.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.api.services.task_service import get_task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskDispatchResponse(BaseModel):
    """Response model for task dispatch."""

    task_id: str = Field(..., description="The ID of the dispatched task")
    status: str = Field(..., description="Current status of the task")


class TaskStatusResponse(BaseModel):
    """Response model for task status."""

    task_id: str = Field(..., description="The ID of the task")
    state: str = Field(..., description="Current state of the task")
    result: Any = Field(None, description="Task result if ready")
    ready: bool = Field(..., description="Whether the task is ready")
    successful: bool | None = Field(None, description="Whether the task succeeded")


@router.post("/process-data", response_model=TaskDispatchResponse)
async def dispatch_data_processing(
    data_items: list[dict[str, Any]]
) -> TaskDispatchResponse:
    """Dispatch a bulk data processing task.

    Args:
        data_items: List of data items to process

    Returns:
        Task dispatch response with task ID

    Example:
        POST /tasks/process-data
        Body: [{"id": 1, "value": "data"}]
    """
    service = get_task_service()
    result = service.dispatch_bulk_data_processing(data_items)
    return TaskDispatchResponse(**result)


@router.post("/send-notification", response_model=TaskDispatchResponse)
async def dispatch_notification(
    notification_data: dict[str, Any]
) -> TaskDispatchResponse:
    """Dispatch a notification task.

    Args:
        notification_data: Notification details

    Returns:
        Task dispatch response with task ID

    Example:
        POST /tasks/send-notification
        Body: {"user_id": 123, "type": "email", "message": "Hello"}
    """
    service = get_task_service()
    result = service.dispatch_notification(notification_data)
    return TaskDispatchResponse(**result)


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a background task.

    Args:
        task_id: The task ID to check

    Returns:
        Task status response

    Raises:
        HTTPException: If task not found

    Example:
        GET /tasks/abc-123-def-456
    """
    service = get_task_service()
    try:
        status = service.get_task_status(task_id)
        return TaskStatusResponse(**status)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {str(e)}")

