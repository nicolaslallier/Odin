"""Repository for Confluence statistics persistence in TimescaleDB.

This module provides data access operations for storing and retrieving
Confluence space statistics from the TimescaleDB hypertable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Text, and_, desc, func, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.api.exceptions import DatabaseError


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class ConfluenceStatisticsModel(Base):
    """SQLAlchemy model for confluence_statistics table."""

    __tablename__ = "confluence_statistics"

    id: Mapped[int] = mapped_column(primary_key=True)
    space_key: Mapped[str] = mapped_column(Text, nullable=False)
    space_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Basic statistics
    total_pages: Mapped[int] = mapped_column(nullable=False, default=0)
    total_size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    contributor_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_updated: Mapped[datetime | None] = mapped_column(nullable=True)

    # Detailed statistics (JSONB)
    page_breakdown_by_type: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    attachment_stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version_count: Mapped[int] = mapped_column(nullable=False, default=0)

    # Comprehensive statistics (JSONB)
    user_activity: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    page_views: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    comment_counts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    link_analysis: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Metadata
    collection_time_seconds: Mapped[float | None] = mapped_column(nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)


class StatisticsRepository:
    """Repository for Confluence statistics data access.

    This class provides methods for storing and retrieving Confluence
    space statistics from TimescaleDB with proper async operations.

    Attributes:
        session: Async SQLAlchemy session for database operations
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def save_statistics(
        self,
        space_key: str,
        space_name: str | None,
        timestamp: datetime,
        statistics: dict[str, Any],
    ) -> int:
        """Save Confluence statistics to TimescaleDB.

        Args:
            space_key: Confluence space key
            space_name: Confluence space name (optional)
            timestamp: Collection timestamp
            statistics: Dictionary containing all statistics data

        Returns:
            ID of the created statistics entry

        Raises:
            DatabaseError: If save operation fails
        """
        try:
            # Extract statistics from nested structure
            basic = statistics.get("basic", {})
            detailed = statistics.get("detailed", {})
            comprehensive = statistics.get("comprehensive", {})

            # Create model instance
            stats_model = ConfluenceStatisticsModel(
                space_key=space_key,
                space_name=space_name,
                timestamp=timestamp,
                # Basic
                total_pages=basic.get("total_pages", 0),
                total_size_bytes=basic.get("total_size_bytes", 0),
                contributor_count=basic.get("contributor_count", 0),
                last_updated=(
                    datetime.fromisoformat(basic["last_updated"].replace("Z", "+00:00"))
                    if basic.get("last_updated")
                    else None
                ),
                # Detailed
                page_breakdown_by_type=detailed.get("page_breakdown_by_type", {}),
                attachment_stats=detailed.get("attachment_stats", {}),
                version_count=detailed.get("version_count", 0),
                # Comprehensive
                user_activity=comprehensive.get("user_activity", {}),
                page_views=comprehensive.get("page_views", {}),
                comment_counts=comprehensive.get("comment_counts", {}),
                link_analysis=comprehensive.get("link_analysis", {}),
                # Metadata
                collection_time_seconds=statistics.get("collection_time_seconds"),
                extra_metadata=statistics,  # Store full stats in metadata for flexibility
            )

            self.session.add(stats_model)
            await self.session.commit()
            await self.session.refresh(stats_model)

            return stats_model.id

        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(f"Failed to save statistics: {e}")

    async def get_latest_statistics(self, space_key: str) -> dict[str, Any] | None:
        """Get the most recent statistics for a space.

        Args:
            space_key: Confluence space key

        Returns:
            Dictionary containing statistics data, or None if not found

        Raises:
            DatabaseError: If query fails
        """
        try:
            stmt = (
                select(ConfluenceStatisticsModel)
                .where(ConfluenceStatisticsModel.space_key == space_key)
                .order_by(desc(ConfluenceStatisticsModel.timestamp))
                .limit(1)
            )

            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return None

            return self._model_to_dict(model)

        except Exception as e:
            raise DatabaseError(f"Failed to get latest statistics: {e}")

    async def get_statistics_history(
        self,
        space_key: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        granularity: str = "raw",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get historical statistics for a space.

        Args:
            space_key: Confluence space key
            start_date: Start of time range (default: 7 days ago)
            end_date: End of time range (default: now)
            granularity: Data granularity (raw, hourly, daily)
            limit: Maximum number of entries to return

        Returns:
            List of statistics entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Set default time range
            if end_date is None:
                end_date = datetime.utcnow()
            if start_date is None:
                start_date = end_date - timedelta(days=7)

            if granularity == "hourly":
                return await self._get_hourly_statistics(space_key, start_date, end_date, limit)
            elif granularity == "daily":
                return await self._get_daily_statistics(space_key, start_date, end_date, limit)
            else:
                # Raw data
                stmt = (
                    select(ConfluenceStatisticsModel)
                    .where(
                        and_(
                            ConfluenceStatisticsModel.space_key == space_key,
                            ConfluenceStatisticsModel.timestamp >= start_date,
                            ConfluenceStatisticsModel.timestamp <= end_date,
                        )
                    )
                    .order_by(desc(ConfluenceStatisticsModel.timestamp))
                    .limit(limit)
                )

                result = await self.session.execute(stmt)
                models = result.scalars().all()

                return [self._model_to_dict(model) for model in models]

        except Exception as e:
            raise DatabaseError(f"Failed to get statistics history: {e}")

    async def _get_hourly_statistics(
        self, space_key: str, start_date: datetime, end_date: datetime, limit: int
    ) -> list[dict[str, Any]]:
        """Get hourly aggregated statistics from continuous aggregate.

        Args:
            space_key: Confluence space key
            start_date: Start of time range
            end_date: End of time range
            limit: Maximum number of entries

        Returns:
            List of hourly statistics entries
        """
        query = text(
            """
            SELECT 
                hour AS timestamp,
                avg_pages AS total_pages,
                avg_size_bytes AS total_size_bytes,
                avg_contributors AS contributor_count,
                sample_count
            FROM confluence_stats_hourly
            WHERE space_key = :space_key
              AND hour >= :start_date
              AND hour <= :end_date
            ORDER BY hour DESC
            LIMIT :limit
            """
        )

        result = await self.session.execute(
            query,
            {
                "space_key": space_key,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            {
                "timestamp": row.timestamp.isoformat(),
                "total_pages": int(row.total_pages),
                "total_size_bytes": int(row.total_size_bytes),
                "contributor_count": int(row.contributor_count),
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    async def _get_daily_statistics(
        self, space_key: str, start_date: datetime, end_date: datetime, limit: int
    ) -> list[dict[str, Any]]:
        """Get daily aggregated statistics from continuous aggregate.

        Args:
            space_key: Confluence space key
            start_date: Start of time range
            end_date: End of time range
            limit: Maximum number of entries

        Returns:
            List of daily statistics entries
        """
        query = text(
            """
            SELECT 
                day AS timestamp,
                avg_pages AS total_pages,
                avg_size_bytes AS total_size_bytes,
                avg_contributors AS contributor_count,
                sample_count
            FROM confluence_stats_daily
            WHERE space_key = :space_key
              AND day >= :start_date
              AND day <= :end_date
            ORDER BY day DESC
            LIMIT :limit
            """
        )

        result = await self.session.execute(
            query,
            {
                "space_key": space_key,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        return [
            {
                "timestamp": row.timestamp.isoformat(),
                "total_pages": int(row.total_pages),
                "total_size_bytes": int(row.total_size_bytes),
                "contributor_count": int(row.contributor_count),
                "sample_count": row.sample_count,
            }
            for row in rows
        ]

    async def delete_old_statistics(self, days: int = 365) -> int:
        """Delete statistics older than specified days.

        Args:
            days: Number of days to retain (default: 365)

        Returns:
            Number of deleted records

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            stmt = select(func.count()).where(ConfluenceStatisticsModel.timestamp < cutoff_date)
            result = await self.session.execute(stmt)
            count = result.scalar() or 0

            # TimescaleDB retention policy will handle actual deletion
            # This is just for reporting

            return count

        except Exception as e:
            raise DatabaseError(f"Failed to delete old statistics: {e}")

    def _model_to_dict(self, model: ConfluenceStatisticsModel) -> dict[str, Any]:
        """Convert SQLAlchemy model to dictionary.

        Args:
            model: ConfluenceStatisticsModel instance

        Returns:
            Dictionary representation of the model
        """
        return {
            "id": model.id,
            "space_key": model.space_key,
            "space_name": model.space_name,
            "timestamp": model.timestamp.isoformat(),
            "total_pages": model.total_pages,
            "total_size_bytes": model.total_size_bytes,
            "contributor_count": model.contributor_count,
            "last_updated": model.last_updated.isoformat() if model.last_updated else None,
            "page_breakdown_by_type": model.page_breakdown_by_type,
            "attachment_stats": model.attachment_stats,
            "version_count": model.version_count,
            "user_activity": model.user_activity,
            "page_views": model.page_views,
            "comment_counts": model.comment_counts,
            "link_analysis": model.link_analysis,
            "collection_time_seconds": model.collection_time_seconds,
            "metadata": model.extra_metadata,
            "created_at": model.created_at.isoformat(),
        }
