"""Unit tests for home route handlers.

Following TDD principles - RED phase: These tests will fail until implementation.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHomeRouter:
    """Test suite for home router configuration."""

    def test_home_router_exists(self) -> None:
        """Test that home router can be imported."""
        from src.web.routes.home import router

        assert isinstance(router, APIRouter)

    def test_home_router_has_routes(self) -> None:
        """Test that home router has registered routes."""
        from src.web.routes.home import router

        assert len(router.routes) > 0

    def test_home_router_has_root_route(self) -> None:
        """Test that home router has a root route."""
        from src.web.routes.home import router

        paths = [route.path for route in router.routes]
        assert "/" in paths


@pytest.mark.unit
class TestHomeRouteHandlers:
    """Test suite for home route handler functions."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client for the application.

        Returns:
            TestClient instance for making test requests
        """
        from src.web.app import create_app

        app = create_app()
        return TestClient(app)

    def test_home_page_returns_200(self, client: TestClient) -> None:
        """Test that home page returns 200 status code."""
        response = client.get("/")

        assert response.status_code == 200

    def test_home_page_returns_html(self, client: TestClient) -> None:
        """Test that home page returns HTML content."""
        response = client.get("/")

        assert "text/html" in response.headers["content-type"]

    def test_home_page_contains_hello_world(self, client: TestClient) -> None:
        """Test that home page contains 'Hello World' text."""
        response = client.get("/")

        assert "Hello World" in response.text or "Hello, World" in response.text

    def test_home_page_contains_odin_title(self, client: TestClient) -> None:
        """Test that home page contains Odin in title or heading."""
        response = client.get("/")

        # Check for Odin in various elements
        assert "Odin" in response.text

    def test_home_page_has_proper_html_structure(self, client: TestClient) -> None:
        """Test that home page has proper HTML structure."""
        response = client.get("/")

        content = response.text
        assert "<!DOCTYPE html>" in content or "<html" in content
        assert "<head>" in content
        assert "<body>" in content
        assert "</html>" in content

    def test_home_page_is_idempotent(self, client: TestClient) -> None:
        """Test that multiple requests to home page return consistent results."""
        response1 = client.get("/")
        response2 = client.get("/")

        assert response1.status_code == response2.status_code
        assert response1.text == response2.text

    def test_health_endpoint_returns_200(self, client: TestClient) -> None:
        """Test that ping endpoint returns 200 status code."""
        response = client.get("/ping")

        assert response.status_code == 200

    def test_health_endpoint_returns_json(self, client: TestClient) -> None:
        """Test that ping endpoint returns JSON."""
        response = client.get("/ping")

        assert response.headers["content-type"] == "application/json"

    def test_health_endpoint_has_status_field(self, client: TestClient) -> None:
        """Test that ping endpoint returns status field."""
        response = client.get("/ping")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"

