"""Unit tests for PostgreSQL database service.

This module tests the database service client for connection management,
CRUD operations, and transaction handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.api.services.database import DatabaseService


class TestDatabaseService:
    """Test suite for DatabaseService."""

    @pytest.fixture
    def mock_engine(self) -> AsyncMock:
        """Create a mock async engine."""
        engine = AsyncMock(spec=AsyncEngine)
        return engine

    @pytest.fixture
    def db_service(self, mock_engine: AsyncMock) -> DatabaseService:
        """Create a DatabaseService instance with mock engine."""
        return DatabaseService(dsn="postgresql://test:test@localhost:5432/test")

    @pytest.mark.asyncio
    async def test_database_service_initialization(self) -> None:
        """Test that DatabaseService initializes with DSN."""
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        assert service.dsn == "postgresql://user:pass@host:5432/db"

    @pytest.mark.asyncio
    async def test_get_engine_creates_engine(self) -> None:
        """Test that get_engine creates an async engine."""
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        with patch("src.api.services.database.create_async_engine") as mock_create:
            mock_engine = AsyncMock(spec=AsyncEngine)
            mock_create.return_value = mock_engine
            
            engine = service.get_engine()
            
            assert engine == mock_engine
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_engine_raises_service_unavailable(self) -> None:
        from src.api.services.database import DatabaseService, ServiceUnavailableError
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        with patch("src.api.services.database.create_async_engine", side_effect=Exception("fail")):
            service._engine = None  # force new engine
            with pytest.raises(ServiceUnavailableError) as exc:
                service.get_engine()
            assert "Failed to create database engine" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_get_session_sqlalchemy_error(self) -> None:
        from src.api.services.database import DatabaseService, DatabaseError
        from sqlalchemy.exc import SQLAlchemyError
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        with patch.object(service, "get_engine") as mock_get_engine:
            mock_engine = AsyncMock()
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_sessionmaker = MagicMock()
            mock_sessionmaker.return_value.__aenter__.return_value = mock_session
            mock_sessionmaker.return_value.__aexit__.return_value = None
            mock_get_engine.return_value = mock_engine
            with patch("src.api.services.database.async_sessionmaker", return_value=mock_sessionmaker):
                # SQLAlchemyError triggers rollback and DatabaseError
                mock_session.commit.side_effect = SQLAlchemyError("fail")
                with pytest.raises(DatabaseError) as exc:
                    async with service.get_session():
                        pass
                assert "Database operation failed" in str(exc.value)
                mock_session.rollback.assert_awaited()
    
    @pytest.mark.asyncio
    async def test_get_session_non_sqlalchemy_error(self) -> None:
        from src.api.services.database import DatabaseService, DatabaseError
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        with patch.object(service, "get_engine") as mock_get_engine:
            mock_engine = AsyncMock()
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_sessionmaker = MagicMock()
            mock_sessionmaker.return_value.__aenter__.return_value = mock_session
            mock_sessionmaker.return_value.__aexit__.return_value = None
            mock_get_engine.return_value = mock_engine
            with patch("src.api.services.database.async_sessionmaker", return_value=mock_sessionmaker):
                # Non-SQLAlchemyError triggers rollback and DatabaseError
                mock_session.commit.side_effect = RuntimeError("generic fail")
                with pytest.raises(DatabaseError) as exc:
                    async with service.get_session():
                        pass
                assert "Unexpected error during database operation" in str(exc.value)
                mock_session.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        """Test health check returns True when database is accessible."""
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        
        with patch.object(service, "get_session") as mock_get_session:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.execute = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await service.health_check()
            
            assert result is True
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        """Test health check returns False when database is not accessible."""
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        
        with patch.object(service, "get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.side_effect = Exception("Connection failed")
            
            result = await service.health_check()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self) -> None:
        """Test that close disposes the engine."""
        service = DatabaseService(dsn="postgresql://user:pass@host:5432/db")
        
        # Create a mock engine and set it directly on the service
        mock_engine = AsyncMock(spec=AsyncEngine)
        service._engine = mock_engine
        
        await service.close()
        
        mock_engine.dispose.assert_called_once()
        assert service._engine is None

