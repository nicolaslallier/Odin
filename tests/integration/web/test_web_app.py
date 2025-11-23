"""Integration tests for the complete web application.

These tests verify that all components work together correctly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestWebApplicationIntegration:
    """Integration test suite for the full web application."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client with full application setup.

        Returns:
            TestClient instance for making test requests
        """
        from src.web.app import create_app

        app = create_app()
        # Mount static files for web app integration tests
        import os

        from fastapi.staticfiles import StaticFiles

        static_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "web", "static"
        )
        os.makedirs(static_dir, exist_ok=True)
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        return TestClient(app)

    def test_application_starts_successfully(self, client: TestClient) -> None:
        """Test that the application starts and responds."""
        # Check that the web dashboard (HTML) renders
        resp_html = client.get("/health")
        assert resp_html.status_code == 200
        assert "Odin" in resp_html.text or "Health" in resp_html.text    # minimal HTML content check

        # Check that health API returns JSON
        resp_api = client.get("/health/api")
        assert resp_api.status_code == 200
        assert resp_api.headers["content-type"].startswith("application/json")
        data = resp_api.json()
        assert "infrastructure" in data
        assert "application" in data

    def test_home_page_renders_complete_html(self, client: TestClient) -> None:
        """Test that home page renders with complete HTML structure."""
        response = client.get("/")

        assert response.status_code == 200
        content = response.text

        # Verify complete HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "<head>" in content
        assert "<body>" in content
        assert "</body>" in content
        assert "</html>" in content

    def test_home_page_includes_navigation(self, client: TestClient) -> None:
        """Test that home page includes navigation elements."""
        response = client.get("/")

        content = response.text
        assert "nav" in content.lower()
        assert "Home" in content
        assert "Health" in content

    def test_home_page_includes_footer(self, client: TestClient) -> None:
        """Test that home page includes footer with version."""
        response = client.get("/")

        content = response.text
        assert "footer" in content.lower()
        assert "1.5.0" in content or "Version" in content

    def test_static_css_is_referenced(self, client: TestClient) -> None:
        """Test that CSS file is properly referenced."""
        response = client.get("/")

        content = response.text
        assert "/static/css/style.css" in content or "stylesheet" in content

    def test_static_files_are_served(self, client: TestClient) -> None:
        """Test that static files can be accessed."""
        response = client.get("/static/css/style.css")

        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_404_for_nonexistent_route(self, client: TestClient) -> None:
        """Test that nonexistent routes return 404."""
        response = client.get("/nonexistent-route-12345")

        assert response.status_code == 404

    def test_application_handles_multiple_requests(self, client: TestClient) -> None:
        """Test that application handles multiple concurrent-like requests."""
        responses = []
        for _ in range(10):
            response = client.get("/")
            responses.append(response)

        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)

        # All responses should be consistent
        first_content = responses[0].text
        assert all(r.text == first_content for r in responses)

    def test_configuration_is_accessible(self, client: TestClient) -> None:
        """Test that application configuration is properly set up."""
        from src.web.app import create_app

        app = create_app()

        assert hasattr(app.state, "config")
        assert app.state.config.host == "0.0.0.0"
        assert app.state.config.port == 8000

    def test_application_metadata_is_correct(self, client: TestClient) -> None:
        """Test that application has correct metadata."""
        from src.web.app import create_app

        app = create_app()

        assert app.title == "Odin Web Interface"
        assert app.version == "1.6.0"
        assert app.description is not None
