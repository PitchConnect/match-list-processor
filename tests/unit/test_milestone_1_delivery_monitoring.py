"""Tests for Milestone 1 delivery monitoring implementation."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.notifications.monitoring.delivery_monitor import DeliveryMonitor
from src.notifications.monitoring.models import (
    DeliveryStatus,
    FailureReason,
    NotificationDeliveryRecord,
)
from src.notifications.monitoring.retry_strategy import RetryStrategy


@pytest.mark.unit
class TestDeliveryMonitor:
    """Test delivery monitoring functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

        self.monitor = DeliveryMonitor(storage_path=self.temp_file.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            os.unlink(self.temp_file.name)
        except FileNotFoundError:
            pass

    def test_record_successful_delivery(self):
        """Test recording a successful delivery."""
        self.monitor.record_delivery_attempt(
            notification_id="test_123",
            channel="email",
            recipient="test@example.com",
            status=DeliveryStatus.DELIVERED,
            response_time_ms=150,
        )

        # Check that record was created
        record_key = "test_123_email_test@example.com"
        assert record_key in self.monitor.delivery_records

        record = self.monitor.delivery_records[record_key]
        assert record.notification_id == "test_123"
        assert record.channel == "email"
        assert record.recipient == "test@example.com"
        assert record.final_status == DeliveryStatus.DELIVERED
        assert record.total_attempts == 1
        assert record.delivered_at is not None
        assert record.total_delivery_time_ms is not None

    def test_record_failed_delivery_with_retry(self):
        """Test recording a failed delivery that should be retried."""
        self.monitor.record_delivery_attempt(
            notification_id="test_456",
            channel="discord",
            recipient="webhook_url",
            status=DeliveryStatus.FAILED,
            error_message="Network timeout",
            failure_reason=FailureReason.NETWORK_ERROR,
        )

        # Check that record was created
        record_key = "test_456_discord_webhook_url"
        assert record_key in self.monitor.delivery_records

        record = self.monitor.delivery_records[record_key]
        assert record.final_status == DeliveryStatus.RETRYING
        assert record.total_attempts == 1

        # Check that retry was scheduled
        assert len(self.monitor.retry_queue) == 1
        retry_item = self.monitor.retry_queue[0]
        assert retry_item["notification_id"] == "test_456"
        assert retry_item["channel"] == "discord"

    def test_record_failed_delivery_non_retryable(self):
        """Test recording a failed delivery that should not be retried."""
        self.monitor.record_delivery_attempt(
            notification_id="test_789",
            channel="email",
            recipient="invalid@example.com",
            status=DeliveryStatus.FAILED,
            error_message="Invalid recipient",
            failure_reason=FailureReason.INVALID_RECIPIENT,
        )

        # Check that record was created
        record_key = "test_789_email_invalid@example.com"
        record = self.monitor.delivery_records[record_key]
        assert record.final_status == DeliveryStatus.DEAD_LETTER

        # Check that item was moved to dead letter queue
        assert len(self.monitor.dead_letter_queue) == 1
        dead_letter_item = self.monitor.dead_letter_queue[0]
        assert dead_letter_item["notification_id"] == "test_789"
        assert dead_letter_item["failure_reason"] == FailureReason.INVALID_RECIPIENT.value

    def test_multiple_delivery_attempts(self):
        """Test multiple delivery attempts for same notification."""
        notification_id = "test_multi"
        channel = "webhook"
        recipient = "https://example.com/webhook"

        # First attempt fails
        self.monitor.record_delivery_attempt(
            notification_id=notification_id,
            channel=channel,
            recipient=recipient,
            status=DeliveryStatus.FAILED,
            failure_reason=FailureReason.NETWORK_ERROR,
        )

        # Second attempt succeeds
        self.monitor.record_delivery_attempt(
            notification_id=notification_id,
            channel=channel,
            recipient=recipient,
            status=DeliveryStatus.DELIVERED,
            response_time_ms=200,
        )

        record_key = f"{notification_id}_{channel}_{recipient}"
        record = self.monitor.delivery_records[record_key]

        assert record.total_attempts == 2
        assert record.final_status == DeliveryStatus.DELIVERED
        assert len(record.attempts) == 2
        assert record.attempts[0].status == DeliveryStatus.FAILED
        assert record.attempts[1].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_process_retry_queue(self):
        """Test processing of retry queue."""
        # Add item to retry queue with past retry time
        past_time = datetime.utcnow() - timedelta(minutes=5)
        self.monitor.retry_queue.append(
            {
                "notification_id": "retry_test",
                "channel": "email",
                "recipient": "retry@example.com",
                "retry_time": past_time.isoformat(),
                "attempt_number": 2,
                "failure_reason": FailureReason.NETWORK_ERROR.value,
            }
        )

        # Add item with future retry time
        future_time = datetime.utcnow() + timedelta(minutes=5)
        self.monitor.retry_queue.append(
            {
                "notification_id": "future_test",
                "channel": "discord",
                "recipient": "future_webhook",
                "retry_time": future_time.isoformat(),
                "attempt_number": 1,
                "failure_reason": FailureReason.TIMEOUT.value,
            }
        )

        # Process retry queue
        ready_items = await self.monitor.process_retry_queue()

        # Should return only the past item
        assert len(ready_items) == 1
        assert ready_items[0]["notification_id"] == "retry_test"

        # Future item should remain in queue
        assert len(self.monitor.retry_queue) == 1
        assert self.monitor.retry_queue[0]["notification_id"] == "future_test"

    def test_get_delivery_stats(self):
        """Test delivery statistics calculation."""
        # Create some test records
        now = datetime.utcnow()

        # Successful delivery
        self.monitor.delivery_records["success_1"] = NotificationDeliveryRecord(
            notification_id="success_1",
            channel="email",
            recipient="success@example.com",
            created_at=now - timedelta(hours=1),
            final_status=DeliveryStatus.DELIVERED,
            total_attempts=1,
            total_delivery_time_ms=100,
        )

        # Failed delivery
        self.monitor.delivery_records["failed_1"] = NotificationDeliveryRecord(
            notification_id="failed_1",
            channel="discord",
            recipient="failed_webhook",
            created_at=now - timedelta(hours=2),
            final_status=DeliveryStatus.FAILED,
            total_attempts=3,
        )

        # Old record (outside time window)
        self.monitor.delivery_records["old_1"] = NotificationDeliveryRecord(
            notification_id="old_1",
            channel="email",
            recipient="old@example.com",
            created_at=now - timedelta(hours=25),
            final_status=DeliveryStatus.DELIVERED,
            total_attempts=1,
        )

        stats = self.monitor.get_delivery_stats(time_window_hours=24)

        assert stats["total_notifications"] == 2  # Only recent records
        assert stats["delivered"] == 1
        assert stats["failed"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["average_delivery_time_ms"] == 100

        # Check channel breakdown
        assert "email" in stats["by_channel"]
        assert "discord" in stats["by_channel"]
        assert stats["by_channel"]["email"]["delivered"] == 1
        assert stats["by_channel"]["discord"]["failed"] == 1

    def test_get_health_status(self):
        """Test health status assessment."""
        # Create records for health assessment
        now = datetime.utcnow()

        # Add mostly successful deliveries
        for i in range(10):
            self.monitor.delivery_records[f"success_{i}"] = NotificationDeliveryRecord(
                notification_id=f"success_{i}",
                channel="email",
                recipient=f"test{i}@example.com",
                created_at=now - timedelta(minutes=30),
                final_status=DeliveryStatus.DELIVERED,
                total_attempts=1,
            )

        # Add one failed delivery
        self.monitor.delivery_records["failed_1"] = NotificationDeliveryRecord(
            notification_id="failed_1",
            channel="email",
            recipient="failed@example.com",
            created_at=now - timedelta(minutes=30),
            final_status=DeliveryStatus.FAILED,
            total_attempts=3,
        )

        health = self.monitor.get_health_status()

        assert health["status"] in ["healthy", "degraded"]  # 10/11 = 90.9% success rate
        assert "stats" in health
        assert health["stats"]["success_rate"] > 0.9

    def test_clear_old_records(self):
        """Test clearing of old delivery records."""
        now = datetime.utcnow()

        # Add recent record
        self.monitor.delivery_records["recent"] = NotificationDeliveryRecord(
            notification_id="recent",
            channel="email",
            recipient="recent@example.com",
            created_at=now - timedelta(days=1),
            final_status=DeliveryStatus.DELIVERED,
            total_attempts=1,
        )

        # Add old record
        self.monitor.delivery_records["old"] = NotificationDeliveryRecord(
            notification_id="old",
            channel="email",
            recipient="old@example.com",
            created_at=now - timedelta(days=35),
            final_status=DeliveryStatus.DELIVERED,
            total_attempts=1,
        )

        # Add old dead letter item
        self.monitor.dead_letter_queue.append(
            {
                "notification_id": "old_dead",
                "failed_at": (now - timedelta(days=35)).isoformat(),
            }
        )

        cleared_count = self.monitor.clear_old_records(days_to_keep=30)

        assert cleared_count == 2  # One old record + one old dead letter
        assert "recent" in self.monitor.delivery_records
        assert "old" not in self.monitor.delivery_records
        assert len(self.monitor.dead_letter_queue) == 0

    def test_storage_persistence(self):
        """Test that records are persisted to storage."""
        # Record a delivery
        self.monitor.record_delivery_attempt(
            notification_id="persist_test",
            channel="email",
            recipient="persist@example.com",
            status=DeliveryStatus.DELIVERED,
        )

        # Create new monitor with same storage path
        new_monitor = DeliveryMonitor(storage_path=self.temp_file.name)

        # Should load the previous record
        record_key = "persist_test_email_persist@example.com"
        assert record_key in new_monitor.delivery_records

        record = new_monitor.delivery_records[record_key]
        assert record.notification_id == "persist_test"
        assert record.final_status == DeliveryStatus.DELIVERED


@pytest.mark.unit
class TestRetryStrategy:
    """Test retry strategy functionality."""

    def test_should_retry_within_limits(self):
        """Test retry decision within attempt limits."""
        strategy = RetryStrategy(max_retries=3)

        # Should retry for retryable failures within limits
        assert strategy.should_retry(1, FailureReason.NETWORK_ERROR) is True
        assert strategy.should_retry(2, FailureReason.TIMEOUT) is True
        assert strategy.should_retry(2, FailureReason.RATE_LIMIT) is True  # Within max_retries=3

    def test_should_not_retry_beyond_limits(self):
        """Test retry decision beyond attempt limits."""
        strategy = RetryStrategy(max_retries=3)

        # Should not retry beyond max attempts
        assert strategy.should_retry(4, FailureReason.NETWORK_ERROR) is False
        assert strategy.should_retry(5, FailureReason.TIMEOUT) is False

    def test_should_not_retry_non_retryable(self):
        """Test retry decision for non-retryable failures."""
        strategy = RetryStrategy(max_retries=3)

        # Should not retry for non-retryable failures
        assert strategy.should_retry(1, FailureReason.AUTHENTICATION_ERROR) is False
        assert strategy.should_retry(1, FailureReason.INVALID_RECIPIENT) is False

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff delay calculation."""
        strategy = RetryStrategy(base_delay=5, exponential_base=2.0, max_delay=300)

        # Test exponential backoff
        delay1 = strategy.calculate_delay(1, FailureReason.NETWORK_ERROR)
        delay2 = strategy.calculate_delay(2, FailureReason.NETWORK_ERROR)
        delay3 = strategy.calculate_delay(3, FailureReason.NETWORK_ERROR)

        assert delay1 == 10  # 5 * 2^1
        assert delay2 == 20  # 5 * 2^2
        assert delay3 == 40  # 5 * 2^3

    def test_calculate_delay_rate_limit(self):
        """Test delay calculation for rate limiting."""
        strategy = RetryStrategy(base_delay=5, exponential_base=2.0)

        # Rate limit should have longer delay
        normal_delay = strategy.calculate_delay(1, FailureReason.NETWORK_ERROR)
        rate_limit_delay = strategy.calculate_delay(1, FailureReason.RATE_LIMIT)

        assert rate_limit_delay > normal_delay

    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at maximum."""
        strategy = RetryStrategy(base_delay=5, exponential_base=2.0, max_delay=100)

        # Large attempt number should be capped
        delay = strategy.calculate_delay(10, FailureReason.NETWORK_ERROR)
        assert delay <= 100
