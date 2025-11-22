"""Domain entities for the API service.

This module defines domain entities that represent core business concepts,
separate from database models and DTOs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class DataItem:
    """Domain entity for data items.

    This entity represents a data item in the domain layer,
    separate from the database representation.

    Attributes:
        id: Unique identifier (None for new items)
        name: Item name
        description: Optional description
        data: Additional data as key-value pairs
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    name: str
    description: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize timestamps for new entities."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def update(
        self, name: Optional[str] = None, description: Optional[str] = None, data: Optional[dict[str, Any]] = None
    ) -> None:
        """Update entity fields.

        Args:
            name: New name (if provided)
            description: New description (if provided)
            data: New data (if provided)
        """
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if data is not None:
            self.data = data
        self.updated_at = datetime.utcnow()

