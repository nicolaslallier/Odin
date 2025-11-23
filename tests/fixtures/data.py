"""Data fixtures for testing.

This module provides pytest fixtures for test data.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.api.domain.entities import DataItem as DataItemEntity
from src.api.models.schemas import DataItem


@pytest.fixture
def sample_data_item_entity() -> DataItemEntity:
    """Create a sample data item entity for testing.

    Returns:
        Sample data item entity
    """
    return DataItemEntity(
        id=1,
        name="Test Item",
        description="A test data item",
        data={"key1": "value1", "key2": "value2"},
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_data_item_dto() -> DataItem:
    """Create a sample data item DTO for testing.

    Returns:
        Sample data item DTO
    """
    return DataItem(
        id=1,
        name="Test Item",
        description="A test data item",
        data={"key1": "value1", "key2": "value2"},
    )


@pytest.fixture
def sample_data_items_list() -> list[DataItemEntity]:
    """Create a list of sample data items for testing.

    Returns:
        List of sample data item entities
    """
    return [
        DataItemEntity(
            id=1,
            name="Item 1",
            description="First item",
            data={"type": "A"},
        ),
        DataItemEntity(
            id=2,
            name="Item 2",
            description="Second item",
            data={"type": "B"},
        ),
        DataItemEntity(
            id=3,
            name="Item 3",
            description="Third item",
            data={"type": "A"},
        ),
    ]


@pytest.fixture
def sample_batch_data() -> list[dict[str, str]]:
    """Create sample batch data for worker testing.

    Returns:
        List of batch data items
    """
    return [
        {"id": "1", "value": "data1"},
        {"id": "2", "value": "data2"},
        {"id": "3", "value": "data3"},
        {"id": "4", "value": "data4"},
        {"id": "5", "value": "data5"},
    ]


@pytest.fixture
def sample_notifications() -> list[dict[str, str | int]]:
    """Create sample notifications for worker testing.

    Returns:
        List of notification dictionaries
    """
    return [
        {"user_id": 1, "message": "Test notification 1"},
        {"user_id": 2, "message": "Test notification 2"},
        {"user_id": 3, "message": "Test notification 3"},
    ]


@pytest.fixture
def invalid_data_item() -> dict[str, str]:
    """Create invalid data for error testing.

    Returns:
        Invalid data item dictionary
    """
    return {
        "name": "",  # Empty name (invalid)
        "description": None,
    }
