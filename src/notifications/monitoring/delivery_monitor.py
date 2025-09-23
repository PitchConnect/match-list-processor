"""Delivery monitoring system for notification tracking and retry management."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import DeliveryAttempt, DeliveryStatus, FailureReason, NotificationDeliveryRecord
from .retry_strategy import ChannelSpecificRetryStrategy

logger = logging.getLogger(__name__)


class DeliveryMonitor:
    """Monitors and tracks notification delivery with retry capabilities."""

    def __init__(self, storage_path: str = "data/delivery_records.json"):
        """Initialize delivery monitor.

        Args:
            storage_path: Path to store delivery records
        """
        self.storage_path = storage_path
        self.delivery_records: Dict[str, NotificationDeliveryRecord] = {}
        self.retry_queue: List[Dict[str, Any]] = []
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self.retry_strategy = ChannelSpecificRetryStrategy()

        # Ensure storage directory exists
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)

        # Load existing records
        self._load_records()

        logger.info(f"Delivery monitor initialized with storage: {storage_path}")

    def record_delivery_attempt(
        self,
        notification_id: str,
        channel: str,
        recipient: str,
        status: DeliveryStatus,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        failure_reason: Optional[FailureReason] = None,
    ) -> None:
        """Record a delivery attempt.

        Args:
            notification_id: Unique notification identifier
            channel: Delivery channel (email, discord, webhook)
            recipient: Recipient address/identifier
            status: Delivery status
            response_time_ms: Response time in milliseconds
            error_message: Error message if failed
            failure_reason: Categorized failure reason
        """
        record_key = f"{notification_id}_{channel}_{recipient}"

        # Create record if it doesn't exist
        if record_key not in self.delivery_records:
            self.delivery_records[record_key] = NotificationDeliveryRecord(
                notification_id=notification_id,
                channel=channel,
                recipient=recipient,
                created_at=datetime.utcnow(),
                final_status=DeliveryStatus.PENDING,
            )

        record = self.delivery_records[record_key]
        attempt = DeliveryAttempt(
            attempt_number=record.total_attempts + 1,
            timestamp=datetime.utcnow(),
            status=status,
            response_time_ms=response_time_ms,
            error_message=error_message,
            failure_reason=failure_reason,
        )

        record.add_attempt(attempt)

        # Handle retry logic for failed deliveries
        if status == DeliveryStatus.FAILED and failure_reason:
            self._handle_failed_delivery(record, failure_reason)

        # Save updated records
        self._save_records()

        logger.info(
            f"Recorded delivery attempt {attempt.attempt_number} for {record_key}: {status.value}"
        )

    def _handle_failed_delivery(
        self, record: NotificationDeliveryRecord, failure_reason: FailureReason
    ) -> None:
        """Handle failed delivery and schedule retry if appropriate.

        Args:
            record: Delivery record for the failed notification
            failure_reason: Reason for the failure
        """
        strategy = self.retry_strategy.get_strategy(record.channel)

        if strategy.should_retry(record.total_attempts, failure_reason):
            delay = strategy.calculate_delay(record.total_attempts, failure_reason)
            retry_time = datetime.utcnow() + timedelta(seconds=delay)

            retry_item = {
                "notification_id": record.notification_id,
                "channel": record.channel,
                "recipient": record.recipient,
                "retry_time": retry_time.isoformat(),
                "attempt_number": record.total_attempts + 1,
                "failure_reason": failure_reason.value,
            }

            self.retry_queue.append(retry_item)
            record.final_status = DeliveryStatus.RETRYING

            logger.info(f"Scheduled retry for {record.notification_id} in {delay} seconds")
        else:
            # Move to dead letter queue
            dead_letter_item = {
                "notification_id": record.notification_id,
                "channel": record.channel,
                "recipient": record.recipient,
                "failed_at": datetime.utcnow().isoformat(),
                "total_attempts": record.total_attempts,
                "final_error": (record.attempts[-1].error_message if record.attempts else None),
                "failure_reason": failure_reason.value,
            }

            self.dead_letter_queue.append(dead_letter_item)
            record.final_status = DeliveryStatus.DEAD_LETTER

            logger.warning(
                f"Moved {record.notification_id} to dead letter queue after {record.total_attempts} attempts"
            )

    async def process_retry_queue(self) -> List[Dict[str, Any]]:
        """Process items in retry queue that are ready for retry.

        Returns:
            List of items ready for retry
        """
        ready_for_retry = []
        remaining_items = []
        current_time = datetime.utcnow()

        for item in self.retry_queue:
            try:
                retry_time = datetime.fromisoformat(item["retry_time"])
                if current_time >= retry_time:
                    ready_for_retry.append(item)
                else:
                    remaining_items.append(item)
            except (ValueError, KeyError) as e:
                logger.error(f"Invalid retry queue item: {item}, error: {e}")
                # Skip invalid items
                continue

        self.retry_queue = remaining_items

        if ready_for_retry:
            logger.info(f"Processing {len(ready_for_retry)} items from retry queue")

        return ready_for_retry

    def get_delivery_stats(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get delivery statistics for specified time window.

        Args:
            time_window_hours: Time window in hours for statistics

        Returns:
            Dictionary with delivery statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_records = [
            record for record in self.delivery_records.values() if record.created_at >= cutoff_time
        ]

        if not recent_records:
            return {"total_notifications": 0, "time_window_hours": time_window_hours}

        # Calculate basic statistics
        total = len(recent_records)
        delivered = sum(1 for r in recent_records if r.final_status == DeliveryStatus.DELIVERED)
        failed = sum(1 for r in recent_records if r.final_status == DeliveryStatus.FAILED)
        dead_letter = sum(1 for r in recent_records if r.final_status == DeliveryStatus.DEAD_LETTER)
        retrying = sum(1 for r in recent_records if r.final_status == DeliveryStatus.RETRYING)

        # Calculate average delivery time for successful deliveries
        successful_deliveries = [r for r in recent_records if r.total_delivery_time_ms is not None]
        avg_delivery_time = (
            sum(
                r.total_delivery_time_ms
                for r in successful_deliveries
                if r.total_delivery_time_ms is not None
            )
            / len(successful_deliveries)
            if successful_deliveries
            else 0
        )

        # Group by channel
        by_channel: Dict[str, Dict[str, Any]] = {}
        for record in recent_records:
            channel = record.channel
            if channel not in by_channel:
                by_channel[channel] = {"total": 0, "delivered": 0, "failed": 0}
            by_channel[channel]["total"] += 1
            if record.final_status == DeliveryStatus.DELIVERED:
                by_channel[channel]["delivered"] += 1
            elif record.final_status in [
                DeliveryStatus.FAILED,
                DeliveryStatus.DEAD_LETTER,
            ]:
                by_channel[channel]["failed"] += 1

        # Calculate success rates by channel
        for channel_stats in by_channel.values():
            total_channel = channel_stats["total"]
            channel_stats["success_rate"] = (
                float(channel_stats["delivered"]) / total_channel if total_channel > 0 else 0.0
            )

        return {
            "time_window_hours": time_window_hours,
            "total_notifications": total,
            "delivered": delivered,
            "failed": failed,
            "dead_letter": dead_letter,
            "retrying": retrying,
            "success_rate": delivered / total if total > 0 else 0,
            "average_delivery_time_ms": avg_delivery_time,
            "retry_queue_size": len(self.retry_queue),
            "dead_letter_queue_size": len(self.dead_letter_queue),
            "by_channel": by_channel,
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of notification system.

        Returns:
            Dictionary with health status information
        """
        stats = self.get_delivery_stats(1)  # Last hour

        # Define health thresholds
        success_rate_threshold = 0.95
        max_retry_queue_size = 100
        max_dead_letter_size = 50

        health_issues = []

        if stats["success_rate"] < success_rate_threshold:
            health_issues.append(f"Low success rate: {stats['success_rate']:.2%}")

        if stats["retry_queue_size"] > max_retry_queue_size:
            health_issues.append(f"High retry queue size: {stats['retry_queue_size']}")

        if stats["dead_letter_queue_size"] > max_dead_letter_size:
            health_issues.append(f"High dead letter queue size: {stats['dead_letter_queue_size']}")

        # Check channel-specific health
        unhealthy_channels = []
        for channel, channel_stats in stats["by_channel"].items():
            if channel_stats["success_rate"] < success_rate_threshold:
                unhealthy_channels.append(f"{channel}: {channel_stats['success_rate']:.2%}")

        if unhealthy_channels:
            health_issues.append(f"Unhealthy channels: {', '.join(unhealthy_channels)}")

        health_status = "healthy" if not health_issues else "degraded"

        return {
            "status": health_status,
            "issues": health_issues,
            "last_check": datetime.utcnow().isoformat(),
            "stats": stats,
        }

    def _load_records(self) -> None:
        """Load delivery records from storage."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Load delivery records
                    for key, record_data in data.get("delivery_records", {}).items():
                        self.delivery_records[key] = NotificationDeliveryRecord.from_dict(
                            record_data
                        )

                    # Load queues
                    self.retry_queue = data.get("retry_queue", [])
                    self.dead_letter_queue = data.get("dead_letter_queue", [])

                logger.info(f"Loaded {len(self.delivery_records)} delivery records from storage")
        except Exception as e:
            logger.error(f"Failed to load delivery records: {e}")
            # Continue with empty records

    def _save_records(self) -> None:
        """Save delivery records to storage."""
        try:
            data = {
                "delivery_records": {
                    key: record.to_dict() for key, record in self.delivery_records.items()
                },
                "retry_queue": self.retry_queue,
                "dead_letter_queue": self.dead_letter_queue,
                "last_updated": datetime.utcnow().isoformat(),
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save delivery records: {e}")

    def clear_old_records(self, days_to_keep: int = 30) -> int:
        """Clear old delivery records to prevent storage bloat.

        Args:
            days_to_keep: Number of days of records to keep

        Returns:
            Number of records cleared
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days_to_keep)

        old_records = [
            key for key, record in self.delivery_records.items() if record.created_at < cutoff_time
        ]

        for key in old_records:
            del self.delivery_records[key]

        # Also clear old dead letter queue items
        old_dead_letters = []
        for i, item in enumerate(self.dead_letter_queue):
            try:
                failed_at = datetime.fromisoformat(item["failed_at"])
                if failed_at < cutoff_time:
                    old_dead_letters.append(i)
            except (ValueError, KeyError):
                # Remove invalid items
                old_dead_letters.append(i)

        # Remove in reverse order to maintain indices
        for i in reversed(old_dead_letters):
            self.dead_letter_queue.pop(i)

        if old_records or old_dead_letters:
            self._save_records()
            logger.info(
                f"Cleared {len(old_records)} old delivery records and {len(old_dead_letters)} dead letter items"
            )

        return len(old_records) + len(old_dead_letters)
