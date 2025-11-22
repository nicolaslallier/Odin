"""Worker task modules.

This package contains all Celery task definitions organized by type:
- scheduled: Periodic tasks executed by Celery Beat
- batch: Batch processing tasks for large datasets
- events: Event-driven tasks triggered by user actions
"""

from src.worker.tasks.batch import (
    process_bulk_data,
    process_file_batch,
    send_bulk_notifications,
)
from src.worker.tasks.events import (
    handle_user_registration,
    process_webhook,
    send_notification,
)
from src.worker.tasks.scheduled import (
    cleanup_old_task_results,
    generate_daily_report,
    health_check_services,
)

__all__ = [
    # Scheduled tasks
    "health_check_services",
    "cleanup_old_task_results",
    "generate_daily_report",
    # Batch tasks
    "process_bulk_data",
    "process_file_batch",
    "send_bulk_notifications",
    # Event tasks
    "handle_user_registration",
    "process_webhook",
    "send_notification",
]

