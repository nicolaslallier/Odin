"""Celery Beat schedule configuration.

This module defines the schedule for periodic tasks executed by Celery Beat.
Tasks are scheduled using timedelta or crontab for various intervals.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from celery.schedules import crontab


def get_beat_schedule() -> dict[str, dict[str, Any]]:
    """Get the Celery Beat schedule configuration.

    This function returns a dictionary defining all periodic tasks and their
    execution schedules. Tasks can be scheduled using timedelta for interval-based
    scheduling or crontab for cron-like scheduling.

    Returns:
        Dictionary mapping task names to their schedule configuration

    Example:
        >>> schedule = get_beat_schedule()
        >>> print(schedule['health-check-services']['schedule'])
    """
    return {
        # Health check services every 5 minutes
        "health-check-services": {
            "task": "src.worker.tasks.scheduled.health_check_services",
            "schedule": timedelta(minutes=5),
            "options": {"expires": 300},  # Expire after 5 minutes
        },
        # Cleanup old task results daily at 2 AM
        "cleanup-old-task-results": {
            "task": "src.worker.tasks.scheduled.cleanup_old_task_results",
            "schedule": crontab(hour=2, minute=0),
            "args": (30,),  # Keep results for 30 days
            "options": {"expires": 3600},  # Expire after 1 hour
        },
        # Generate daily report at midnight
        "generate-daily-report": {
            "task": "src.worker.tasks.scheduled.generate_daily_report",
            "schedule": crontab(hour=0, minute=0),
            "options": {"expires": 3600},  # Expire after 1 hour
        },
        # Cleanup old logs daily at 2 AM
        "cleanup-old-logs": {
            "task": "maintenance.cleanup_old_logs",
            "schedule": crontab(hour=2, minute=30),
            "options": {"expires": 7200},  # Expire after 2 hours
        },
        # Collect log statistics every hour
        "log-statistics": {
            "task": "maintenance.log_statistics",
            "schedule": crontab(minute=15),  # Run at :15 past every hour
            "options": {"expires": 3600},  # Expire after 1 hour
        },
    }
