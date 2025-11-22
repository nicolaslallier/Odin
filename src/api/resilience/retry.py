"""Retry pattern implementation with exponential backoff.

This module provides retry logic with configurable backoff strategies.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Optional, TypeVar

from src.api.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    """Retry function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for function
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry
        **kwargs: Keyword arguments for function

    Returns:
        Function result

    Raises:
        Exception: If all retries exhausted

    Example:
        >>> result = await retry_with_backoff(
        ...     fetch_data,
        ...     url="http://api.example.com",
        ...     max_retries=3,
        ...     base_delay=1.0,
        ... )
    """
    last_exception: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                logger.info(f"Retry succeeded on attempt {attempt + 1}")
            return result

        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    f"All {max_retries + 1} attempts failed: {e}",
                    exc_info=True,
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base**attempt), max_delay)

            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...",
            )

            await asyncio.sleep(delay)

    # This should never be reached, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected retry loop exit")


class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter
        exceptions: Tuple of exceptions to retry on
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter
            exceptions: Tuple of exceptions to retry on
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions

    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        return await retry_with_backoff(
            func,
            *args,
            max_retries=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_base=self.exponential_base,
            jitter=self.jitter,
            exceptions=self.exceptions,
            **kwargs,
        )


# Pre-configured retry strategies
DEFAULT_RETRY = RetryConfig(max_retries=3, base_delay=1.0)
AGGRESSIVE_RETRY = RetryConfig(max_retries=5, base_delay=0.5, max_delay=30.0)
CONSERVATIVE_RETRY = RetryConfig(max_retries=2, base_delay=2.0, max_delay=120.0)

