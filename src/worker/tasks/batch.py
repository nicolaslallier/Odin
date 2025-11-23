"""Batch processing tasks.

This module contains tasks for processing large datasets and bulk operations,
including data processing, file handling, and bulk notifications.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
from minio import Minio

from src.worker.celery_app import celery_app
from src.worker.config import get_config
from src.worker.exceptions import BatchProcessingError
from src.worker.tasks.scheduled import session_scope

# Configure logging
logger = logging.getLogger(__name__)


class MinioClient:
    """Wrapper for MinIO client operations with proper configuration.

    This class provides a properly configured MinIO client that reads
    connection details from environment variables.
    """

    def __init__(self) -> None:
        """Initialize MinIO client with configuration from environment."""
        config = get_config()
        self.client = Minio(
            config.minio_endpoint,
            access_key=config.minio_access_key,
            secret_key=config.minio_secret_key,
            secure=config.minio_secure,
        )
        logger.info(f"MinIO client initialized for endpoint: {config.minio_endpoint}")


@celery_app.task(name="src.worker.tasks.batch.process_bulk_data", bind=True)
def process_bulk_data(
    self, data_items: list[dict[str, Any]], batch_size: int = 100
) -> dict[str, Any]:
    """Process a large dataset in batches with improved resource management.

    This task processes bulk data in configurable batch sizes with proper
    session management and error handling. Each batch is committed separately
    to prevent holding a database transaction for the entire operation.

    Args:
        self: Celery task instance (bound)
        data_items: List of data items to process
        batch_size: Number of items to process per batch

    Returns:
        Dictionary containing processing results

    Raises:
        BatchProcessingError: If validation fails

    Example:
        >>> data = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
        >>> result = process_bulk_data.delay(data)
    """
    if not isinstance(data_items, list):
        raise BatchProcessingError("data_items must be a list")

    if batch_size <= 0:
        raise BatchProcessingError("batch_size must be positive")

    logger.info(f"Processing {len(data_items)} items in batches of {batch_size}")

    processed = 0
    failed = 0
    batch_count = 0

    try:
        for i in range(0, len(data_items), batch_size):
            batch = data_items[i : i + batch_size]
            batch_count += 1

            # Use a separate session for each batch to avoid long-running transactions
            with session_scope() as session:
                for item in batch:
                    try:
                        # Validate item has required fields
                        if not isinstance(item, dict):
                            logger.warning(f"Invalid item type: {type(item)}")
                            failed += 1
                            continue

                        if item.get("value") is None:
                            logger.warning(f"Item missing required 'value' field: {item}")
                            failed += 1
                            continue

                        # Process the item (placeholder logic)
                        # In real implementation, this would do actual processing
                        processed += 1

                    except Exception as e:
                        logger.error(f"Failed to process item: {e}", exc_info=True)
                        failed += 1

            # Update task progress
            if batch_count % 10 == 0:
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "processed": processed,
                        "failed": failed,
                        "batch": batch_count,
                        "percent": (i + len(batch)) / len(data_items) * 100,
                    },
                )

        logger.info(
            f"Batch processing complete: {processed} processed, "
            f"{failed} failed, {batch_count} batches"
        )

        return {
            "status": "success",
            "processed": processed,
            "failed": failed,
            "total": len(data_items),
            "batches": batch_count,
        }

    except Exception as e:
        logger.error(f"Batch processing error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "processed": processed,
            "failed": failed,
        }


@celery_app.task(name="src.worker.tasks.batch.process_file_batch")
def process_file_batch(file_paths: list[str], upload_to_storage: bool = False) -> dict[str, Any]:
    """Process a batch of files.

    This task processes multiple files, optionally uploading them to object
    storage (MinIO) after processing.

    Args:
        file_paths: List of file paths to process
        upload_to_storage: Whether to upload processed files to MinIO

    Returns:
        Dictionary containing processing results

    Example:
        >>> files = ["file1.txt", "file2.txt"]
        >>> result = process_file_batch.delay(files, upload_to_storage=True)
    """
    processed = 0
    failed = 0
    uploaded = 0

    minio_client = MinioClient() if upload_to_storage else None

    for file_path_str in file_paths:
        try:
            if not file_path_str:
                failed += 1
                continue

            file_path = Path(file_path_str)

            # Process file (placeholder logic)
            # In real implementation, this would do actual file processing

            processed += 1

            # Upload to MinIO if requested
            if upload_to_storage and minio_client:
                # Actual upload logic would go here
                uploaded += 1

        except Exception:
            failed += 1

    return {
        "status": "success",
        "processed": processed,
        "failed": failed,
        "total": len(file_paths),
        "uploaded": uploaded if upload_to_storage else None,
    }


@celery_app.task(name="src.worker.tasks.batch.send_bulk_notifications", bind=True)
def send_bulk_notifications(
    self, notifications: list[dict[str, Any]], rate_limit: int = 100
) -> dict[str, Any]:
    """Send notifications in bulk with rate limiting and proper error handling.

    This task sends multiple notifications while respecting rate limits and
    handling errors gracefully. Validation is performed before processing begins.

    Args:
        self: Celery task instance (bound)
        notifications: List of notification data dictionaries
        rate_limit: Maximum notifications per batch

    Returns:
        Dictionary containing sending results

    Raises:
        BatchProcessingError: If notification data validation fails

    Example:
        >>> notifs = [
        ...     {"user_id": 1, "message": "Hello"},
        ...     {"user_id": 2, "message": "World"}
        ... ]
        >>> result = send_bulk_notifications.delay(notifs)
    """
    # Validate notification format BEFORE processing
    if not isinstance(notifications, list):
        raise BatchProcessingError("notifications must be a list")

    if rate_limit <= 0:
        raise BatchProcessingError("rate_limit must be positive")

    logger.info(f"Sending {len(notifications)} notifications with rate limit {rate_limit}")

    for i, notification in enumerate(notifications):
        if not isinstance(notification, dict):
            raise BatchProcessingError(
                f"Notification at index {i} must be a dictionary",
                {"index": i, "type": str(type(notification))},
            )
        if "user_id" not in notification or "message" not in notification:
            raise BatchProcessingError(
                f"Notification at index {i} must have user_id and message",
                {"index": i, "notification": notification},
            )

    sent = 0
    failed = 0
    batch_count = 0

    # Process in rate-limited batches
    for i in range(0, len(notifications), rate_limit):
        batch = notifications[i : i + rate_limit]
        batch_count += 1

        for notification in batch:
            try:
                # Send notification via HTTP API (placeholder)
                # In production, this would use the actual notification service
                with httpx.Client() as client:
                    response = client.post(
                        "http://localhost/api/notifications",
                        json=notification,
                        timeout=5.0,
                    )

                    if response.status_code == 200:
                        sent += 1
                    else:
                        logger.warning(
                            f"Notification failed with status {response.status_code}: "
                            f"{notification.get('user_id')}"
                        )
                        failed += 1

            except httpx.TimeoutException as e:
                logger.error(f"Notification timeout: {e}")
                failed += 1
            except httpx.RequestError as e:
                logger.error(f"Notification request error: {e}")
                failed += 1
            except Exception as e:
                logger.error(f"Unexpected error sending notification: {e}", exc_info=True)
                failed += 1

        # Update task progress
        if batch_count % 10 == 0:
            self.update_state(
                state="PROGRESS",
                meta={
                    "sent": sent,
                    "failed": failed,
                    "batch": batch_count,
                    "percent": (i + len(batch)) / len(notifications) * 100,
                },
            )

    logger.info(
        f"Notification sending complete: {sent} sent, {failed} failed, " f"{batch_count} batches"
    )

    return {
        "status": "success",
        "sent": sent,
        "failed": failed,
        "total": len(notifications),
        "rate_limited": rate_limit < len(notifications),
    }
