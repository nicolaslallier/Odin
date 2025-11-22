"""Message queue routes for API service.

This module provides endpoints for RabbitMQ message operations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.config import APIConfig, get_config
from src.api.models.schemas import MessageRequest, MessageResponse
from src.api.services.queue import QueueService

router = APIRouter(prefix="/messages", tags=["messages"])


def get_queue_service(config: APIConfig = Depends(get_config)) -> QueueService:
    """Dependency to get queue service instance.

    Args:
        config: API configuration

    Returns:
        Queue service instance
    """
    return QueueService(url=config.rabbitmq_url)


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
    """
    try:
        queue.declare_queue(request.queue)
        queue.publish_message(request.queue, request.message)
        return {"message": f"Message sent to {request.queue}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    """
    try:
        message = queue.consume_message(queue_name)
        return MessageResponse(queue=queue_name, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

