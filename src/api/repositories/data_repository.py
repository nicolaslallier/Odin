"""Repository for data item persistence.

This module provides data access operations for data items using
the repository pattern to abstract database operations.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    delete,
    insert,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.domain.entities import DataItem
from src.api.exceptions import DatabaseError, ResourceNotFoundError

# Define the data_items table
metadata = MetaData()

data_items_table = Table(
    "data_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("description", String(1000), nullable=True),
    Column("data", JSON, nullable=False, default={}),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


class DataRepository:
    """Repository for data item persistence operations.

    This class provides CRUD operations for data items, following the
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

    async def create(self, item: DataItem) -> DataItem:
        """Create a new data item.

        Args:
            item: Data item entity to create

        Returns:
            Created data item with assigned ID

        Raises:
            DatabaseError: If creation fails
        """
        try:
            stmt = (
                insert(data_items_table)
                .values(
                    name=item.name,
                    description=item.description,
                    data=item.data,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                .returning(data_items_table.c.id)
            )

            result = await self.session.execute(stmt)
            item_id = result.scalar_one()
            item.id = item_id
            await self.session.commit()
            return item
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create data item: {e}")

    async def get_by_id(self, item_id: int) -> DataItem:
        """Get a data item by ID.

        Args:
            item_id: ID of the item to retrieve

        Returns:
            Data item entity

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If retrieval fails
        """
        try:
            stmt = select(data_items_table).where(data_items_table.c.id == item_id)
            result = await self.session.execute(stmt)
            row = result.first()

            if row is None:
                raise ResourceNotFoundError("Data item not found", {"id": item_id})

            return DataItem(
                id=row.id,
                name=row.name,
                description=row.description,
                data=row.data,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve data item: {e}")

    async def get_all(self) -> list[DataItem]:
        """Get all data items.

        Returns:
            List of data item entities

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            stmt = select(data_items_table).order_by(data_items_table.c.created_at.desc())
            result = await self.session.execute(stmt)
            rows = result.fetchall()

            return [
                DataItem(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    data=row.data,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve data items: {e}")

    async def update(self, item: DataItem) -> DataItem:
        """Update an existing data item.

        Args:
            item: Data item entity with updated values

        Returns:
            Updated data item entity

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If update fails
        """
        if item.id is None:
            raise DatabaseError("Cannot update item without ID")

        try:
            # Check if item exists
            await self.get_by_id(item.id)

            stmt = (
                update(data_items_table)
                .where(data_items_table.c.id == item.id)
                .values(
                    name=item.name,
                    description=item.description,
                    data=item.data,
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
            raise DatabaseError(f"Failed to update data item: {e}")

    async def delete(self, item_id: int) -> None:
        """Delete a data item.

        Args:
            item_id: ID of the item to delete

        Raises:
            ResourceNotFoundError: If item not found
            DatabaseError: If deletion fails
        """
        try:
            # Check if item exists
            await self.get_by_id(item_id)

            stmt = delete(data_items_table).where(data_items_table.c.id == item_id)
            await self.session.execute(stmt)
            await self.session.commit()
        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete data item: {e}")

    async def count(self) -> int:
        """Count total number of data items.

        Returns:
            Total count of items

        Raises:
            DatabaseError: If count fails
        """
        try:
            from sqlalchemy import func

            stmt = select(func.count()).select_from(data_items_table)
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception as e:
            raise DatabaseError(f"Failed to count data items: {e}")


async def create_tables(engine) -> None:
    """Create database tables.

    This function creates the data_items table in the database.
    Should be called during application startup.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
