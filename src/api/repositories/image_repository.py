"""Repository for image analysis persistence.

This module provides data access operations for image analysis records using
the repository pattern to abstract database operations.
"""

from __future__ import annotations

from typing import List

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.domain.entities import ImageAnalysis
from src.api.exceptions import DatabaseError, ResourceNotFoundError


# Define the image_analysis table
metadata = MetaData()

image_analysis_table = Table(
    "image_analysis",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String(255), nullable=False),
    Column("bucket", String(100), nullable=False),
    Column("object_key", String(500), nullable=False),
    Column("content_type", String(100), nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("llm_description", String, nullable=True),
    Column("model_used", String(100), nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


class ImageRepository:
    """Repository for image analysis persistence operations.

    This class provides CRUD operations for image analysis records, following the
    Repository pattern to abstract database operations from business logic.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, item: ImageAnalysis) -> ImageAnalysis:
        """Create a new image analysis record.

        Args:
            item: ImageAnalysis entity to create

        Returns:
            Created image analysis with assigned ID

        Raises:
            DatabaseError: If creation fails
        """
        try:
            stmt = (
                insert(image_analysis_table)
                .values(
                    filename=item.filename,
                    bucket=item.bucket,
                    object_key=item.object_key,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    llm_description=item.llm_description,
                    model_used=item.model_used,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                .returning(image_analysis_table.c.id)
            )

            result = await self.session.execute(stmt)
            item_id = result.scalar_one()
            item.id = item_id
            await self.session.commit()
            return item
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create image analysis: {e}")

    async def get_by_id(self, item_id: int) -> ImageAnalysis:
        """Get an image analysis record by ID.

        Args:
            item_id: ID of the item to retrieve

        Returns:
            ImageAnalysis entity

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If retrieval fails
        """
        try:
            stmt = select(image_analysis_table).where(image_analysis_table.c.id == item_id)
            result = await self.session.execute(stmt)
            row = result.first()

            if row is None:
                raise ResourceNotFoundError(
                    f"Image analysis not found", {"id": item_id}
                )

            return ImageAnalysis(
                id=row.id,
                filename=row.filename,
                bucket=row.bucket,
                object_key=row.object_key,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
                llm_description=row.llm_description,
                model_used=row.model_used,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve image analysis: {e}")

    async def get_all(self) -> List[ImageAnalysis]:
        """Get all image analysis records.

        Returns:
            List of ImageAnalysis entities

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            stmt = select(image_analysis_table).order_by(
                image_analysis_table.c.created_at.desc()
            )
            result = await self.session.execute(stmt)
            rows = result.fetchall()

            return [
                ImageAnalysis(
                    id=row.id,
                    filename=row.filename,
                    bucket=row.bucket,
                    object_key=row.object_key,
                    content_type=row.content_type,
                    size_bytes=row.size_bytes,
                    llm_description=row.llm_description,
                    model_used=row.model_used,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve image analyses: {e}")

    async def update(self, item: ImageAnalysis) -> ImageAnalysis:
        """Update an existing image analysis record.

        Args:
            item: ImageAnalysis entity with updated values

        Returns:
            Updated ImageAnalysis entity

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If update fails
        """
        if item.id is None:
            raise DatabaseError("Cannot update image analysis without ID")

        try:
            # Check if item exists
            await self.get_by_id(item.id)

            stmt = (
                update(image_analysis_table)
                .where(image_analysis_table.c.id == item.id)
                .values(
                    filename=item.filename,
                    bucket=item.bucket,
                    object_key=item.object_key,
                    content_type=item.content_type,
                    size_bytes=item.size_bytes,
                    llm_description=item.llm_description,
                    model_used=item.model_used,
                    updated_at=item.updated_at,
                )
            )

            await self.session.execute(stmt)
            await self.session.commit()
            return item
        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to update image analysis: {e}")

    async def delete(self, item_id: int) -> None:
        """Delete an image analysis record.

        Args:
            item_id: ID of the item to delete

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If deletion fails
        """
        try:
            # Check if item exists
            await self.get_by_id(item_id)

            stmt = delete(image_analysis_table).where(
                image_analysis_table.c.id == item_id
            )
            await self.session.execute(stmt)
            await self.session.commit()
        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete image analysis: {e}")

    async def count(self) -> int:
        """Count total number of image analysis records.

        Returns:
            Total count of items

        Raises:
            DatabaseError: If count fails
        """
        try:
            from sqlalchemy import func

            stmt = select(func.count()).select_from(image_analysis_table)
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception as e:
            raise DatabaseError(f"Failed to count image analyses: {e}")


async def create_tables(engine) -> None:
    """Create database tables.

    This function creates the image_analysis table in the database.
    Should be called during application startup.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

