"""Structured logging configuration for the API service.

This module configures structured logging with JSON output for better
log aggregation and analysis.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Any, cast, MutableMapping

try:
    import orjson as json
except ImportError:
    import json  # type: ignore

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


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
                return (
                    json.dumps(log_data).decode("utf-8")
                    if isinstance(json.dumps(log_data), bytes)
                    else json.dumps(log_data)
                )
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

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
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


class DatabaseLogHandler(logging.Handler):
    """Async database log handler with buffering.

    This handler batches log records and writes them to PostgreSQL in bulk
    to reduce database load. It runs a background thread that periodically
    flushes the buffer.

    Attributes:
        dsn: PostgreSQL connection string
        buffer_size: Maximum number of records before flush
        buffer_timeout: Maximum seconds before flush
        min_level: Minimum log level to store in database
        service_name: Name of the service (api, worker, web, etc.)
    """

    def __init__(
        self,
        dsn: str,
        service_name: str,
        buffer_size: int = 100,
        buffer_timeout: float = 5.0,
        min_level: int = logging.INFO,
    ) -> None:
        """Initialize database log handler.

        Args:
            dsn: PostgreSQL connection string
            service_name: Name of the service generating logs
            buffer_size: Maximum records before flush (default: 100)
            buffer_timeout: Maximum seconds before flush (default: 5.0)
            min_level: Minimum log level to store (default: INFO)
        """
        super().__init__(level=min_level)
        self.dsn = dsn
        self.service_name = service_name
        self.buffer_size = buffer_size
        self.buffer_timeout = buffer_timeout
        self.min_level = min_level

        self._buffer: Queue[dict[str, Any]] = Queue()
        self._engine: AsyncEngine | None = None
        self._shutdown = threading.Event()
        self._flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self._flush_thread.start()
        self._last_flush = time.time()

    def _get_engine(self) -> AsyncEngine:
        """Get or create async database engine.

        Returns:
            SQLAlchemy async engine
        """
        if self._engine is None:
            self._engine = create_async_engine(
                self.dsn,
                echo=False,
                pool_pre_ping=True,
                pool_size=2,
                max_overflow=5,
            )
        return self._engine

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the buffer.

        Args:
            record: Log record to emit
        """
        try:
            # Extract log data
            log_data: dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created),
                "level": record.levelname,
                "service": self.service_name,
                "logger": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "exception": self.format(record) if record.exc_info else None,
                "request_id": getattr(record, "request_id", None),
                "task_id": getattr(record, "task_id", None),
                "user_id": getattr(record, "user_id", None),
                "metadata": {},
            }

            # Add extra fields to metadata
            if hasattr(record, "extra_fields"):
                log_data["metadata"].update(record.extra_fields)

            # Add to buffer
            self._buffer.put(log_data)

            # Check if we should flush immediately
            if self._buffer.qsize() >= self.buffer_size:
                self._trigger_flush()

        except Exception:
            # Don't let logging errors break the application
            self.handleError(record)

    def _trigger_flush(self) -> None:
        """Trigger an immediate flush of the buffer."""
        # Signal the flush thread to wake up
        pass

    def _flush_worker(self) -> None:
        """Background worker that flushes buffer periodically."""
        while not self._shutdown.is_set():
            try:
                # Check if we should flush
                should_flush = (
                    self._buffer.qsize() >= self.buffer_size
                    or (time.time() - self._last_flush) >= self.buffer_timeout
                )

                if should_flush and not self._buffer.empty():
                    self._flush_buffer()
                    self._last_flush = time.time()

                # Sleep briefly to avoid busy waiting
                time.sleep(0.5)

            except Exception:
                # Continue even if flush fails
                time.sleep(1)

    def _flush_buffer(self) -> None:
        """Flush buffered log records to database."""
        if self._buffer.empty():
            return

        # Collect all pending records
        records: list[dict[str, Any]] = []
        while not self._buffer.empty() and len(records) < self.buffer_size:
            try:
                records.append(self._buffer.get_nowait())
            except Exception:
                break

        if not records:
            return

        # Insert records in bulk
        try:
            asyncio.run(self._insert_logs(records))
        except Exception as e:
            # Suppress shutdown/atexit errors during interpreter exit
            msg = str(e)
            if (
                "atexit" in msg
                or "after shutdown" in msg
                or "cannot schedule new futures" in msg
                or "no event loop" in msg
            ):
                return
            print(f"Failed to insert logs to database: {e}", file=sys.stderr)

    async def _insert_logs(self, records: list[dict[str, Any]]) -> None:
        """Insert log records into database.

        Args:
            records: List of log records to insert
        """
        engine = self._get_engine()

        # Build bulk insert query
        values_list = []
        for record in records:
            # Convert UUID objects to strings
            request_id = str(record["request_id"]) if record["request_id"] else None
            task_id = str(record["task_id"]) if record["task_id"] else None

            values_list.append(
                f"('{record['timestamp'].isoformat()}', "
                f"'{record['level']}', "
                f"'{record['service']}', "
                f"'{record['logger'].replace("'", "''")}', "
                f"'{record['message'].replace("'", "''")}', "
                f"'{record['module']}', "
                f"'{record['function']}', "
                f"{record['line']}, "
                f"{'NULL' if not record['exception'] else "'" + record['exception'].replace("'", "''") + "'"}, "
                f"{'NULL' if not request_id else "'" + request_id + "'"}, "
                f"{'NULL' if not task_id else "'" + task_id + "'"}, "
                f"{'NULL' if not record['user_id'] else "'" + record['user_id'].replace("'", "''") + "'"}, "
                f"'{json.dumps(record['metadata']) if hasattr(json, 'dumps') else '{}'}')"
            )

        if not values_list:
            return

        query = f"""
            INSERT INTO application_logs (
                timestamp, level, service, logger, message, module, function,
                line, exception, request_id, task_id, user_id, metadata
            ) VALUES {', '.join(values_list)}
        """

        async with engine.begin() as conn:
            await conn.execute(text(query))

    def flush(self) -> None:
        """Flush all buffered log records."""
        self._flush_buffer()

    def close(self) -> None:
        """Close the handler and cleanup resources."""
        # Signal shutdown
        self._shutdown.set()

        # Flush remaining records
        self.flush()

        # Wait for flush thread to finish
        if self._flush_thread.is_alive():
            self._flush_thread.join(timeout=5.0)

        # Close engine
        if self._engine is not None:
            asyncio.run(self._engine.dispose())
            self._engine = None

        super().close()


