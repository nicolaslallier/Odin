"""Integration tests for template rendering.

These tests verify that templates are rendered correctly with proper context.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestTemplateRendering:
    """Integration test suite for template rendering."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client for testing templates.

        Returns:
            TestClient instance for making test requests
        """
        from src.web.app import create_app

        app = create_app()
        return TestClient(app)

    def test_base_template_is_used(self, client: TestClient) -> None:
        """Test that pages use the base template."""
        response = client.get("/")

        content = response.text
        # Check for base template elements
        assert "Odin" in content
        assert "footer" in content.lower()

    def test_index_template_renders_message(self, client: TestClient) -> None:
        """Test that index template renders the welcome message."""
        response = client.get("/")

        content = response.text
        assert "Hello World" in content or "Hello, World" in content
        assert "Welcome" in content

    def test_template_includes_version(self, client: TestClient) -> None:
        """Test that template includes version information."""
        response = client.get("/")

        content = response.text
        assert "0.4.2" in content

    def test_template_renders_features(self, client: TestClient) -> None:
        """Test that template renders feature cards."""
        response = client.get("/")

        content = response.text
        assert "FastAPI" in content
        assert "TDD" in content
        assert "SOLID" in content

    def test_template_has_proper_structure(self, client: TestClient) -> None:
        """Test that template has proper semantic HTML structure."""
        response = client.get("/")

        content = response.text
        assert "<header>" in content or "<nav>" in content
        assert "<main" in content
        assert "<footer>" in content

    def test_template_is_accessible(self, client: TestClient) -> None:
        """Test that template includes accessibility features."""
        response = client.get("/")

        content = response.text
        # Check for basic accessibility
        assert 'lang="en"' in content or 'lang=en' in content
        assert "<title>" in content
        assert 'charset="UTF-8"' in content or 'charset=UTF-8' in content

    def test_template_is_responsive(self, client: TestClient) -> None:
        """Test that template includes responsive meta tags."""
        response = client.get("/")

        content = response.text
        assert "viewport" in content
        assert "width=device-width" in content

    def test_css_linked_correctly(self, client: TestClient) -> None:
        """Test that CSS is linked correctly in template."""
        response = client.get("/")

        content = response.text
        assert 'rel="stylesheet"' in content or 'rel=stylesheet' in content
        assert "/static/css/style.css" in content

    def test_template_context_variables_rendered(self, client: TestClient) -> None:
        """Test that all context variables are properly rendered."""
        response = client.get("/")

        content = response.text
        # These should come from the route context
        assert "Welcome to Odin" in content or "Odin" in content
        assert "Hello World" in content or "Hello, World" in content
        assert "0.4.2" in content

    def test_no_template_errors_in_response(self, client: TestClient) -> None:
        """Test that there are no template rendering errors."""
        response = client.get("/")

        content = response.text
        # Check for common template error indicators
        assert "TemplateNotFound" not in content
        assert "UndefinedError" not in content
        assert "{{ " not in content  # No unrendered variables
        assert "{% " not in content  # No unrendered tags

