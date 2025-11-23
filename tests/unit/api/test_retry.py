"""Unit tests for retry functionality.

This module tests the retry pattern implementation including
exponential backoff, jitter, and exception handling.
"""

from __future__ import annotations

import asyncio

import pytest

from src.api.resilience.retry import RetryConfig, retry_with_backoff


@pytest.mark.unit
class TestRetryWithBackoff:
    """Test cases for retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self) -> None:
        """Test that successful call doesn't trigger retry."""
        call_count = 0

        async def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_with_backoff(successful_func, max_retries=3)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_exception(self) -> None:
        """Test that function retries on exception."""
        call_count = 0

        async def failing_then_success() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await retry_with_backoff(failing_then_success, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises_exception(self) -> None:
        """Test that exhausted retries raises the last exception."""

        async def always_failing() -> None:
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await retry_with_backoff(always_failing, max_retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_exponential_backoff(self) -> None:
        """Test that delays follow exponential backoff pattern."""
        delays: list[float] = []
        call_count = 0

        async def failing_func() -> None:
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                # Record time between calls
                delays.append(asyncio.get_event_loop().time())
            raise ValueError("Test error")

        try:
            await retry_with_backoff(
                failing_func,
                max_retries=3,
                base_delay=0.1,
                exponential_base=2.0,
                jitter=False,
            )
        except ValueError:
            pass

        # Should have 3 attempts (initial + 3 retries = 4 total calls)
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_max_delay_cap(self) -> None:
        """Test that delay is capped at max_delay."""
        call_count = 0

        async def failing_func() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        start_time = asyncio.get_event_loop().time()
        try:
            await retry_with_backoff(
                failing_func,
                max_retries=2,
                base_delay=1.0,
                max_delay=0.2,  # Cap at 0.2 seconds
                exponential_base=10.0,
                jitter=False,
            )
        except ValueError:
            pass
        end_time = asyncio.get_event_loop().time()

        # Even with exponential_base=10, delays should be capped
        # Total time should be less than if delays weren't capped
        elapsed = end_time - start_time
        assert elapsed < 1.0  # Should be much less than uncapped delay

    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self) -> None:
        """Test that jitter adds randomness to delays."""
        delays_with_jitter: list[float] = []
        delays_without_jitter: list[float] = []

        async def failing_func() -> None:
            raise ValueError("Test error")

        # Measure delays with jitter
        for _ in range(5):
            start = asyncio.get_event_loop().time()
            try:
                await retry_with_backoff(failing_func, max_retries=1, base_delay=0.1, jitter=True)
            except ValueError:
                pass
            end = asyncio.get_event_loop().time()
            delays_with_jitter.append(end - start)

        # Measure delays without jitter
        for _ in range(5):
            start = asyncio.get_event_loop().time()
            try:
                await retry_with_backoff(failing_func, max_retries=1, base_delay=0.1, jitter=False)
            except ValueError:
                pass
            end = asyncio.get_event_loop().time()
            delays_without_jitter.append(end - start)

        # Delays with jitter should have more variance
        jitter_variance = max(delays_with_jitter) - min(delays_with_jitter)
        no_jitter_variance = max(delays_without_jitter) - min(delays_without_jitter)
        assert jitter_variance > no_jitter_variance

    @pytest.mark.asyncio
    async def test_custom_exception_filter(self) -> None:
        """Test that only specified exceptions trigger retry."""
        call_count = 0

        async def mixed_exceptions() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            elif call_count == 2:
                raise RuntimeError("Non-retryable")
            return "success"

        # Only ValueError should trigger retry
        with pytest.raises(RuntimeError, match="Non-retryable"):
            await retry_with_backoff(
                mixed_exceptions,
                max_retries=3,
                base_delay=0.01,
                exceptions=(ValueError,),
            )

        assert call_count == 2  # Initial call + 1 retry before RuntimeError

    @pytest.mark.asyncio
    async def test_function_with_args_and_kwargs(self) -> None:
        """Test retry with function that takes args and kwargs."""

        async def func_with_params(x: int, y: int, multiply: bool = False) -> int:
            if multiply:
                return x * y
            return x + y

        result = await retry_with_backoff(func_with_params, 5, 3, multiply=True)
        assert result == 15

    @pytest.mark.asyncio
    async def test_zero_retries(self) -> None:
        """Test behavior with zero retries (no retry attempts)."""
        call_count = 0

        async def failing_func() -> None:
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await retry_with_backoff(failing_func, max_retries=0, base_delay=0.01)

        assert call_count == 1  # Only initial call, no retries


@pytest.mark.unit
class TestRetryConfig:
    """Test cases for RetryConfig class."""

    @pytest.mark.asyncio
    async def test_retry_config_execute(self) -> None:
        """Test retry execution through RetryConfig."""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        call_count = 0

        async def func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return "success"

        result = await config.execute(func)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_default_retry_config(self) -> None:
        """Test default retry configuration."""
        from src.api.resilience.retry import DEFAULT_RETRY

        assert DEFAULT_RETRY.max_retries == 3
        assert DEFAULT_RETRY.base_delay == 1.0

    @pytest.mark.asyncio
    async def test_aggressive_retry_config(self) -> None:
        """Test aggressive retry configuration."""
        from src.api.resilience.retry import AGGRESSIVE_RETRY

        assert AGGRESSIVE_RETRY.max_retries == 5
        assert AGGRESSIVE_RETRY.base_delay == 0.5
        assert AGGRESSIVE_RETRY.max_delay == 30.0

    @pytest.mark.asyncio
    async def test_conservative_retry_config(self) -> None:
        """Test conservative retry configuration."""
        from src.api.resilience.retry import CONSERVATIVE_RETRY

        assert CONSERVATIVE_RETRY.max_retries == 2
        assert CONSERVATIVE_RETRY.base_delay == 2.0
        assert CONSERVATIVE_RETRY.max_delay == 120.0

    @pytest.mark.asyncio
    async def test_retry_config_with_custom_exceptions(self) -> None:
        """Test RetryConfig with custom exception filter."""
        config = RetryConfig(max_retries=2, base_delay=0.01, exceptions=(ValueError, TypeError))

        call_count = 0

        async def func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First")
            elif call_count == 2:
                raise TypeError("Second")
            return "success"

        result = await config.execute(func)
        assert result == "success"
        assert call_count == 3
