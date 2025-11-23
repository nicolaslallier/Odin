"""Repository for query history persistence.

This module provides data access operations for SQL query execution history
using the repository pattern to abstract database operations.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.exceptions import DatabaseError, ResourceNotFoundError

# Define the query_history table
metadata = MetaData()

query_history_table = Table(
    "query_history",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("query_text", String, nullable=False),
    Column("executed_at", DateTime, nullable=False),
    Column("execution_time_ms", Float, nullable=True),
    Column("status", String(20), nullable=False),  # 'success' or 'error'
    Column("row_count", Integer, nullable=True),
    Column("error_message", String, nullable=True),
)


class QueryHistory:
    """Entity representing a query execution history record.

    Attributes:
        id: Unique identifier for the record
        query_text: The SQL query that was executed
        executed_at: Timestamp when the query was executed
        execution_time_ms: Time taken to execute the query in milliseconds
        status: Execution status ('success' or 'error')
        row_count: Number of rows affected/returned
        error_message: Error message if query failed
    """

    def __init__(
        self,
        id: int | None,
        query_text: str,
        executed_at: datetime,
        execution_time_ms: float | None,
        status: str,
        row_count: int | None,
        error_message: str | None,
    ) -> None:
        """Initialize query history entity.

        Args:
            id: Unique identifier (None for new records)
            query_text: SQL query text
            executed_at: Execution timestamp
            execution_time_ms: Execution time in milliseconds
            status: Status ('success' or 'error')
            row_count: Number of rows affected/returned
            error_message: Error message if failed
        """
        self.id = id
        self.query_text = query_text
        self.executed_at = executed_at
        self.execution_time_ms = execution_time_ms
        self.status = status
        self.row_count = row_count
        self.error_message = error_message


class QueryHistoryRepository:
    """Repository for query history persistence operations.

    This class provides CRUD operations for query execution history,
    following the Repository pattern to abstract database operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, query_history: QueryHistory) -> QueryHistory:
        """Create a new query history record.

        Args:
            query_history: QueryHistory entity to create

        Returns:
            Created query history with assigned ID

        Raises:
            DatabaseError: If creation fails
        """
        try:
            stmt = (
                insert(query_history_table)
                .values(
                    query_text=query_history.query_text,
                    executed_at=query_history.executed_at,
                    execution_time_ms=query_history.execution_time_ms,
                    status=query_history.status,
                    row_count=query_history.row_count,
                    error_message=query_history.error_message,
                )
                .returning(query_history_table.c.id)
            )

            result = await self.session.execute(stmt)
            query_id = result.scalar_one()
            query_history.id = query_id
            await self.session.commit()
            return query_history
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to create query history: {e}")

    async def get_by_id(self, query_id: int) -> QueryHistory:
        """Get a query history record by ID.

        Args:
            query_id: ID of the query history record

        Returns:
            QueryHistory entity

        Raises:
            ResourceNotFoundError: If record not found
            DatabaseError: If retrieval fails
        """
        try:
            stmt = select(query_history_table).where(query_history_table.c.id == query_id)
            result = await self.session.execute(stmt)
            row = result.first()

            if row is None:
                raise ResourceNotFoundError("Query history not found", {"id": query_id})

            return QueryHistory(
                id=row.id,
                query_text=row.query_text,
                executed_at=row.executed_at,
                execution_time_ms=row.execution_time_ms,
                status=row.status,
                row_count=row.row_count,
                error_message=row.error_message,
            )
        except ResourceNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve query history: {e}")

    async def get_recent(self, limit: int = 50) -> list[QueryHistory]:
        """Get recent query history records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of QueryHistory entities, most recent first

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            stmt = (
                select(query_history_table)
                .order_by(query_history_table.c.executed_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            rows = result.fetchall()

            return [
                QueryHistory(
                    id=row.id,
                    query_text=row.query_text,
                    executed_at=row.executed_at,
                    execution_time_ms=row.execution_time_ms,
                    status=row.status,
                    row_count=row.row_count,
                    error_message=row.error_message,
                )
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve recent query history: {e}")

    async def search_queries(self, search_term: str, limit: int = 50) -> list[QueryHistory]:
        """Search query history by query text.

        Args:
            search_term: Term to search for in query text
            limit: Maximum number of records to return

        Returns:
            List of matching QueryHistory entities

        Raises:
            DatabaseError: If search fails
        """
        try:
            stmt = (
                select(query_history_table)
                .where(query_history_table.c.query_text.ilike(f"%{search_term}%"))
                .order_by(query_history_table.c.executed_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            rows = result.fetchall()

            return [
                QueryHistory(
                    id=row.id,
                    query_text=row.query_text,
                    executed_at=row.executed_at,
                    execution_time_ms=row.execution_time_ms,
                    status=row.status,
                    row_count=row.row_count,
                    error_message=row.error_message,
                )
                for row in rows
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to search query history: {e}")

    async def delete(self, query_id: int) -> None:
        """Delete a query history record.

        Args:
            query_id: ID of the record to delete

        Raises:
            ResourceNotFoundError: If record not found
            DatabaseError: If deletion fails
        """
        try:
            # Check if record exists
            await self.get_by_id(query_id)

            stmt = delete(query_history_table).where(query_history_table.c.id == query_id)
            await self.session.execute(stmt)
            await self.session.commit()
        except ResourceNotFoundError:
            raise
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete query history: {e}")

    async def count(self) -> int:
        """Count total number of query history records.

        Returns:
            Total count of records

        Raises:
            DatabaseError: If count fails
        """
        try:
            stmt = select(func.count()).select_from(query_history_table)
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except Exception as e:
            raise DatabaseError(f"Failed to count query history: {e}")

    async def delete_old_records(self, days: int = 30) -> int:
        """Delete query history records older than specified days.

        Args:
            days: Number of days to keep (delete older records)

        Returns:
            Number of records deleted

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            stmt = delete(query_history_table).where(
                query_history_table.c.executed_at < cutoff_date
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to delete old query history: {e}")


async def create_tables(engine) -> None:
    """Create database tables.

    This function creates the query_history table in the database.
    Should be called during application startup.

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
