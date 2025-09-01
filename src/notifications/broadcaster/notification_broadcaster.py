"""Multi-channel notification broadcaster."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.notification_models import (
    ChangeNotification,
    DeliveryResult,
    DeliveryStatus,
    NotificationChannel,
)
from .channel_clients.discord_client import DiscordNotificationClient
from .channel_clients.email_client import EmailNotificationClient
from .channel_clients.webhook_client import WebhookNotificationClient

logger = logging.getLogger(__name__)


class NotificationBroadcaster:
    """Multi-channel notification broadcaster."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize notification broadcaster.

        Args:
            config: Configuration dictionary with channel settings
        """
        self.config = config
        self.email_client = EmailNotificationClient(config.get("email", {}))
        self.discord_client = DiscordNotificationClient(config.get("discord", {}))
        self.webhook_client = WebhookNotificationClient(config.get("webhook", {}))

        # Track delivery statistics
        self.delivery_stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "by_channel": {},
        }

    async def broadcast_notification(
        self, notification: ChangeNotification
    ) -> Dict[str, DeliveryResult]:
        """Broadcast notification to all recipients.

        Args:
            notification: Notification to broadcast

        Returns:
            Dictionary mapping recipient keys to delivery results
        """
        if not notification.recipients:
            logger.warning(f"No recipients for notification {notification.notification_id}")
            return {}

        logger.info(
            f"Broadcasting notification {notification.notification_id} to {len(notification.recipients)} recipients"
        )

        # Group recipients by channel for efficient processing
        recipients_by_channel = self._group_recipients_by_channel(notification.recipients)

        # Send notifications concurrently by channel
        tasks = []
        for channel, recipients in recipients_by_channel.items():
            task = self._send_to_channel(notification, channel, recipients)
            tasks.append(task)

        # Wait for all deliveries to complete
        channel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results from all channels
        all_results = {}
        for result in channel_results:
            if isinstance(result, dict):
                all_results.update(result)
            elif isinstance(result, Exception):
                logger.error(f"Channel delivery failed: {result}")

        # Update delivery statistics
        self._update_delivery_stats(all_results)

        # Update notification delivery status
        self._update_notification_status(notification, all_results)

        logger.info(f"Completed broadcasting notification {notification.notification_id}")
        return all_results

    def _group_recipients_by_channel(self, recipients) -> Dict[NotificationChannel, List]:
        """Group recipients by notification channel.

        Args:
            recipients: List of notification recipients

        Returns:
            Dictionary mapping channels to recipient lists
        """
        grouped = {}
        for recipient in recipients:
            channel = recipient.channel
            if channel not in grouped:
                grouped[channel] = []
            grouped[channel].append(recipient)
        return grouped

    async def _send_to_channel(
        self, notification: ChangeNotification, channel: NotificationChannel, recipients: List
    ) -> Dict[str, DeliveryResult]:
        """Send notification to all recipients on a specific channel.

        Args:
            notification: Notification to send
            channel: Notification channel
            recipients: List of recipients for this channel

        Returns:
            Dictionary mapping recipient keys to delivery results
        """
        results = {}

        try:
            if channel == NotificationChannel.EMAIL:
                channel_results = await self._send_email_notifications(notification, recipients)
            elif channel == NotificationChannel.DISCORD:
                channel_results = await self._send_discord_notifications(notification, recipients)
            elif channel == NotificationChannel.WEBHOOK:
                channel_results = await self._send_webhook_notifications(notification, recipients)
            else:
                logger.warning(f"Unsupported notification channel: {channel}")
                channel_results = {}

            results.update(channel_results)

        except Exception as e:
            logger.error(f"Error sending notifications via {channel.value}: {e}")
            # Create failed results for all recipients
            for recipient in recipients:
                key = f"{channel.value}_{recipient.stakeholder_id}"
                results[key] = DeliveryResult(
                    recipient_id=recipient.stakeholder_id,
                    channel=channel,
                    status=DeliveryStatus.FAILED,
                    message="Channel delivery failed",
                    error_details=str(e),
                )

        return results

    async def _send_email_notifications(
        self, notification: ChangeNotification, recipients: List
    ) -> Dict[str, DeliveryResult]:
        """Send email notifications.

        Args:
            notification: Notification to send
            recipients: Email recipients

        Returns:
            Dictionary mapping recipient keys to delivery results
        """
        results = {}

        for recipient in recipients:
            try:
                result = await self.email_client.send_notification(notification, recipient)
                key = f"email_{recipient.stakeholder_id}"
                results[key] = result

            except Exception as e:
                logger.error(f"Failed to send email to {recipient.address}: {e}")
                key = f"email_{recipient.stakeholder_id}"
                results[key] = DeliveryResult(
                    recipient_id=recipient.stakeholder_id,
                    channel=NotificationChannel.EMAIL,
                    status=DeliveryStatus.FAILED,
                    message="Email delivery failed",
                    error_details=str(e),
                )

        return results

    async def _send_discord_notifications(
        self, notification: ChangeNotification, recipients: List
    ) -> Dict[str, DeliveryResult]:
        """Send Discord notifications.

        Args:
            notification: Notification to send
            recipients: Discord recipients

        Returns:
            Dictionary mapping recipient keys to delivery results
        """
        results = {}

        for recipient in recipients:
            try:
                result = await self.discord_client.send_notification(notification, recipient)
                key = f"discord_{recipient.stakeholder_id}"
                results[key] = result

            except Exception as e:
                logger.error(f"Failed to send Discord notification to {recipient.address}: {e}")
                key = f"discord_{recipient.stakeholder_id}"
                results[key] = DeliveryResult(
                    recipient_id=recipient.stakeholder_id,
                    channel=NotificationChannel.DISCORD,
                    status=DeliveryStatus.FAILED,
                    message="Discord delivery failed",
                    error_details=str(e),
                )

        return results

    async def _send_webhook_notifications(
        self, notification: ChangeNotification, recipients: List
    ) -> Dict[str, DeliveryResult]:
        """Send webhook notifications.

        Args:
            notification: Notification to send
            recipients: Webhook recipients

        Returns:
            Dictionary mapping recipient keys to delivery results
        """
        results = {}

        for recipient in recipients:
            try:
                result = await self.webhook_client.send_notification(notification, recipient)
                key = f"webhook_{recipient.stakeholder_id}"
                results[key] = result

            except Exception as e:
                logger.error(f"Failed to send webhook notification to {recipient.address}: {e}")
                key = f"webhook_{recipient.stakeholder_id}"
                results[key] = DeliveryResult(
                    recipient_id=recipient.stakeholder_id,
                    channel=NotificationChannel.WEBHOOK,
                    status=DeliveryStatus.FAILED,
                    message="Webhook delivery failed",
                    error_details=str(e),
                )

        return results

    def _update_delivery_stats(self, results: Dict[str, DeliveryResult]) -> None:
        """Update delivery statistics.

        Args:
            results: Delivery results to process
        """
        for result in results.values():
            self.delivery_stats["total_sent"] += 1

            if result.status == DeliveryStatus.DELIVERED:
                self.delivery_stats["total_delivered"] += 1
            elif result.status == DeliveryStatus.FAILED:
                self.delivery_stats["total_failed"] += 1

            # Update channel statistics
            channel_name = result.channel.value
            if channel_name not in self.delivery_stats["by_channel"]:
                self.delivery_stats["by_channel"][channel_name] = {
                    "sent": 0,
                    "delivered": 0,
                    "failed": 0,
                }

            self.delivery_stats["by_channel"][channel_name]["sent"] += 1
            if result.status == DeliveryStatus.DELIVERED:
                self.delivery_stats["by_channel"][channel_name]["delivered"] += 1
            elif result.status == DeliveryStatus.FAILED:
                self.delivery_stats["by_channel"][channel_name]["failed"] += 1

    def _update_notification_status(
        self, notification: ChangeNotification, results: Dict[str, DeliveryResult]
    ) -> None:
        """Update notification delivery status.

        Args:
            notification: Notification to update
            results: Delivery results
        """
        for key, result in results.items():
            notification.delivery_status[key] = result.status

    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get delivery statistics.

        Returns:
            Dictionary with delivery statistics
        """
        stats = self.delivery_stats.copy()

        # Calculate success rates
        if stats["total_sent"] > 0:
            stats["success_rate"] = stats["total_delivered"] / stats["total_sent"]
        else:
            stats["success_rate"] = 0.0

        # Calculate channel success rates
        for channel_stats in stats["by_channel"].values():
            if channel_stats["sent"] > 0:
                channel_stats["success_rate"] = channel_stats["delivered"] / channel_stats["sent"]
            else:
                channel_stats["success_rate"] = 0.0

        return stats

    def reset_statistics(self) -> None:
        """Reset delivery statistics."""
        self.delivery_stats = {
            "total_sent": 0,
            "total_delivered": 0,
            "total_failed": 0,
            "by_channel": {},
        }
