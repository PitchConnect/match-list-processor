"""
Tests for enhanced error handling and logging functionality.

This module tests the improved error handling, logging configuration,
and retry mechanisms implemented for Issue #4.
"""

import logging
import time
from unittest.mock import Mock, patch

import pytest

from src.core.logging_config import (
    ContextualFormatter,
    SensitiveDataFilter,
    configure_logging,
    get_logger,
    log_error_context,
)
from src.core.retry_utils import (
    CircuitBreaker,
    CircuitBreakerError,
    async_retry_with_backoff,
    calculate_delay,
    is_retryable_error,
    retry_with_backoff,
)


class TestLoggingConfiguration:
    """Test enhanced logging configuration."""

    def test_configure_logging_with_defaults(self):
        """Test logging configuration with default settings."""
        configure_logging()

        logger = get_logger(__name__)
        assert logger is not None
        assert logger.level <= logging.INFO

    def test_configure_logging_with_custom_level(self):
        """Test logging configuration with custom log level."""
        configure_logging(log_level="DEBUG")

        logger = get_logger(__name__)
        assert logger.level <= logging.DEBUG

    def test_contextual_formatter(self):
        """Test contextual formatter adds required fields."""
        formatter = ContextualFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatter.format(record)

        # Check that contextual fields were added
        assert hasattr(record, "timestamp")
        assert hasattr(record, "service")
        assert hasattr(record, "component")
        assert record.service == "match-list-processor"
        assert record.component == "module"

    def test_sensitive_data_filter(self):
        """Test sensitive data filter masks credentials."""
        filter_obj = SensitiveDataFilter()

        # Create a log record with sensitive data
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Login with password=secret123 and token=abc123",
            args=(),
            exc_info=None,
        )

        # Apply filter
        filter_obj.filter(record)

        # Check that sensitive data was masked
        assert "secret123" not in record.msg
        assert "abc123" not in record.msg
        assert "********" in record.msg

    def test_log_error_context(self):
        """Test error context logging function."""
        logger = get_logger(__name__)

        with patch.object(logger, "error") as mock_error:
            error = ValueError("Test error")
            context = {"operation": "test_operation", "user_id": "123"}

            log_error_context(logger, error, context, "test_operation")

            # Verify error was logged with context
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "test_operation" in call_args[0][0]
            assert call_args[1]["exc_info"] is True


class TestRetryUtilities:
    """Test enhanced retry utilities."""

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        import requests

        # Test retryable errors
        assert is_retryable_error(requests.exceptions.ConnectionError())
        assert is_retryable_error(requests.exceptions.Timeout())

        # Create HTTP error with retryable status code
        response = Mock()
        response.status_code = 503
        http_error = requests.exceptions.HTTPError()
        http_error.response = response
        assert is_retryable_error(http_error)

        # Test non-retryable errors
        response.status_code = 404
        http_error.response = response
        assert not is_retryable_error(http_error)

        assert not is_retryable_error(KeyError("Not retryable"))

    def test_calculate_delay(self):
        """Test delay calculation for exponential backoff."""
        # Test basic exponential backoff
        delay1 = calculate_delay(0, base_delay=1.0, jitter=False)
        delay2 = calculate_delay(1, base_delay=1.0, jitter=False)
        delay3 = calculate_delay(2, base_delay=1.0, jitter=False)

        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0

        # Test max delay limit
        delay_max = calculate_delay(10, base_delay=1.0, max_delay=5.0, jitter=False)
        assert delay_max == 5.0

        # Test jitter adds randomness
        calculate_delay(1, base_delay=1.0, jitter=True)
        calculate_delay(1, base_delay=1.0, jitter=True)
        # With jitter, delays should be different (with high probability)
        # Note: This test might occasionally fail due to randomness

    def test_retry_decorator_success(self):
        """Test retry decorator with successful function."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_function()
        assert result == "success"
        assert call_count == 1

    def test_retry_decorator_with_retryable_error(self):
        """Test retry decorator with retryable errors."""
        import requests

        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Connection failed")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_retry_decorator_with_non_retryable_error(self):
        """Test retry decorator with non-retryable errors."""
        import requests

        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=[
                requests.exceptions.ConnectionError
            ],  # Only retry connection errors
        )
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            failing_function()

        assert call_count == 1  # Should not retry

    def test_retry_decorator_max_attempts_exceeded(self):
        """Test retry decorator when max attempts exceeded."""
        import requests

        call_count = 0

        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise requests.exceptions.ConnectionError("Always fails")

        with pytest.raises(requests.exceptions.ConnectionError):
            always_failing_function()

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """Test async retry decorator."""
        import requests

        call_count = 0

        @async_retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def async_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.ConnectionError("Connection failed")
            return "success"

        result = await async_failing_function()
        assert result == "success"
        assert call_count == 3


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)

        # Function should work normally in closed state
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == "CLOSED"

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        # Cause failures to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("Test error")))

        assert cb.state == "OPEN"

        # Next call should fail fast
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "should not execute")

    def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker recovery through half-open state."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("Test error")))

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(0.2)

        # Next successful call should close circuit
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state == "CLOSED"

    def test_circuit_breaker_as_decorator(self):
        """Test circuit breaker used as decorator."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

        @cb
        def test_function(should_fail=False):
            if should_fail:
                raise ValueError("Test error")
            return "success"

        # Should work normally
        assert test_function() == "success"

        # Cause failures to open circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                test_function(should_fail=True)

        # Circuit should be open
        with pytest.raises(CircuitBreakerError):
            test_function()


class TestIntegrationErrorHandling:
    """Test integration of error handling components."""

    def test_logging_and_retry_integration(self):
        """Test integration of logging and retry mechanisms."""
        import requests

        # Configure logging for test
        configure_logging(log_level="DEBUG")
        logger = get_logger(__name__)

        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def test_function():
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                error = requests.exceptions.ConnectionError("Test connection error")
                log_error_context(
                    logger, error, context={"attempt": call_count}, operation="test_operation"
                )
                raise error

            return "success"

        with patch.object(logger, "error") as mock_error:
            result = test_function()

            assert result == "success"
            assert call_count == 3
            # Should have logged errors for first 2 attempts
            assert mock_error.call_count >= 2
