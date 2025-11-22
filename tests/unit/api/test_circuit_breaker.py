"""Unit tests for circuit breaker functionality.

This module tests the circuit breaker pattern implementation including
state transitions, failure detection, and recovery logic.
"""

from __future__ import annotations

import asyncio

import pytest

from src.api.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.unit
class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""

    @pytest.mark.asyncio
    async def test_circuit_starts_closed(self) -> None:
        """Test that circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_keeps_circuit_closed(self) -> None:
        """Test that successful calls keep circuit in CLOSED state."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)

        async def successful_func() -> str:
            return "success"

        result = await breaker.call(successful_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold_failures(self) -> None:
        """Test that circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Execute failures up to threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self) -> None:
        """Test that OPEN circuit rejects calls without executing them."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Trigger circuit to open
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Next call should be rejected without executing function
        call_executed = False

        async def track_execution() -> None:
            nonlocal call_executed
            call_executed = True
            raise Exception("Should not execute")

        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(track_execution)

        assert not call_executed, "Function should not have been executed"

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open_after_timeout(self) -> None:
        """Test that circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.2)

        # Next call should transition to HALF_OPEN
        async def successful_func() -> str:
            return "success"

        result = await breaker.call(successful_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        """Test that successful call in HALF_OPEN state closes circuit."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        await asyncio.sleep(0.2)

        # Successful call should close circuit
        async def successful_func() -> str:
            return "recovered"

        result = await breaker.call(successful_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        """Test that failed call in HALF_OPEN state reopens circuit."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.1)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        await asyncio.sleep(0.2)

        # Failed call should reopen circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reset_closes_circuit(self) -> None:
        """Test that reset closes circuit regardless of state."""
        breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)

        async def failing_func() -> None:
            raise Exception("Test failure")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Reset should close circuit
        await breaker.reset()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_with_custom_exception_type(self) -> None:
        """Test circuit breaker with custom exception type."""
        breaker = CircuitBreaker(
            failure_threshold=2, timeout=1.0, expected_exception=ValueError
        )

        async def value_error_func() -> None:
            raise ValueError("Test error")

        async def runtime_error_func() -> None:
            raise RuntimeError("Different error")

        # ValueError should trigger circuit
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)

        assert breaker.state == CircuitState.OPEN

        # RuntimeError should not be caught by circuit breaker
        with pytest.raises(RuntimeError):
            await breaker.call(runtime_error_func)

    @pytest.mark.asyncio
    async def test_concurrent_calls_through_circuit(self) -> None:
        """Test that circuit breaker handles concurrent calls correctly."""
        breaker = CircuitBreaker(failure_threshold=5, timeout=1.0)
        call_count = 0

        async def counting_func() -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count

        # Execute concurrent calls
        tasks = [breaker.call(counting_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert breaker.state == CircuitState.CLOSED
        assert call_count == 10

    @pytest.mark.asyncio
    async def test_failure_count_resets_on_success(self) -> None:
        """Test that failure count resets on successful call."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=1.0)

        async def failing_func() -> None:
            raise Exception("Test failure")

        async def successful_func() -> str:
            return "success"

        # Fail twice (below threshold)
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.CLOSED

        # Success should reset count
        await breaker.call(successful_func)

        # Can fail again without opening (count was reset)
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.CLOSED

