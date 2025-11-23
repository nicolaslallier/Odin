"""Unit tests for cache service functionality.

This module tests the caching service including TTL expiration,
concurrent access, and cache operations.
"""

from __future__ import annotations

import asyncio

import pytest

from src.api.services.cache import CacheEntry, CacheService


@pytest.mark.unit
class TestCacheEntry:
    """Test cases for CacheEntry class."""

    def test_cache_entry_without_ttl(self) -> None:
        """Test that cache entry without TTL never expires."""
        entry = CacheEntry("test_value", ttl=None)
        assert entry.value == "test_value"
        assert not entry.is_expired()

    def test_cache_entry_with_ttl(self) -> None:
        """Test that cache entry with TTL tracks expiration."""
        entry = CacheEntry("test_value", ttl=1.0)
        assert not entry.is_expired()

    @pytest.mark.asyncio
    async def test_cache_entry_expires(self) -> None:
        """Test that cache entry expires after TTL."""
        entry = CacheEntry("test_value", ttl=0.1)
        assert not entry.is_expired()
        await asyncio.sleep(0.15)
        assert entry.is_expired()


@pytest.mark.unit
class TestCacheService:
    """Test cases for CacheService class."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self) -> None:
        """Test basic cache set and get operations."""
        cache = CacheService()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent_key(self) -> None:
        """Test that getting nonexistent key returns None."""
        cache = CacheService()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self) -> None:
        """Test cache delete operation."""
        cache = CacheService()
        await cache.set("key1", "value1")
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete_nonexistent(self) -> None:
        """Test that deleting nonexistent key doesn't raise error."""
        cache = CacheService()
        await cache.delete("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_cache_clear(self) -> None:
        """Test cache clear operation."""
        cache = CacheService()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self) -> None:
        """Test that cache entries expire after TTL."""
        cache = CacheService(default_ttl=0.1)
        await cache.set("key1", "value1")

        # Should be available immediately
        result = await cache.get("key1")
        assert result == "value1"

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_custom_ttl(self) -> None:
        """Test cache entry with custom TTL."""
        cache = CacheService(default_ttl=10.0)
        await cache.set("key1", "value1", ttl=0.1)

        # Wait for custom TTL expiration
        await asyncio.sleep(0.15)

        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=0.1)
        await cache.set("key2", "value2", ttl=10.0)

        # Wait for first entry to expire
        await asyncio.sleep(0.15)

        cleaned = await cache.cleanup_expired()
        assert cleaned == 1
        assert cache.size() == 1

    @pytest.mark.asyncio
    async def test_cache_size(self) -> None:
        """Test cache size tracking."""
        cache = CacheService()
        assert cache.size() == 0

        await cache.set("key1", "value1")
        assert cache.size() == 1

        await cache.set("key2", "value2")
        assert cache.size() == 2

        await cache.delete("key1")
        assert cache.size() == 1

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self) -> None:
        """Test that cache handles concurrent access correctly."""
        cache = CacheService()

        async def writer(key: str, value: str) -> None:
            await cache.set(key, value)

        async def reader(key: str) -> str | None:
            return await cache.get(key)

        # Concurrent writes
        await asyncio.gather(
            writer("key1", "value1"),
            writer("key2", "value2"),
            writer("key3", "value3"),
        )

        # Concurrent reads
        results = await asyncio.gather(
            reader("key1"),
            reader("key2"),
            reader("key3"),
        )

        assert results == ["value1", "value2", "value3"]

    @pytest.mark.asyncio
    async def test_cache_overwrites_existing_key(self) -> None:
        """Test that setting existing key overwrites value."""
        cache = CacheService()
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")

        result = await cache.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_cache_stores_different_types(self) -> None:
        """Test that cache can store different data types."""
        cache = CacheService()

        await cache.set("string", "text")
        await cache.set("int", 42)
        await cache.set("list", [1, 2, 3])
        await cache.set("dict", {"key": "value"})

        assert await cache.get("string") == "text"
        assert await cache.get("int") == 42
        assert await cache.get("list") == [1, 2, 3]
        assert await cache.get("dict") == {"key": "value"}

    @pytest.mark.asyncio
    async def test_cache_miss_logging(self) -> None:
        """Test that cache miss is handled correctly."""
        cache = CacheService()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expired_entry_removed_on_get(self) -> None:
        """Test that expired entry is removed when accessed."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=0.1)

        assert cache.size() == 1
        await asyncio.sleep(0.15)

        # Accessing expired entry should remove it
        result = await cache.get("key1")
        assert result is None
        assert cache.size() == 0

    @pytest.mark.asyncio
    async def test_cache_zero_ttl(self) -> None:
        """Test cache behavior with zero TTL (immediately expired)."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=0.0)

        # Should be immediately expired
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_negative_ttl(self) -> None:
        """Test cache behavior with negative TTL (immediately expired)."""
        cache = CacheService()
        await cache.set("key1", "value1", ttl=-1.0)

        # Should be immediately expired
        result = await cache.get("key1")
        assert result is None
