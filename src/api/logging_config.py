"""Structured logging configuration for the API service.

This module configures structured logging with JSON output for better
log aggregation and analysis.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    import orjson as json
except ImportError:
    import json  # type: ignore


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging.

    This formatter outputs logs in JSON format with structured fields
    for better parsing and analysis in log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add request context if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        try:
            if hasattr(json, "dumps"):
                return json.dumps(log_data).decode("utf-8") if isinstance(json.dumps(log_data), bytes) else json.dumps(log_data)
            return json.dumps(log_data)
        except Exception:
            # Fallback to simple format if JSON serialization fails
            return f"{log_data['timestamp']} - {log_data['level']} - {log_data['message']}"


def configure_logging(
    level: str = "INFO",
    use_json: bool = True,
    log_file: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        log_file: Optional file path for file logging
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create formatter
    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set level for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding contextual information to logs.

    This adapter allows adding request-specific context like request_id
    and user_id to all log messages.
    """

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Process log message to add extra context.

        Args:
            msg: Log message
            kwargs: Logging keyword arguments

        Returns:
            Processed message and kwargs
        """
        # Add extra fields from adapter context
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)
        return msg, kwargs


def get_logger(name: str, **context: Any) -> logging.Logger | LoggerAdapter:
    """Get a logger with optional context.

    Args:
        name: Logger name (usually __name__)
        **context: Additional context to add to all logs

    Returns:
        Logger or LoggerAdapter with context

    Example:
        >>> logger = get_logger(__name__, request_id="abc-123")
        >>> logger.info("Processing request")
    """
    logger = logging.getLogger(name)
    if context:
        return LoggerAdapter(logger, context)
    return logger

