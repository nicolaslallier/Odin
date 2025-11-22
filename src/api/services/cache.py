"""In-memory cache service with TTL support.

This module provides a simple in-memory cache service with time-to-live (TTL)
support. For production, consider using Redis or Memcached.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from src.api.logging_config import get_logger

logger = get_logger(__name__)


class CacheEntry:
    """Cache entry with value and expiration time.

    Attributes:
        value: Cached value
        expires_at: Timestamp when entry expires (None for no expiration)
    """

    def __init__(self, value: Any, ttl: Optional[float] = None) -> None:
        """Initialize cache entry.

        Args:
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
        """
        self.value = value
        self.expires_at = time.time() + ttl if ttl is not None else None

    def is_expired(self) -> bool:
        """Check if cache entry has expired.

        Returns:
            True if expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CacheService:
    """Simple in-memory cache service with TTL support.

    This service provides basic caching functionality with automatic expiration.
    For production use, consider using Redis with redis-py or aioredis.

    Attributes:
        default_ttl: Default TTL in seconds for cached entries
    """

    def __init__(self, default_ttl: float = 300.0) -> None:
        """Initialize cache service.

        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                logger.debug(f"Cache miss: {key}")
                return None

            if entry.is_expired():
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
                return None

            logger.debug(f"Cache hit: {key}")
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None uses default_ttl)
        """
        async with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            self._cache[key] = CacheEntry(value, ttl)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            return len(expired_keys)

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of entries in cache
        """
        return len(self._cache)


# Global cache instance (singleton)
_cache_instance: Optional[CacheService] = None


def get_cache() -> CacheService:
    """Get global cache instance.

    Returns:
        Global cache service instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance

