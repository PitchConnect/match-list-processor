"""
Enhanced retry utilities for robust error handling.

This module provides standardized retry mechanisms with exponential backoff,
circuit breaker patterns, and comprehensive error handling for external service calls.
"""

import asyncio
import functools
import secrets
import time
from typing import Any, Awaitable, Callable, List, Optional, Type, TypeVar

import requests

from .logging_config import get_logger, log_error_context

logger = get_logger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Exception that indicates an operation should be retried."""

    pass


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Args:
        error: Exception to evaluate

    Returns:
        True if the error is retryable, False otherwise
    """
    # Network and connection errors are retryable
    if isinstance(
        error,
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ReadTimeout,
            RetryableError,
        ),
    ):
        return True

    # HTTP errors with specific status codes are retryable
    if isinstance(error, requests.exceptions.HTTPError):
        if hasattr(error, "response") and error.response is not None:
            status_code = error.response.status_code
            # Retry on server errors and rate limiting
            if status_code in [429, 500, 502, 503, 504]:
                return True

    # JSON decode errors might be retryable (temporary server issues)
    if isinstance(error, requests.exceptions.JSONDecodeError):
        return True

    return False


def calculate_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> float:
    """
    Calculate delay for exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Exponential backoff factor
        jitter: Whether to add random jitter

    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (backoff_factor**attempt), max_delay)

    if jitter:
        # Add ±25% jitter to prevent thundering herd
        jitter_range = delay * 0.25
        # Use secrets.SystemRandom for better randomness
        random_gen = secrets.SystemRandom()
        delay += random_gen.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable:
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including initial)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff factor
        jitter: Whether to add random jitter to delays
        retryable_exceptions: List of exception types that should trigger retry
        on_retry: Callback function called on each retry attempt

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = any(
                            isinstance(e, exc_type) for exc_type in retryable_exceptions
                        )
                    else:
                        should_retry = is_retryable_error(e)

                    # If not retryable or last attempt, raise the exception
                    if not should_retry or attempt == max_attempts - 1:
                        log_error_context(
                            logger,
                            e,
                            context={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "retryable": should_retry,
                            },
                            operation=f"retry_attempt_{attempt + 1}",
                        )
                        raise

                    # Calculate delay and wait
                    delay = calculate_delay(attempt, base_delay, max_delay, backoff_factor, jitter)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error_type": type(e).__name__,
                        },
                    )

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")

                    time.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in retry logic")

        return wrapper

    return decorator


def async_retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Async version of retry_with_backoff decorator.

    Args:
        max_attempts: Maximum number of attempts (including initial)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff factor
        jitter: Whether to add random jitter to delays
        retryable_exceptions: List of exception types that should trigger retry
        on_retry: Callback function called on each retry attempt

    Returns:
        Decorated async function with retry logic
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)  # type: ignore

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    should_retry = False
                    if retryable_exceptions:
                        should_retry = any(
                            isinstance(e, exc_type) for exc_type in retryable_exceptions
                        )
                    else:
                        should_retry = is_retryable_error(e)

                    # If not retryable or last attempt, raise the exception
                    if not should_retry or attempt == max_attempts - 1:
                        log_error_context(
                            logger,
                            e,
                            context={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": max_attempts,
                                "retryable": should_retry,
                            },
                            operation=f"async_retry_attempt_{attempt + 1}",
                        )
                        raise

                    # Calculate delay and wait
                    delay = calculate_delay(attempt, base_delay, max_delay, backoff_factor, jitter)

                    logger.warning(
                        f"Async attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error_type": type(e).__name__,
                        },
                    )

                    # Call retry callback if provided
                    if on_retry:
                        try:
                            on_retry(attempt + 1, e)
                        except Exception as callback_error:
                            logger.warning(f"Async retry callback failed: {callback_error}")

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected error in async retry logic")

        return wrapper  # type: ignore

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failure threshold exceeded, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use circuit breaker as a decorator."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Call function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info(f"Circuit breaker for {func.__name__} transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerError(f"Circuit breaker for {func.__name__} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success(func.__name__)
            return result

        except self.expected_exception as e:
            self._on_failure(func.__name__, e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout  # type: ignore

    def _on_success(self, func_name: str) -> None:
        """Handle successful function call."""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info(f"Circuit breaker for {func_name} reset to CLOSED")

        self.failure_count = 0

    def _on_failure(self, func_name: str, error: Exception) -> None:
        """Handle failed function call."""
        self.failure_count += 1
        self.last_failure_time = time.time()  # type: ignore

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker for {func_name} opened after {self.failure_count} failures",
                extra={
                    "function": func_name,
                    "failure_count": self.failure_count,
                    "threshold": self.failure_threshold,
                    "error_type": type(error).__name__,
                },
            )
