"""Comprehensive tests for NotificationBroadcaster to reach 90% coverage."""

from unittest.mock import AsyncMock

import pytest

from src.notifications.broadcaster.notification_broadcaster import NotificationBroadcaster
from src.notifications.models.notification_models import (
    ChangeNotification,
    DeliveryResult,
    DeliveryStatus,
    NotificationChannel,
    NotificationRecipient,
)


@pytest.mark.unit
class TestNotificationBroadcasterCoverage:
    """Comprehensive tests for NotificationBroadcaster to increase coverage."""

    def test_broadcaster_initialization(self):
        """Test broadcaster initialization with full config."""
        config = {
            "email": {"smtp_server": "smtp.example.com", "enabled": True},
            "discord": {"webhook_url": "https://discord.com/webhook", "enabled": True},
            "webhook": {"timeout": 30, "enabled": True},
        }

        broadcaster = NotificationBroadcaster(config)

        # Verify initialization
        assert broadcaster.config == config
        assert broadcaster.email_client is not None
        assert broadcaster.discord_client is not None
        assert broadcaster.webhook_client is not None
        assert broadcaster.delivery_stats["total_sent"] == 0
        assert broadcaster.delivery_stats["total_delivered"] == 0
        assert broadcaster.delivery_stats["total_failed"] == 0
        assert broadcaster.delivery_stats["by_channel"] == {}

    @pytest.mark.asyncio
    async def test_broadcast_notification_no_recipients(self):
        """Test broadcasting notification with no recipients."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create notification without recipients
        notification = ChangeNotification(
            change_summary="Test change",
            change_category="referee_change",
            recipients=[],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify empty results for no recipients
        assert results == {}

    @pytest.mark.asyncio
    async def test_broadcast_notification_email_success(self):
        """Test successful email notification broadcasting."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock email client
        mock_delivery_result = DeliveryResult(
            recipient_id="test-123",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            message="Email sent successfully",
        )
        broadcaster.email_client.send_notification = AsyncMock(return_value=mock_delivery_result)

        # Create notification with email recipient
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
        )
        notification = ChangeNotification(
            change_summary="Test change",
            change_category="referee_change",
            recipients=[recipient],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify email was sent
        broadcaster.email_client.send_notification.assert_called_once_with(notification, recipient)
        assert len(results) == 1
        assert "email_test-123" in results
        assert results["email_test-123"].status == DeliveryStatus.DELIVERED

        # Verify delivery stats were updated
        assert broadcaster.delivery_stats["total_sent"] == 1
        assert broadcaster.delivery_stats["total_delivered"] == 1
        assert broadcaster.delivery_stats["total_failed"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_notification_discord_success(self):
        """Test successful Discord notification broadcasting."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock discord client
        mock_delivery_result = DeliveryResult(
            recipient_id="test-456",
            channel=NotificationChannel.DISCORD,
            status=DeliveryStatus.DELIVERED,
            message="Discord message sent successfully",
        )
        broadcaster.discord_client.send_notification = AsyncMock(return_value=mock_delivery_result)

        # Create notification with discord recipient
        recipient = NotificationRecipient(
            stakeholder_id="test-456",
            name="Discord User",
            channel=NotificationChannel.DISCORD,
            address="https://discord.com/api/webhooks/123/abc",
        )
        notification = ChangeNotification(
            change_summary="Test change",
            change_category="time_change",
            recipients=[recipient],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify discord was sent
        broadcaster.discord_client.send_notification.assert_called_once_with(
            notification, recipient
        )
        assert len(results) == 1
        assert "discord_test-456" in results
        assert results["discord_test-456"].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_broadcast_notification_webhook_success(self):
        """Test successful webhook notification broadcasting."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock webhook client
        mock_delivery_result = DeliveryResult(
            recipient_id="test-789",
            channel=NotificationChannel.WEBHOOK,
            status=DeliveryStatus.DELIVERED,
            message="Webhook sent successfully",
        )
        broadcaster.webhook_client.send_notification = AsyncMock(return_value=mock_delivery_result)

        # Create notification with webhook recipient
        recipient = NotificationRecipient(
            stakeholder_id="test-789",
            name="Webhook User",
            channel=NotificationChannel.WEBHOOK,
            address="https://example.com/webhook",
        )
        notification = ChangeNotification(
            change_summary="Test change",
            change_category="venue_change",
            recipients=[recipient],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify webhook was sent
        broadcaster.webhook_client.send_notification.assert_called_once_with(
            notification, recipient
        )
        assert len(results) == 1
        assert "webhook_test-789" in results
        assert results["webhook_test-789"].status == DeliveryStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_broadcast_notification_mixed_channels(self):
        """Test broadcasting to multiple channels simultaneously."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock all clients
        email_result = DeliveryResult(
            recipient_id="email-user",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            message="Email sent",
        )
        discord_result = DeliveryResult(
            recipient_id="discord-user",
            channel=NotificationChannel.DISCORD,
            status=DeliveryStatus.DELIVERED,
            message="Discord sent",
        )
        webhook_result = DeliveryResult(
            recipient_id="webhook-user",
            channel=NotificationChannel.WEBHOOK,
            status=DeliveryStatus.DELIVERED,
            message="Webhook sent",
        )

        broadcaster.email_client.send_notification = AsyncMock(return_value=email_result)
        broadcaster.discord_client.send_notification = AsyncMock(return_value=discord_result)
        broadcaster.webhook_client.send_notification = AsyncMock(return_value=webhook_result)

        # Create notification with multiple recipients
        recipients = [
            NotificationRecipient(
                stakeholder_id="email-user",
                name="Email User",
                channel=NotificationChannel.EMAIL,
                address="email@example.com",
            ),
            NotificationRecipient(
                stakeholder_id="discord-user",
                name="Discord User",
                channel=NotificationChannel.DISCORD,
                address="https://discord.com/webhook",
            ),
            NotificationRecipient(
                stakeholder_id="webhook-user",
                name="Webhook User",
                channel=NotificationChannel.WEBHOOK,
                address="https://example.com/webhook",
            ),
        ]
        notification = ChangeNotification(
            change_summary="Multi-channel test",
            change_category="batch_change",
            recipients=recipients,
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify all channels were used
        broadcaster.email_client.send_notification.assert_called_once()
        broadcaster.discord_client.send_notification.assert_called_once()
        broadcaster.webhook_client.send_notification.assert_called_once()

        # Verify results
        assert len(results) == 3
        assert "email_email-user" in results
        assert "discord_discord-user" in results
        assert "webhook_webhook-user" in results

        # Verify delivery stats
        assert broadcaster.delivery_stats["total_sent"] == 3
        assert broadcaster.delivery_stats["total_delivered"] == 3
        assert broadcaster.delivery_stats["total_failed"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_notification_email_failure(self):
        """Test email notification failure handling."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock email client to raise exception
        broadcaster.email_client.send_notification = AsyncMock(side_effect=Exception("SMTP Error"))

        # Create notification with email recipient
        recipient = NotificationRecipient(
            stakeholder_id="test-error",
            name="Error User",
            channel=NotificationChannel.EMAIL,
            address="error@example.com",
        )
        notification = ChangeNotification(
            change_summary="Error test",
            change_category="error_test",
            recipients=[recipient],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify error was handled
        assert len(results) == 1
        assert "email_test-error" in results
        assert results["email_test-error"].status == DeliveryStatus.FAILED
        assert "SMTP Error" in results["email_test-error"].error_details

        # Verify delivery stats
        assert broadcaster.delivery_stats["total_sent"] == 1
        assert broadcaster.delivery_stats["total_delivered"] == 0
        assert broadcaster.delivery_stats["total_failed"] == 1

    @pytest.mark.asyncio
    async def test_broadcast_notification_unsupported_channel(self):
        """Test handling of unsupported notification channel."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create notification with unsupported channel (SMS)
        recipient = NotificationRecipient(
            stakeholder_id="test-sms",
            name="SMS User",
            channel=NotificationChannel.SMS,
            address="+1234567890",
        )
        notification = ChangeNotification(
            change_summary="SMS test",
            change_category="sms_test",
            recipients=[recipient],
        )

        # Broadcast notification
        results = await broadcaster.broadcast_notification(notification)

        # Verify unsupported channel was handled (returns empty results)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_send_to_channel_exception_handling(self):
        """Test exception handling in _send_to_channel method."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Mock email client to raise exception during channel processing
        broadcaster.email_client.send_notification = AsyncMock(
            side_effect=Exception("Channel Error")
        )

        # Create notification
        recipient = NotificationRecipient(
            stakeholder_id="channel-error",
            name="Channel Error User",
            channel=NotificationChannel.EMAIL,
            address="channel@example.com",
        )
        notification = ChangeNotification(
            change_summary="Channel error test", recipients=[recipient]
        )

        # Test _send_to_channel directly
        results = await broadcaster._send_to_channel(
            notification, NotificationChannel.EMAIL, [recipient]
        )

        # Verify exception was handled and failed result created
        assert len(results) == 1
        assert "email_channel-error" in results
        assert results["email_channel-error"].status == DeliveryStatus.FAILED
        assert "Channel Error" in results["email_channel-error"].error_details

    def test_group_recipients_by_channel(self):
        """Test grouping recipients by notification channel."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create recipients with different channels
        recipients = [
            NotificationRecipient(
                stakeholder_id="email-1",
                name="Email User 1",
                channel=NotificationChannel.EMAIL,
                address="email1@example.com",
            ),
            NotificationRecipient(
                stakeholder_id="email-2",
                name="Email User 2",
                channel=NotificationChannel.EMAIL,
                address="email2@example.com",
            ),
            NotificationRecipient(
                stakeholder_id="discord-1",
                name="Discord User",
                channel=NotificationChannel.DISCORD,
                address="https://discord.com/webhook",
            ),
            NotificationRecipient(
                stakeholder_id="webhook-1",
                name="Webhook User",
                channel=NotificationChannel.WEBHOOK,
                address="https://example.com/webhook",
            ),
        ]

        # Group recipients
        grouped = broadcaster._group_recipients_by_channel(recipients)

        # Verify grouping
        assert len(grouped) == 3
        assert NotificationChannel.EMAIL in grouped
        assert NotificationChannel.DISCORD in grouped
        assert NotificationChannel.WEBHOOK in grouped
        assert len(grouped[NotificationChannel.EMAIL]) == 2
        assert len(grouped[NotificationChannel.DISCORD]) == 1
        assert len(grouped[NotificationChannel.WEBHOOK]) == 1

    def test_update_delivery_stats_success(self):
        """Test updating delivery statistics for successful deliveries."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create delivery results
        results = {
            "email_user1": DeliveryResult(
                recipient_id="user1",
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.DELIVERED,
                message="Success",
            ),
            "discord_user2": DeliveryResult(
                recipient_id="user2",
                channel=NotificationChannel.DISCORD,
                status=DeliveryStatus.DELIVERED,
                message="Success",
            ),
        }

        # Update stats
        broadcaster._update_delivery_stats(results)

        # Verify stats
        assert broadcaster.delivery_stats["total_sent"] == 2
        assert broadcaster.delivery_stats["total_delivered"] == 2
        assert broadcaster.delivery_stats["total_failed"] == 0
        assert "email" in broadcaster.delivery_stats["by_channel"]
        assert "discord" in broadcaster.delivery_stats["by_channel"]
        assert broadcaster.delivery_stats["by_channel"]["email"]["delivered"] == 1
        assert broadcaster.delivery_stats["by_channel"]["discord"]["delivered"] == 1

    def test_update_delivery_stats_failures(self):
        """Test updating delivery statistics for failed deliveries."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create delivery results with failures
        results = {
            "email_user1": DeliveryResult(
                recipient_id="user1",
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.FAILED,
                message="Failed",
                error_details="SMTP Error",
            ),
            "webhook_user2": DeliveryResult(
                recipient_id="user2",
                channel=NotificationChannel.WEBHOOK,
                status=DeliveryStatus.FAILED,
                message="Failed",
                error_details="HTTP 500",
            ),
        }

        # Update stats
        broadcaster._update_delivery_stats(results)

        # Verify stats
        assert broadcaster.delivery_stats["total_sent"] == 2
        assert broadcaster.delivery_stats["total_delivered"] == 0
        assert broadcaster.delivery_stats["total_failed"] == 2
        assert broadcaster.delivery_stats["by_channel"]["email"]["failed"] == 1
        assert broadcaster.delivery_stats["by_channel"]["webhook"]["failed"] == 1

    def test_update_notification_status(self):
        """Test updating notification delivery status."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Create notification
        notification = ChangeNotification(change_summary="Status test")

        # Create delivery results
        results = {
            "email_user1": DeliveryResult(
                recipient_id="user1",
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.DELIVERED,
                message="Success",
            ),
            "discord_user2": DeliveryResult(
                recipient_id="user2",
                channel=NotificationChannel.DISCORD,
                status=DeliveryStatus.FAILED,
                message="Failed",
            ),
        }

        # Update notification status
        broadcaster._update_notification_status(notification, results)

        # Verify notification status was updated
        assert len(notification.delivery_status) == 2
        assert notification.delivery_status["email_user1"] == DeliveryStatus.DELIVERED
        assert notification.delivery_status["discord_user2"] == DeliveryStatus.FAILED

    def test_get_delivery_statistics_with_data(self):
        """Test getting delivery statistics with existing data."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Set up some delivery stats
        broadcaster.delivery_stats = {
            "total_sent": 10,
            "total_delivered": 8,
            "total_failed": 2,
            "by_channel": {
                "email": {"sent": 6, "delivered": 5, "failed": 1},
                "discord": {"sent": 4, "delivered": 3, "failed": 1},
            },
        }

        # Get statistics
        stats = broadcaster.get_delivery_statistics()

        # Verify statistics calculation
        assert stats["total_sent"] == 10
        assert stats["total_delivered"] == 8
        assert stats["total_failed"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["by_channel"]["email"]["success_rate"] == 5 / 6
        assert stats["by_channel"]["discord"]["success_rate"] == 3 / 4

    def test_get_delivery_statistics_empty(self):
        """Test getting delivery statistics with no data."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Get statistics (should be empty)
        stats = broadcaster.get_delivery_statistics()

        # Verify empty statistics
        assert stats["total_sent"] == 0
        assert stats["total_delivered"] == 0
        assert stats["total_failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["by_channel"] == {}

    def test_reset_statistics(self):
        """Test resetting delivery statistics."""
        config = {"email": {}, "discord": {}, "webhook": {}}
        broadcaster = NotificationBroadcaster(config)

        # Set up some delivery stats
        broadcaster.delivery_stats = {
            "total_sent": 10,
            "total_delivered": 8,
            "total_failed": 2,
            "by_channel": {"email": {"sent": 5, "delivered": 4, "failed": 1}},
        }

        # Reset statistics
        broadcaster.reset_statistics()

        # Verify reset
        assert broadcaster.delivery_stats["total_sent"] == 0
        assert broadcaster.delivery_stats["total_delivered"] == 0
        assert broadcaster.delivery_stats["total_failed"] == 0
        assert broadcaster.delivery_stats["by_channel"] == {}
