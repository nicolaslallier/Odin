"""Unit tests for web application configuration.

Following TDD principles - RED phase: These tests will fail until implementation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestWebConfig:
    """Test suite for web configuration management."""

    def test_config_has_default_values(self) -> None:
        """Test that configuration initializes with sensible defaults."""
        from src.web.config import WebConfig

        config = WebConfig()

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is False
        assert config.log_level == "info"

    def test_config_accepts_custom_values(self) -> None:
        """Test that configuration accepts custom values."""
        from src.web.config import WebConfig

        config = WebConfig(
            host="127.0.0.1",
            port=9000,
            reload=True,
            log_level="debug",
        )

        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.reload is True
        assert config.log_level == "debug"

    def test_config_validates_port_range(self) -> None:
        """Test that port must be in valid range."""
        from src.web.config import WebConfig

        with pytest.raises(ValidationError):
            WebConfig(port=0)

        with pytest.raises(ValidationError):
            WebConfig(port=65536)

        with pytest.raises(ValidationError):
            WebConfig(port=-1)

    def test_config_validates_log_level(self) -> None:
        """Test that log level must be valid."""
        from src.web.config import WebConfig

        with pytest.raises(ValidationError):
            WebConfig(log_level="invalid")

    def test_config_valid_log_levels(self) -> None:
        """Test that all standard log levels are accepted."""
        from src.web.config import WebConfig

        valid_levels = ["debug", "info", "warning", "error", "critical"]

        for level in valid_levels:
            config = WebConfig(log_level=level)
            assert config.log_level == level

    def test_config_from_env(self) -> None:
        """Test that configuration can be loaded from environment variables."""
        import os

        from src.web.config import get_config

        # Set environment variables
        os.environ["WEB_HOST"] = "192.168.1.1"
        os.environ["WEB_PORT"] = "8080"
        os.environ["WEB_RELOAD"] = "true"
        os.environ["WEB_LOG_LEVEL"] = "debug"

        config = get_config()

        assert config.host == "192.168.1.1"
        assert config.port == 8080
        assert config.reload is True
        assert config.log_level == "debug"

        # Cleanup
        del os.environ["WEB_HOST"]
        del os.environ["WEB_PORT"]
        del os.environ["WEB_RELOAD"]
        del os.environ["WEB_LOG_LEVEL"]

    def test_config_env_defaults_when_not_set(self) -> None:
        """Test that defaults are used when environment variables are not set."""
        import os

        from src.web.config import get_config

        # Ensure env vars are not set
        for key in ["WEB_HOST", "WEB_PORT", "WEB_RELOAD", "WEB_LOG_LEVEL"]:
            os.environ.pop(key, None)

        config = get_config()

        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is False
        assert config.log_level == "info"

    def test_config_is_immutable(self) -> None:
        """Test that configuration is immutable after creation."""
        from src.web.config import WebConfig

        config = WebConfig()

        with pytest.raises((AttributeError, ValidationError)):
            config.port = 9000  # type: ignore

    def test_config_string_representation(self) -> None:
        """Test that configuration has useful string representation."""
        from src.web.config import WebConfig

        config = WebConfig(host="localhost", port=8000)
        config_str = str(config)

        assert "localhost" in config_str
        assert "8000" in config_str
