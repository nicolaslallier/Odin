"""Unit tests for inactivity tracking middleware.

This module tests the InactivityTracker and InactivityMiddleware classes
that enable automatic service shutdown based on inactivity.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from src.api.middleware.inactivity_tracker import (
    InactivityMiddleware,
    InactivityTracker,
    add_inactivity_tracking,
)


class TestInactivityTracker:
    """Test suite for InactivityTracker class."""

    def test_initialization(self):
        """Test tracker initializes with current timestamp."""
        tracker = InactivityTracker()
        
        assert tracker.request_count == 0
        assert tracker.last_activity > 0
        assert tracker.service_start_time > 0
        assert tracker.get_idle_seconds() < 1  # Just initialized

    def test_record_activity(self):
        """Test recording activity updates timestamp and counter."""
        tracker = InactivityTracker()
        initial_count = tracker.request_count
        initial_time = tracker.last_activity
        
        time.sleep(0.1)
        tracker.record_activity()
        
        assert tracker.request_count == initial_count + 1
        assert tracker.last_activity > initial_time

    def test_get_idle_seconds(self):
        """Test idle time calculation."""
        tracker = InactivityTracker()
        
        # Record activity then wait
        tracker.record_activity()
        time.sleep(0.2)
        
        idle = tracker.get_idle_seconds()
        assert 0.15 < idle < 0.3  # Should be around 0.2 seconds

    def test_get_uptime_seconds(self):
        """Test uptime calculation."""
        tracker = InactivityTracker()
        time.sleep(0.1)
        
        uptime = tracker.get_uptime_seconds()
        assert uptime >= 0.1

    def test_get_metrics(self):
        """Test metrics dictionary contains all expected fields."""
        tracker = InactivityTracker()
        tracker.record_activity()
        tracker.record_activity()
        
        metrics = tracker.get_metrics()
        
        assert "idle_seconds" in metrics
        assert "uptime_seconds" in metrics
        assert "request_count" in metrics
        assert "last_activity_timestamp" in metrics
        assert metrics["request_count"] == 2


class TestInactivityMiddleware:
    """Test suite for InactivityMiddleware class."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app."""
        return FastAPI()

    @pytest.fixture
    def tracker(self) -> InactivityTracker:
        """Create a test tracker."""
        return InactivityTracker()

    @pytest.fixture
    def client(self, app: FastAPI, tracker: InactivityTracker) -> TestClient:
        """Create a test client with middleware."""
        app.add_middleware(InactivityMiddleware, tracker=tracker)
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        @app.get("/internal/test")
        async def internal_endpoint():
            return {"status": "internal"}
        
        return TestClient(app)

    def test_middleware_records_activity(self, client: TestClient, tracker: InactivityTracker):
        """Test middleware records activity on regular requests."""
        initial_count = tracker.request_count
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert tracker.request_count == initial_count + 1

    def test_middleware_skips_internal_endpoints(
        self, client: TestClient, tracker: InactivityTracker
    ):
        """Test middleware skips activity recording for internal endpoints."""
        initial_count = tracker.request_count
        
        response = client.get("/internal/test")
        
        assert response.status_code == 200
        assert tracker.request_count == initial_count  # No increment

    def test_middleware_updates_idle_time(self, client: TestClient, tracker: InactivityTracker):
        """Test middleware updates idle time correctly."""
        # Make a request
        client.get("/test")
        time.sleep(0.1)
        
        # Check idle time increased
        idle = tracker.get_idle_seconds()
        assert idle >= 0.1


class TestAddInactivityTracking:
    """Test suite for add_inactivity_tracking function."""

    def test_adds_middleware_and_endpoint(self):
        """Test function adds middleware and activity endpoint."""
        app = FastAPI()
        
        tracker = add_inactivity_tracking(app)
        
        # Check tracker was returned
        assert isinstance(tracker, InactivityTracker)
        
        # Check tracker stored in app state
        assert hasattr(app.state, "inactivity_tracker")
        assert app.state.inactivity_tracker is tracker
        
        # Check middleware was added
        assert len(app.user_middleware) > 0
        
        # Check activity endpoint exists
        client = TestClient(app)
        response = client.get("/internal/activity")
        assert response.status_code == 200

    def test_activity_endpoint_returns_metrics(self):
        """Test activity endpoint returns correct metrics."""
        app = FastAPI()
        tracker = add_inactivity_tracking(app)
        
        # Record some activity
        tracker.record_activity()
        tracker.record_activity()
        
        client = TestClient(app)
        response = client.get("/internal/activity")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "idle_seconds" in data
        assert "uptime_seconds" in data
        assert "request_count" in data
        assert "last_activity_timestamp" in data
        assert data["request_count"] == 2

    def test_activity_endpoint_not_recorded_as_activity(self):
        """Test activity endpoint doesn't trigger activity recording."""
        app = FastAPI()
        tracker = add_inactivity_tracking(app)
        
        initial_count = tracker.request_count
        
        client = TestClient(app)
        client.get("/internal/activity")
        
        # Request count should not increase
        assert tracker.request_count == initial_count

