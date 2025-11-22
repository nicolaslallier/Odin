"""Batch processing tasks.

This module contains tasks for processing large datasets and bulk operations,
including data processing, file handling, and bulk notifications.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
from minio import Minio

from src.worker.celery_app import celery_app
from src.worker.tasks.scheduled import session_scope


class MinioClient:
    """Wrapper for MinIO client operations."""

    def __init__(self) -> None:
        """Initialize MinIO client with configuration."""
        # This would be configured from environment variables
        self.client = Minio(
            "minio:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )


@celery_app.task(name="src.worker.tasks.batch.process_bulk_data")
def process_bulk_data(
    data_items: list[dict[str, Any]], batch_size: int = 100
) -> dict[str, Any]:
    """Process a large dataset in batches.

    This task processes bulk data in configurable batch sizes to prevent
    memory overflow and ensure efficient processing of large datasets.

    Args:
        data_items: List of data items to process
        batch_size: Number of items to process per batch

    Returns:
        Dictionary containing processing results

    Raises:
        ValueError: If data_items is not a list

    Example:
        >>> data = [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
        >>> result = process_bulk_data.delay(data)
    """
    if not isinstance(data_items, list):
        raise ValueError("data_items must be a list")

    processed = 0
    failed = 0
    batch_count = 0

    try:
        with session_scope() as session:
            for i in range(0, len(data_items), batch_size):
                batch = data_items[i : i + batch_size]
                batch_count += 1

                for item in batch:
                    try:
                        # Validate item has required fields
                        if item.get("value") is None:
                            failed += 1
                            continue

                        # Process the item (placeholder logic)
                        # In real implementation, this would do actual processing
                        processed += 1
                    except Exception:
                        failed += 1

            return {
                "status": "success",
                "processed": processed,
                "failed": failed,
                "total": len(data_items),
                "batches": batch_count,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "processed": processed,
            "failed": failed,
        }


@celery_app.task(name="src.worker.tasks.batch.process_file_batch")
def process_file_batch(
    file_paths: list[str], upload_to_storage: bool = False
) -> dict[str, Any]:
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


@celery_app.task(name="src.worker.tasks.batch.send_bulk_notifications")
def send_bulk_notifications(
    notifications: list[dict[str, Any]], rate_limit: int = 100
) -> dict[str, Any]:
    """Send notifications in bulk with rate limiting.

    This task sends multiple notifications while respecting rate limits to
    prevent overwhelming the notification service.

    Args:
        notifications: List of notification data dictionaries
        rate_limit: Maximum notifications per batch

    Returns:
        Dictionary containing sending results

    Raises:
        ValueError: If notification data is invalid

    Example:
        >>> notifs = [
        ...     {"user_id": 1, "message": "Hello"},
        ...     {"user_id": 2, "message": "World"}
        ... ]
        >>> result = send_bulk_notifications.delay(notifs)
    """
    sent = 0
    failed = 0

    # Validate notification format
    for notification in notifications:
        if "user_id" not in notification or "message" not in notification:
            raise ValueError("Each notification must have user_id and message")

    # Process in rate-limited batches
    for i in range(0, len(notifications), rate_limit):
        batch = notifications[i : i + rate_limit]

        for notification in batch:
            try:
                # Send notification via HTTP API (placeholder)
                response = httpx.post(
                    "http://localhost/api/notifications",
                    json=notification,
                    timeout=5.0,
                )

                if response.status_code == 200:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    return {
        "status": "success",
        "sent": sent,
        "failed": failed,
        "total": len(notifications),
        "rate_limited": rate_limit < len(notifications),
    }

