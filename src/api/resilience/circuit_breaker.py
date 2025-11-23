"""Circuit breaker pattern implementation.

This module provides a circuit breaker to prevent cascading failures
by temporarily stopping calls to failing services.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from src.api.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message)
        self.context = context or {}


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures.

    The circuit breaker monitors failures and opens the circuit after a threshold
    is reached, preventing further calls to the failing service. After a timeout,
    it enters half-open state to test if the service recovered.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before trying again (half-open state)
        expected_exception: Exception type to count as failure
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening
            timeout: Seconds to wait in open state before half-open
            expected_exception: Exception type that triggers circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state.

        Returns:
            Current circuit state
        """
        return self._state

    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Call function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: If function raises an exception
        """
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if (
                    self._last_failure_time
                    and (time.time() - self._last_failure_time) > self.timeout
                ):
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self._state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        "Circuit breaker is OPEN",
                        {
                            "failure_count": self._failure_count,
                            "last_failure": self._last_failure_time,
                        },
                    )

        # Try to execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker closing after successful test")
                self._state = CircuitState.CLOSED

            self._failure_count = 0
            self._last_failure_time = None

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit breaker opening after failed test")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker opening after {self._failure_count} failures")
                self._state = CircuitState.OPEN

    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._lock:
            logger.info("Circuit breaker manually reset")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None


class CircuitBreakerManager:
    """Manager for multiple circuit breakers.

    This class manages circuit breakers for different services,
    creating them on demand and providing access by name.
    """

    def __init__(self) -> None:
        """Initialize circuit breaker manager."""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
    ) -> CircuitBreaker:
        """Get or create circuit breaker by name.

        Args:
            name: Circuit breaker name (e.g., 'ollama', 'vault')
            failure_threshold: Number of failures before opening
            timeout: Seconds to wait before retry

        Returns:
            Circuit breaker instance
        """
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    failure_threshold=failure_threshold,
                    timeout=timeout,
                )
                logger.info(f"Created circuit breaker: {name}")
            return self._breakers[name]

    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()
            logger.info("Reset all circuit breakers")

    def get_states(self) -> dict[str, str]:
        """Get states of all circuit breakers.

        Returns:
            Dictionary mapping breaker name to state
        """
        return {name: breaker.state.value for name, breaker in self._breakers.items()}


# Global circuit breaker manager (singleton)
_manager_instance: CircuitBreakerManager | None = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager.

    Returns:
        Global circuit breaker manager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = CircuitBreakerManager()
    return _manager_instance
