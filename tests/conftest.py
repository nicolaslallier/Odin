"""Pytest configuration and shared fixtures.

This module provides pytest configuration and makes fixtures available
across all test modules.
"""

from __future__ import annotations

import os
import pytest

# Import all fixtures to make them available
pytest_plugins = [
    "tests.fixtures.services",
    "tests.fixtures.data",
]


@pytest.fixture(autouse=True, scope="session")
def celery_env_vars():
    """Ensure Celery env vars for all tests (in-memory broker/back for test isolation)."""
    os.environ.setdefault("CELERY_BROKER_URL", "memory://")
    os.environ.setdefault("CELERY_RESULT_BACKEND", "db+sqlite:///file::memory:?cache=shared")


@pytest.fixture(autouse=True, scope="session")
def minio_and_api_test_env_vars():
    os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
    os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
    os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
    os.environ.setdefault("VAULT_ADDR", "http://localhost:8200")
    os.environ.setdefault("VAULT_TOKEN", "root")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")

