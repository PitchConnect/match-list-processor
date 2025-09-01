"""Main notification service that orchestrates the notification system."""

import asyncio
import logging
from typing import Any, Dict, List

from ..core.change_categorization import CategorizedChanges
from .broadcaster.notification_broadcaster import NotificationBroadcaster
from .converter.change_to_notification_converter import ChangeToNotificationConverter
from .models.notification_models import (
    ChangeNotification,
    DeliveryResult,
    DeliveryStatus,
    NotificationBatch,
    NotificationChannel,
)
from .stakeholders.stakeholder_manager import StakeholderManager
from .stakeholders.stakeholder_resolver import StakeholderResolver

logger = logging.getLogger(__name__)


class NotificationService:
    """Main notification service that orchestrates the notification system."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize notification service.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.enabled = config.get("enabled", False)

        # Initialize components
        stakeholder_storage_path = config.get("stakeholder_storage_path", "data/stakeholders.json")
        self.stakeholder_manager = StakeholderManager(stakeholder_storage_path)
        self.stakeholder_resolver = StakeholderResolver(self.stakeholder_manager)
        self.change_converter = ChangeToNotificationConverter(self.stakeholder_resolver)
        self.broadcaster = NotificationBroadcaster(config.get("channels", {}))

        # Notification queue for batch processing
        self.notification_queue: List[ChangeNotification] = []
        self.batch_size = config.get("batch_size", 10)
        self.batch_timeout = config.get("batch_timeout", 30)  # seconds

        if not self.enabled:
            logger.info("Notification service is disabled")
        else:
            logger.info("Notification service initialized successfully")

    async def process_changes(
        self, categorized_changes: CategorizedChanges, match_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process categorized changes and send notifications.

        Args:
            categorized_changes: Categorized changes from change detector
            match_data: Match data for context

        Returns:
            Processing results dictionary
        """
        if not self.enabled:
            logger.debug("Notification service is disabled, skipping change processing")
            return {"enabled": False, "notifications_sent": 0}

        if not categorized_changes or not categorized_changes.changes:
            logger.debug("No changes to process")
            return {"enabled": True, "notifications_sent": 0}

        logger.info(f"Processing {len(categorized_changes.changes)} categorized changes")

        try:
            # Convert changes to notifications
            notifications = self.change_converter.convert_changes_to_notifications(
                categorized_changes, match_data
            )

            if not notifications:
                logger.info("No notifications generated from changes")
                return {"enabled": True, "notifications_sent": 0}

            # Send notifications
            results = await self._send_notifications(notifications)

            logger.info(f"Processed {len(notifications)} notifications")
            return {
                "enabled": True,
                "notifications_sent": len(notifications),
                "delivery_results": results,
                "stakeholder_stats": self.stakeholder_manager.get_statistics(),
                "broadcaster_stats": self.broadcaster.get_delivery_statistics(),
            }

        except Exception as e:
            logger.error(f"Error processing changes: {e}")
            return {"enabled": True, "notifications_sent": 0, "error": str(e)}

    async def process_new_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process new match and send notifications.

        Args:
            match_data: New match data

        Returns:
            Processing results dictionary
        """
        if not self.enabled:
            logger.debug("Notification service is disabled, skipping new match processing")
            return {"enabled": False, "notifications_sent": 0}

        logger.info(f"Processing new match: {match_data.get('matchid', 'unknown')}")

        try:
            # Create notification for new match
            notification = self.change_converter.create_notification_from_match_data(
                match_data, "new_assignment", "medium"
            )

            if not notification.recipients:
                logger.info("No recipients found for new match notification")
                return {"enabled": True, "notifications_sent": 0}

            # Send notification
            results = await self._send_notifications([notification])

            logger.info(
                f"Processed new match notification with {len(notification.recipients)} recipients"
            )
            return {
                "enabled": True,
                "notifications_sent": 1,
                "delivery_results": results,
                "stakeholder_stats": self.stakeholder_manager.get_statistics(),
            }

        except Exception as e:
            logger.error(f"Error processing new match: {e}")
            return {"enabled": True, "notifications_sent": 0, "error": str(e)}

    async def _send_notifications(self, notifications: List[ChangeNotification]) -> Dict[str, Any]:
        """Send notifications using the broadcaster.

        Args:
            notifications: List of notifications to send

        Returns:
            Delivery results dictionary
        """
        all_results: Dict[str, Any] = {}

        # Create notification batch
        batch = NotificationBatch(notifications=notifications)
        batch.total_recipients = sum(len(n.recipients) for n in notifications)

        logger.info(
            f"Sending batch of {len(notifications)} notifications to {batch.total_recipients} recipients"
        )

        # Send notifications concurrently
        tasks = []
        for notification in notifications:
            task = self.broadcaster.broadcast_notification(notification)
            tasks.append(task)

        # Wait for all notifications to be sent
        notification_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        successful_deliveries = 0
        failed_deliveries = 0

        for i, result in enumerate(notification_results):
            if isinstance(result, dict):
                all_results[f"notification_{i}"] = result

                # Count successful and failed deliveries
                for delivery_result in result.values():
                    if hasattr(delivery_result, "status"):
                        if delivery_result.status.value in ("delivered", "sent"):
                            successful_deliveries += 1
                        elif delivery_result.status.value == "failed":
                            failed_deliveries += 1
            elif isinstance(result, Exception):
                logger.error(f"Notification {i} failed: {result}")
                all_results[f"notification_{i}"] = DeliveryResult(
                    recipient_id=f"notification_{i}",
                    channel=NotificationChannel.EMAIL,
                    status=DeliveryStatus.FAILED,
                    message="Notification failed",
                    error_details=str(result),
                )
                failed_deliveries += len(notifications[i].recipients)

        # Update batch statistics
        batch.successful_deliveries = successful_deliveries
        batch.failed_deliveries = failed_deliveries
        batch.processed_at = notifications[0].timestamp if notifications else None

        logger.info(
            f"Batch completed: {successful_deliveries} successful, {failed_deliveries} failed"
        )

        return {
            "batch_id": batch.batch_id,
            "total_notifications": len(notifications),
            "total_recipients": batch.total_recipients,
            "successful_deliveries": successful_deliveries,
            "failed_deliveries": failed_deliveries,
            "delivery_details": all_results,
        }

    def add_stakeholder_contact(
        self, fogis_person_id: str, channel: str, address: str, verified: bool = False
    ) -> bool:
        """Add contact information for a stakeholder.

        Args:
            fogis_person_id: FOGIS person ID
            channel: Notification channel (email, discord, webhook, etc.)
            address: Contact address
            verified: Whether contact is verified

        Returns:
            True if added successfully, False otherwise
        """
        try:
            from .models.notification_models import NotificationChannel

            # Get or create stakeholder
            stakeholder = self.stakeholder_manager.get_stakeholder_by_fogis_id(fogis_person_id)
            if not stakeholder:
                # Create basic stakeholder
                stakeholder_data = {
                    "personid": fogis_person_id,
                    "personnamn": "Unknown",
                }
                stakeholder = self.stakeholder_manager.create_stakeholder_from_referee_data(
                    stakeholder_data
                )

            # Add contact information
            channel_enum = NotificationChannel(channel)
            return self.stakeholder_manager.add_contact_info(
                stakeholder.stakeholder_id, channel_enum, address, verified
            )

        except Exception as e:
            logger.error(f"Error adding stakeholder contact: {e}")
            return False

    def get_stakeholder_statistics(self) -> Dict[str, Any]:
        """Get stakeholder statistics.

        Returns:
            Stakeholder statistics dictionary
        """
        return self.stakeholder_manager.get_statistics()

    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get delivery statistics.

        Returns:
            Delivery statistics dictionary
        """
        return self.broadcaster.get_delivery_statistics()

    def test_notification_channels(self) -> Dict[str, bool]:
        """Test all configured notification channels.

        Returns:
            Dictionary mapping channel names to test results
        """
        if not self.enabled:
            return {"enabled": False}

        results = {}

        # Test email
        try:
            # Email testing would require actual SMTP connection
            results["email"] = (
                self.config.get("channels", {}).get("email", {}).get("enabled", False)
            )
        except Exception as e:
            logger.error(f"Email test failed: {e}")
            results["email"] = False

        # Test Discord
        try:
            results["discord"] = self.broadcaster.discord_client.test_webhook()
        except Exception as e:
            logger.error(f"Discord test failed: {e}")
            results["discord"] = False

        # Test webhook
        try:
            results["webhook"] = self.broadcaster.webhook_client.test_webhook()
        except Exception as e:
            logger.error(f"Webhook test failed: {e}")
            results["webhook"] = False

        return results

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of notification service.

        Returns:
            Health status dictionary
        """
        return {
            "enabled": self.enabled,
            "stakeholder_count": len(self.stakeholder_manager.get_all_stakeholders()),
            "queue_size": len(self.notification_queue),
            "delivery_stats": self.get_delivery_statistics(),
            "channel_tests": self.test_notification_channels(),
        }
