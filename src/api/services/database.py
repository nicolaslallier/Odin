"""PostgreSQL database service client.

This module provides database connectivity and operations using SQLAlchemy
with async support for the API service.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.api.exceptions import DatabaseError, ServiceUnavailableError


class DatabaseService:
    """PostgreSQL database service client.

    This class provides connection management and database operations
    using SQLAlchemy's async engine.

    Attributes:
        dsn: PostgreSQL connection string
    """

    def __init__(self, dsn: str) -> None:
        """Initialize database service with connection string.

        Args:
            dsn: PostgreSQL connection string (e.g., postgresql://user:pass@host:5432/db)
        """
        self.dsn = dsn
        self._engine: Optional[AsyncEngine] = None

    def get_engine(self) -> AsyncEngine:
        """Get or create the async database engine.

        Returns:
            SQLAlchemy async engine instance

        Raises:
            ServiceUnavailableError: If engine creation fails
        """
        if self._engine is None:
            try:
                self._engine = create_async_engine(
                    self.dsn,
                    echo=False,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    pool_recycle=3600,  # Recycle connections after 1 hour
                )
            except Exception as e:
                raise ServiceUnavailableError(f"Failed to create database engine: {e}")
        return self._engine

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session context manager.

        Yields:
            AsyncSession instance for database operations

        Raises:
            DatabaseError: If session operations fail

        Example:
            >>> async with service.get_session() as session:
            >>>     result = await session.execute(text("SELECT 1"))
        """
        engine = self.get_engine()
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                raise DatabaseError(f"Database operation failed: {e}")
            except Exception as e:
                await session.rollback()
                raise DatabaseError(f"Unexpected error during database operation: {e}")

    async def health_check(self) -> bool:
        """Check if database connection is healthy.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the database engine and dispose of connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None

