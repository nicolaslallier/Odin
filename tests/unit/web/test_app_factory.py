"""Unit tests for FastAPI application factory.

Following TDD principles - RED phase: These tests will fail until implementation.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from pydantic import ValidationError


@pytest.mark.unit
class TestAppFactory:
    """Test suite for application factory."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        """Test that create_app returns a FastAPI instance."""
        from src.web.app import create_app

        app = create_app()

        assert isinstance(app, FastAPI)

    def test_create_app_has_title(self) -> None:
        """Test that the app has a proper title."""
        from src.web.app import create_app

        app = create_app()

        assert app.title == "Odin Web Interface"

    def test_create_app_has_version(self) -> None:
        """Test that the app has a version."""
        from src.web.app import create_app

        app = create_app()

        assert app.version == "0.4.2"

    def test_create_app_has_description(self) -> None:
        """Test that the app has a description."""
        from src.web.app import create_app

        app = create_app()

        assert app.description is not None
        assert len(app.description) > 0

    def test_create_app_accepts_custom_config(self) -> None:
        """Test that create_app accepts custom configuration."""
        from src.web.app import create_app
        from src.web.config import WebConfig

        custom_config = WebConfig(host="127.0.0.1", port=9000)
        app = create_app(config=custom_config)

        assert isinstance(app, FastAPI)

    def test_create_app_registers_routes(self) -> None:
        """Test that create_app registers routes."""
        from src.web.app import create_app

        app = create_app()

        # Check that routes are registered
        routes = [route.path for route in app.routes]
        assert "/" in routes

    def test_create_app_configures_static_files(self) -> None:
        """Test that create_app configures static file serving."""
        from src.web.app import create_app

        app = create_app()

        # Check that static files route exists
        routes = [route.path for route in app.routes]
        assert "/static/{path:path}" in routes or any("/static" in r for r in routes)

    def test_create_app_configures_templates(self) -> None:
        """Test that create_app configures Jinja2 templates."""
        from src.web.app import create_app

        app = create_app()

        # Verify that templates are configured
        assert hasattr(app.state, "templates") or "templates" in app.__dict__

    def test_create_app_is_reusable(self) -> None:
        """Test that create_app can be called multiple times."""
        from src.web.app import create_app

        app1 = create_app()
        app2 = create_app()

        assert isinstance(app1, FastAPI)
        assert isinstance(app2, FastAPI)
        assert app1 is not app2  # Should be different instances

    def test_create_app_has_health_endpoint(self) -> None:
        """Test that the app has a health check endpoint."""
        from src.web.app import create_app

        app = create_app()

        routes = [route.path for route in app.routes]
        assert "/health" in routes or "/api/health" in routes


@pytest.mark.unit
class TestAppDependencies:
    """Test suite for application dependencies and state."""

    def test_app_has_config_state(self) -> None:
        """Test that app state includes configuration."""
        from src.web.app import create_app

        app = create_app()

        assert hasattr(app.state, "config")

    def test_app_config_state_is_immutable(self) -> None:
        """Test that config state cannot be modified."""
        from src.web.app import create_app

        app = create_app()

        with pytest.raises((AttributeError, ValidationError)):
            app.state.config.port = 9999  # type: ignore

    def test_get_config_dependency_returns_config(self) -> None:
        """Test that get_config dependency returns configuration."""
        from src.web.app import get_config_dependency, create_app

        app = create_app()
        config = get_config_dependency(app)

        assert config is not None
        assert hasattr(config, "host")
        assert hasattr(config, "port")

