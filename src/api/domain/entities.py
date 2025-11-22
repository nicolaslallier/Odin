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


@dataclass
class ImageAnalysis:
    """Domain entity for image analysis records.

    This entity represents an analyzed image with its LLM-generated description
    and storage metadata.

    Attributes:
        filename: Original filename of the uploaded image
        bucket: MinIO bucket name where image is stored
        object_key: Unique object key in MinIO
        content_type: MIME type of the image
        size_bytes: Size of the image in bytes
        llm_description: LLM-generated description of the image
        model_used: Name of the LLM model used for analysis
        id: Unique identifier (None for new items)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    filename: str
    bucket: str
    object_key: str
    content_type: str
    size_bytes: int
    llm_description: Optional[str] = None
    model_used: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize timestamps for new entities."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def update_description(self, description: str, model: str) -> None:
        """Update the LLM-generated description.

        Args:
            description: New LLM-generated description
            model: Model used for the analysis
        """
        self.llm_description = description
        self.model_used = model
        self.updated_at = datetime.utcnow()

