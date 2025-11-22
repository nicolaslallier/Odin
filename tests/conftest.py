"""Pytest configuration and shared fixtures.

This module provides pytest configuration and makes fixtures available
across all test modules.
"""

from __future__ import annotations

# Import all fixtures to make them available
pytest_plugins = [
    "tests.fixtures.services",
    "tests.fixtures.data",
]

