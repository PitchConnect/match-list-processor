"""Generic webhook notification client."""

import asyncio
import json
import logging
from typing import Any, Dict
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ...models.notification_models import (
    ChangeNotification,
    DeliveryResult,
    DeliveryStatus,
    NotificationChannel,
    NotificationRecipient,
)

logger = logging.getLogger(__name__)


class WebhookNotificationClient:
    """Generic webhook notification client."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize webhook client.

        Args:
            config: Webhook configuration dictionary
        """
        self.config = config
        self.default_webhook_url = config.get("webhook_url", "")
        self.timeout = config.get("timeout", 30)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.custom_headers = config.get("headers", {})
        self.enabled = config.get("enabled", False)

        if not self.enabled:
            logger.info("Webhook notifications are disabled")

    async def send_notification(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send webhook notification to recipient.

        Args:
            notification: Notification to send
            recipient: Webhook recipient

        Returns:
            Delivery result
        """
        if not self.enabled:
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryStatus.FAILED,
                message="Webhook notifications are disabled",
            )

        webhook_url = recipient.address or self.default_webhook_url
        if not webhook_url:
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryStatus.FAILED,
                message="No webhook URL configured",
            )

        try:
            # Generate webhook payload
            payload = self._generate_webhook_payload(notification, recipient)

            # Send webhook with retry logic
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_webhook_with_retry, webhook_url, payload)

            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryStatus.DELIVERED,
                message="Webhook notification sent successfully",
            )

        except Exception as e:
            logger.error(f"Failed to send webhook notification to {webhook_url}: {e}")
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryStatus.FAILED,
                message="Webhook delivery failed",
                error_details=str(e),
            )

    def _send_webhook_with_retry(self, webhook_url: str, payload: Dict[str, Any]) -> None:
        """Send webhook with retry logic.

        Args:
            webhook_url: Webhook URL
            payload: Webhook payload
        """
        last_exception = None

        for attempt in range(self.retry_attempts):
            try:
                self._send_webhook_sync(webhook_url, payload)
                logger.info(f"Webhook sent successfully to {webhook_url} on attempt {attempt + 1}")
                return

            except Exception as e:
                last_exception = e
                logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")

                if attempt < self.retry_attempts - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    import time

                    time.sleep(2**attempt)

        # All attempts failed
        raise last_exception or Exception("All webhook attempts failed")

    def _send_webhook_sync(self, webhook_url: str, payload: Dict[str, Any]) -> None:
        """Send webhook synchronously.

        Args:
            webhook_url: Webhook URL
            payload: Webhook payload
        """
        # Validate webhook URL
        parsed_url = urlparse(webhook_url)
        if not parsed_url.netloc:
            raise ValueError("Invalid webhook URL")

        # Prepare request
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FOGIS-Notification-System/1.0",
            **self.custom_headers,
        }

        request = Request(webhook_url, data=data, headers=headers)

        # Send request
        with urlopen(request, timeout=self.timeout) as response:
            if response.status not in (200, 201, 202, 204):
                response_body = response.read().decode("utf-8", errors="ignore")
                raise Exception(f"Webhook returned status {response.status}: {response_body}")

        logger.debug(f"Webhook sent successfully to {webhook_url}")

    def _generate_webhook_payload(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> Dict[str, Any]:
        """Generate webhook payload.

        Args:
            notification: Notification data
            recipient: Recipient information

        Returns:
            Webhook payload dictionary
        """
        # Create comprehensive payload with all notification data
        payload = {
            "notification_id": notification.notification_id,
            "timestamp": notification.timestamp.isoformat(),
            "event_type": "match_change_notification",
            "priority": notification.priority.value,
            "change_category": notification.change_category,
            "change_summary": notification.change_summary,
            "recipient": {
                "stakeholder_id": recipient.stakeholder_id,
                "name": recipient.name,
                "channel": recipient.channel.value,
                "preferences": recipient.preferences,
            },
            "match": notification.match_context,
            "changes": notification.field_changes,
            "affected_stakeholders": notification.affected_stakeholders,
        }

        # Add custom fields based on recipient preferences
        if recipient.preferences.get("include_metadata", True):
            payload["metadata"] = {
                "system": "fogis-match-list-processor",
                "version": "1.0",
                "delivery_channel": "webhook",
            }

        # Add simplified format for basic integrations
        if recipient.preferences.get("simple_format", False):
            payload = self._generate_simple_payload(notification, recipient)

        return payload

    def _generate_simple_payload(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> Dict[str, Any]:
        """Generate simplified webhook payload.

        Args:
            notification: Notification data
            recipient: Recipient information

        Returns:
            Simplified webhook payload
        """
        match_context = notification.match_context

        return {
            "event": "match_change",
            "priority": notification.priority.value,
            "message": notification.change_summary,
            "match": {
                "home_team": match_context.get("lag1namn", "TBD"),
                "away_team": match_context.get("lag2namn", "TBD"),
                "date": match_context.get("speldatum", "TBD"),
                "time": match_context.get("avsparkstid", "TBD"),
                "venue": match_context.get("anlaggningnamn", "TBD"),
                "competition": match_context.get("serienamn", "TBD"),
            },
            "recipient": recipient.name,
            "timestamp": notification.timestamp.isoformat(),
        }

    def test_webhook(self, webhook_url: str = None) -> bool:
        """Test webhook connectivity.

        Args:
            webhook_url: Optional webhook URL to test (uses default if not provided)

        Returns:
            True if webhook is working, False otherwise
        """
        if not self.enabled:
            return False

        test_url = webhook_url or self.default_webhook_url
        if not test_url:
            return False

        try:
            test_payload = {
                "event": "test_notification",
                "message": "This is a test notification to verify webhook connectivity.",
                "timestamp": "2025-01-01T00:00:00Z",
                "system": "fogis-notification-system",
                "test": True,
            }

            self._send_webhook_sync(test_url, test_payload)
            return True

        except Exception as e:
            logger.error(f"Webhook test failed for {test_url}: {e}")
            return False

    def validate_webhook_url(self, webhook_url: str) -> bool:
        """Validate webhook URL format.

        Args:
            webhook_url: Webhook URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        try:
            parsed_url = urlparse(webhook_url)
            return bool(parsed_url.netloc and parsed_url.scheme in ("http", "https"))
        except Exception:
            return False
