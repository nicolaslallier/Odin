"""Inactivity tracking middleware for microservices.

This module provides middleware to track request activity and expose idle time
metrics for automatic service shutdown based on inactivity.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class InactivityTracker:
    """Tracks last activity timestamp for the service.

    This class maintains a timestamp of the last request received by the service,
    which can be used to determine if the service has been idle and should be
    shut down to save resources.
    """

    def __init__(self):
        """Initialize the inactivity tracker."""
        self.last_activity: float = time.time()
        self.request_count: int = 0
        self.service_start_time: float = time.time()

    def record_activity(self) -> None:
        """Record a new activity (request received).

        Updates the last activity timestamp and increments the request counter.
        """
        self.last_activity = time.time()
        self.request_count += 1

    def get_idle_seconds(self) -> float:
        """Get the number of seconds since last activity.

        Returns:
            Number of seconds since the last recorded activity
        """
        return time.time() - self.last_activity

    def get_uptime_seconds(self) -> float:
        """Get the service uptime in seconds.

        Returns:
            Number of seconds since service started
        """
        return time.time() - self.service_start_time

    def get_metrics(self) -> dict[str, float | int]:
        """Get activity metrics for the service.

        Returns:
            Dictionary containing idle time, uptime, and request count
        """
        return {
            "idle_seconds": self.get_idle_seconds(),
            "uptime_seconds": self.get_uptime_seconds(),
            "request_count": self.request_count,
            "last_activity_timestamp": self.last_activity,
        }


class InactivityMiddleware(BaseHTTPMiddleware):
    """Middleware to track request activity.

    This middleware records every request to track service activity,
    excluding internal monitoring endpoints to avoid false activity signals.
    """

    def __init__(self, app: FastAPI, tracker: InactivityTracker):
        """Initialize the middleware.

        Args:
            app: FastAPI application instance
            tracker: InactivityTracker instance to record activity
        """
        super().__init__(app)
        self.tracker = tracker

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and record activity.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response from the next handler
        """
        # Skip activity recording for internal monitoring endpoints
        if not request.url.path.startswith("/internal/"):
            self.tracker.record_activity()
            logger.debug(
                f"Activity recorded: {request.method} {request.url.path} "
                f"(total requests: {self.tracker.request_count})"
            )

        response = await call_next(request)
        return response


def add_inactivity_tracking(app: FastAPI) -> InactivityTracker:
    """Add inactivity tracking to a FastAPI application.

    This function creates an InactivityTracker, adds the middleware,
    and registers the internal activity endpoint.

    Args:
        app: FastAPI application instance

    Returns:
        InactivityTracker instance for external access
    """
    tracker = InactivityTracker()

    # Add middleware
    app.add_middleware(InactivityMiddleware, tracker=tracker)

    # Add internal activity endpoint
    @app.get("/internal/activity", tags=["internal"])
    async def get_activity_metrics():
        """Get service activity metrics.

        This endpoint returns information about service activity including
        idle time, uptime, and request count. It's used by monitoring
        systems to determine if the service should be shut down.

        Returns:
            Activity metrics dictionary
        """
        return tracker.get_metrics()

    # Store tracker in app state for external access
    app.state.inactivity_tracker = tracker

    logger.info("Inactivity tracking initialized")

    return tracker