def configure_logging_with_db(
    level: str = "INFO",
    use_json: bool = True,
    log_file: str | None = None,
    db_dsn: str | None = None,
    service_name: str = "unknown",
    db_min_level: str = "INFO",
    db_buffer_size: int = 100,
    db_buffer_timeout: float = 5.0,
) -> None:
    """Configure structured logging with optional database handler.

    Args:
        level: Logging level for console/file (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        log_file: Optional file path for file logging
        db_dsn: Optional PostgreSQL DSN for database logging
        service_name: Name of the service (api, worker, web, etc.)
        db_min_level: Minimum log level to store in database
        db_buffer_size: Buffer size for database handler
        db_buffer_timeout: Buffer timeout for database handler
    """
    # Convert string levels to logging constants
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    db_numeric_level = getattr(logging, db_min_level.upper(), logging.INFO)

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
    root_logger.setLevel(min(numeric_level, db_numeric_level))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Database handler if DSN provided
    if db_dsn:
        try:
            db_handler = DatabaseLogHandler(
                dsn=db_dsn,
                service_name=service_name,
                buffer_size=db_buffer_size,
                buffer_timeout=db_buffer_timeout,
                min_level=db_numeric_level,
            )
            root_logger.addHandler(db_handler)
        except Exception as e:
            print(f"Warning: Failed to initialize database log handler: {e}", file=sys.stderr)

    # Set level for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
