"""Message queue routes for API service.

This module provides endpoints for RabbitMQ message operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.exceptions import QueueError, ServiceUnavailableError
from src.api.models.schemas import MessageRequest, MessageResponse
from src.api.services.container import ServiceContainer
from src.api.services.queue import QueueService

router = APIRouter(prefix="/messages", tags=["messages"])


def get_container(request: Request) -> ServiceContainer:
    """Dependency to get service container from app state.

    Args:
        request: FastAPI request object

    Returns:
        Service container instance
    """
    return request.app.state.container


def get_queue_service(container: ServiceContainer = Depends(get_container)) -> QueueService:
    """Dependency to get queue service instance.

    Args:
        container: Service container

    Returns:
        Queue service instance
    """
    return container.queue


@router.post("/send")
async def send_message(
    request: MessageRequest,
    queue: QueueService = Depends(get_queue_service),
) -> dict[str, str]:
    """Send a message to a queue.

    Args:
        request: Message request with queue and content
        queue: Queue service instance

    Returns:
        Confirmation message

    Raises:
        HTTPException: If message send fails
    """
    try:
        queue.declare_queue(request.queue)
        queue.publish_message(request.queue, request.message)
        return {"message": f"Message sent to {request.queue}"}
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except QueueError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/receive", response_model=MessageResponse)
async def receive_message(
    queue_name: str,
    queue: QueueService = Depends(get_queue_service),
) -> MessageResponse:
    """Receive a message from a queue.

    Args:
        queue_name: Name of the queue
        queue: Queue service instance

    Returns:
        Message response with content or None if queue is empty

    Raises:
        HTTPException: If message receive fails
    """
    try:
        message = queue.consume_message(queue_name)
        return MessageResponse(queue=queue_name, message=message)
    except ServiceUnavailableError as e:
        raise HTTPException(status_code=503, detail=e.message)
    except QueueError as e:
        raise HTTPException(status_code=500, detail=e.message)
