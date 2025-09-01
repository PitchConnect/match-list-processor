"""Discord notification client."""

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


class DiscordNotificationClient:
    """Discord notification client using webhooks."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Discord client.

        Args:
            config: Discord configuration dictionary
        """
        self.config = config
        self.webhook_url = config.get("webhook_url", "")
        self.bot_username = config.get("bot_username", "FOGIS Bot")
        self.bot_avatar_url = config.get("bot_avatar_url", "")
        self.enabled = config.get("enabled", False) and bool(self.webhook_url)

        if not self.enabled:
            logger.info("Discord notifications are disabled or webhook URL not configured")

    async def send_notification(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send Discord notification to recipient.

        Args:
            notification: Notification to send
            recipient: Discord recipient (webhook URL)

        Returns:
            Delivery result
        """
        if not self.enabled:
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.DISCORD,
                status=DeliveryStatus.FAILED,
                message="Discord notifications are disabled",
            )

        try:
            # Generate Discord embed
            embed_data = self._generate_discord_embed(notification, recipient)

            # Send webhook in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._send_webhook_sync, recipient.address or self.webhook_url, embed_data
            )

            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.DISCORD,
                status=DeliveryStatus.DELIVERED,
                message="Discord notification sent successfully",
            )

        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.DISCORD,
                status=DeliveryStatus.FAILED,
                message="Discord delivery failed",
                error_details=str(e),
            )

    def _send_webhook_sync(self, webhook_url: str, embed_data: Dict[str, Any]) -> None:
        """Send Discord webhook synchronously.

        Args:
            webhook_url: Discord webhook URL
            embed_data: Discord embed data
        """
        # Validate webhook URL for security (addresses B310)
        parsed_url = urlparse(webhook_url)
        if not parsed_url.netloc or "discord" not in parsed_url.netloc:
            raise ValueError("Invalid Discord webhook URL")
        if parsed_url.scheme not in ("http", "https"):
            raise ValueError("Invalid webhook URL scheme")

        # Prepare webhook payload
        payload = {"username": self.bot_username, "embeds": [embed_data]}

        if self.bot_avatar_url:
            payload["avatar_url"] = self.bot_avatar_url

        # Send webhook request
        data = json.dumps(payload).encode("utf-8")
        request = Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "FOGIS-Notification-Bot/1.0",
            },
        )

        with urlopen(request, timeout=30) as response:  # nosec B310
            if response.status not in (200, 204):
                raise Exception(f"Discord webhook returned status {response.status}")

        logger.info("Discord notification sent successfully")

    def _generate_discord_embed(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> Dict[str, Any]:
        """Generate Discord embed for notification.

        Args:
            notification: Notification data
            recipient: Recipient information

        Returns:
            Discord embed dictionary
        """
        match_context = notification.match_context

        # Priority colors (Discord color integers)
        priority_colors = {
            "critical": 0xDC2626,  # red
            "high": 0xEA580C,  # orange
            "medium": 0x2563EB,  # blue
            "low": 0x059669,  # green
        }

        color = priority_colors.get(notification.priority.value, 0x2563EB)

        # Priority emojis
        priority_emojis = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📢",
            "low": "ℹ️",
        }

        emoji = priority_emojis.get(notification.priority.value, "📢")

        # Build embed
        embed = {
            "title": f"{emoji} FOGIS Match Notification",
            "description": f"**{notification.change_summary}**",
            "color": color,
            "timestamp": notification.timestamp.isoformat(),
            "fields": [],
            "footer": {"text": f"FOGIS Notification System • {notification.notification_id[:8]}"},
        }

        # Add match information field
        match_info = self._format_match_info(match_context)
        embed["fields"].append(
            {"name": "⚽ Match Information", "value": match_info, "inline": False}
        )

        # Add change details field
        change_details = f"**Category:** {notification.change_category.replace('_', ' ').title()}\n"
        change_details += f"**Priority:** {notification.priority.value.upper()}"

        embed["fields"].append(
            {"name": "📋 Change Details", "value": change_details, "inline": True}
        )

        # Add recipient information
        embed["fields"].append(
            {
                "name": "👤 Recipient",
                "value": f"**Name:** {recipient.name}\n**Role:** {recipient.preferences.get('role', 'Unknown')}",
                "inline": True,
            }
        )

        # Add detailed changes if available
        if notification.field_changes:
            changes_text = self._format_field_changes(notification.field_changes)
            if len(changes_text) <= 1024:  # Discord field value limit
                embed["fields"].append(
                    {"name": "📝 Detailed Changes", "value": changes_text, "inline": False}
                )

        return embed

    def _format_match_info(self, match_context: Dict[str, Any]) -> str:
        """Format match information for Discord.

        Args:
            match_context: Match context data

        Returns:
            Formatted match information string
        """
        home_team = match_context.get("lag1namn", "TBD")
        away_team = match_context.get("lag2namn", "TBD")
        date = match_context.get("speldatum", "TBD")
        time = match_context.get("avsparkstid", "TBD")
        venue = match_context.get("anlaggningnamn", "TBD")
        competition = match_context.get("serienamn", "TBD")

        info = f"**Teams:** {home_team} vs {away_team}\n"
        info += f"**Date:** {date}\n"
        info += f"**Time:** {time}\n"
        info += f"**Venue:** {venue}\n"
        info += f"**Competition:** {competition}"

        return info

    def _format_field_changes(self, field_changes: list) -> str:
        """Format field changes for Discord.

        Args:
            field_changes: List of field change dictionaries

        Returns:
            Formatted field changes string
        """
        if not field_changes:
            return "No detailed changes available"

        changes_text = ""
        for change in field_changes[:5]:  # Limit to 5 changes to avoid Discord limits
            field_name = change.get("field_name", "Unknown")
            previous = change.get("previous_value", "None")
            current = change.get("current_value", "None")

            # Truncate long values
            if len(str(previous)) > 50:
                previous = str(previous)[:47] + "..."
            if len(str(current)) > 50:
                current = str(current)[:47] + "..."

            changes_text += f"**{field_name}:** {previous} → {current}\n"

        if len(field_changes) > 5:
            changes_text += f"... and {len(field_changes) - 5} more changes"

        return changes_text.strip()

    def test_webhook(self) -> bool:
        """Test Discord webhook connectivity.

        Returns:
            True if webhook is working, False otherwise
        """
        if not self.enabled:
            return False

        try:
            test_embed = {
                "title": "🧪 FOGIS Notification Test",
                "description": "This is a test notification to verify Discord webhook connectivity.",
                "color": 0x00FF00,  # green
                "timestamp": "2025-01-01T00:00:00Z",
                "footer": {"text": "FOGIS Notification System Test"},
            }

            self._send_webhook_sync(self.webhook_url, test_embed)
            return True

        except Exception as e:
            logger.error(f"Discord webhook test failed: {e}")
            return False
