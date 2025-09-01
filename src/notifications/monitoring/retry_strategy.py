"""Retry strategy implementation with exponential backoff."""

import logging
from typing import Any, Dict

from .models import FailureReason

logger = logging.getLogger(__name__)


class RetryStrategy:
    """Configurable retry strategy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: int = 5,
        max_delay: int = 300,
        exponential_base: float = 2.0,
    ):
        """Initialize retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

        # Non-retryable failure reasons
        self.non_retryable_failures = {
            FailureReason.AUTHENTICATION_ERROR,
            FailureReason.INVALID_RECIPIENT,
        }

        logger.info(
            f"Retry strategy initialized: max_retries={max_retries}, base_delay={base_delay}s"
        )

    def should_retry(self, attempt_number: int, failure_reason: FailureReason) -> bool:
        """Determine if retry should be attempted.

        Args:
            attempt_number: Current attempt number (1-based)
            failure_reason: Reason for the failure

        Returns:
            True if retry should be attempted
        """
        if attempt_number >= self.max_retries:
            logger.debug(f"Max retries ({self.max_retries}) reached for attempt {attempt_number}")
            return False

        if failure_reason in self.non_retryable_failures:
            logger.debug(f"Non-retryable failure: {failure_reason.value}")
            return False

        logger.debug(
            f"Retry approved for attempt {attempt_number}, failure: {failure_reason.value}"
        )
        return True

    def calculate_delay(self, attempt_number: int, failure_reason: FailureReason) -> int:
        """Calculate delay before next retry.

        Args:
            attempt_number: Current attempt number (1-based)
            failure_reason: Reason for the failure

        Returns:
            Delay in seconds before next retry
        """
        if failure_reason == FailureReason.RATE_LIMIT:
            # Longer delay for rate limiting
            delay = self.base_delay * (self.exponential_base**attempt_number) * 2
        else:
            # Standard exponential backoff
            delay = self.base_delay * (self.exponential_base**attempt_number)

        # Cap at maximum delay
        final_delay = min(int(delay), self.max_delay)

        logger.debug(
            f"Calculated retry delay: {final_delay}s for attempt {attempt_number}, reason: {failure_reason.value}"
        )
        return final_delay

    def get_configuration(self) -> Dict[str, Any]:
        """Get current retry strategy configuration.

        Returns:
            Dictionary with configuration details
        """
        return {
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "exponential_base": self.exponential_base,
            "non_retryable_failures": [reason.value for reason in self.non_retryable_failures],
        }

    def update_configuration(self, config: Dict[str, Any]) -> None:
        """Update retry strategy configuration.

        Args:
            config: New configuration values
        """
        if "max_retries" in config:
            self.max_retries = config["max_retries"]
        if "base_delay" in config:
            self.base_delay = config["base_delay"]
        if "max_delay" in config:
            self.max_delay = config["max_delay"]
        if "exponential_base" in config:
            self.exponential_base = config["exponential_base"]

        logger.info(f"Retry strategy configuration updated: {self.get_configuration()}")


class ChannelSpecificRetryStrategy:
    """Channel-specific retry strategies."""

    def __init__(self) -> None:
        """Initialize with default strategies for different channels."""
        self.strategies = {
            "email": RetryStrategy(max_retries=3, base_delay=5, max_delay=300),
            "discord": RetryStrategy(max_retries=5, base_delay=2, max_delay=120),
            "webhook": RetryStrategy(max_retries=3, base_delay=10, max_delay=600),
            "default": RetryStrategy(max_retries=3, base_delay=5, max_delay=300),
        }

        logger.info("Channel-specific retry strategies initialized")

    def get_strategy(self, channel: str) -> RetryStrategy:
        """Get retry strategy for specific channel.

        Args:
            channel: Channel name (email, discord, webhook, etc.)

        Returns:
            RetryStrategy for the channel
        """
        channel_lower = channel.lower()
        strategy = self.strategies.get(channel_lower, self.strategies["default"])

        logger.debug(
            f"Retrieved retry strategy for channel '{channel}': {strategy.get_configuration()}"
        )
        return strategy

    def update_channel_strategy(self, channel: str, config: Dict[str, Any]) -> None:
        """Update retry strategy for specific channel.

        Args:
            channel: Channel name
            config: New configuration for the channel
        """
        channel_lower = channel.lower()

        if channel_lower not in self.strategies:
            self.strategies[channel_lower] = RetryStrategy()

        self.strategies[channel_lower].update_configuration(config)
        logger.info(f"Updated retry strategy for channel '{channel}': {config}")

    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get all channel strategies.

        Returns:
            Dictionary mapping channel names to their configurations
        """
        return {
            channel: strategy.get_configuration() for channel, strategy in self.strategies.items()
        }
