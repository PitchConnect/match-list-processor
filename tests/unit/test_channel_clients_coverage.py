"""Comprehensive tests for channel clients to reach 90% coverage."""

from unittest.mock import Mock, patch

import pytest

from src.notifications.broadcaster.channel_clients.discord_client import DiscordNotificationClient
from src.notifications.broadcaster.channel_clients.email_client import EmailNotificationClient
from src.notifications.broadcaster.channel_clients.webhook_client import WebhookNotificationClient
from src.notifications.models.notification_models import (
    ChangeNotification,
    DeliveryStatus,
    NotificationChannel,
    NotificationPriority,
    NotificationRecipient,
)


@pytest.mark.unit
class TestEmailClientCoverage:
    """Comprehensive tests for EmailNotificationClient to increase coverage from 33% to 80%+."""

    def test_email_client_initialization_enabled(self):
        """Test email client initialization when enabled."""
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "test@gmail.com",
            "smtp_password": "password",
            "email_from": "fogis@example.com",
            "use_tls": True,
            "enabled": True,
        }

        client = EmailNotificationClient(config)

        # Verify configuration
        assert client.smtp_server == "smtp.gmail.com"
        assert client.smtp_port == 587
        assert client.smtp_username == "test@gmail.com"
        assert client.smtp_password == "password"
        assert client.email_from == "fogis@example.com"
        assert client.use_tls is True
        assert client.enabled is True
        assert client.template_engine is not None

    def test_email_client_initialization_disabled(self):
        """Test email client initialization when disabled."""
        config = {"enabled": False}

        with patch(
            "src.notifications.broadcaster.channel_clients.email_client.logger"
        ) as mock_logger:
            client = EmailNotificationClient(config)

            # Verify disabled state
            assert client.enabled is False
            mock_logger.info.assert_called_with("Email notifications are disabled")

    def test_email_client_initialization_defaults(self):
        """Test email client initialization with default values."""
        config = {}

        client = EmailNotificationClient(config)

        # Verify defaults
        assert client.smtp_server == "localhost"
        assert client.smtp_port == 587
        assert client.smtp_username == ""
        assert client.smtp_password == ""
        assert client.email_from == "fogis@example.com"
        assert client.use_tls is True
        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_send_notification_disabled(self):
        """Test sending notification when client is disabled."""
        config = {"enabled": False}
        client = EmailNotificationClient(config)

        # Create test notification and recipient
        notification = ChangeNotification(change_summary="Test change")
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
        )

        # Send notification
        result = await client.send_notification(notification, recipient)

        # Verify disabled result
        assert result.recipient_id == "test-123"
        assert result.channel == NotificationChannel.EMAIL
        assert result.status == DeliveryStatus.FAILED
        assert "disabled" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test successful email notification sending."""
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "test@gmail.com",
            "smtp_password": "password",
            "enabled": True,
        }
        client = EmailNotificationClient(config)

        # Mock the sync email sending method
        with patch.object(client, "_send_email_sync") as mock_send:
            # Create test notification and recipient
            notification = ChangeNotification(
                change_summary="Referee change",
                change_category="referee_change",
                priority=NotificationPriority.HIGH,
                match_context={"lag1namn": "Team A", "lag2namn": "Team B"},
            )
            recipient = NotificationRecipient(
                stakeholder_id="test-456",
                name="Test User",
                channel=NotificationChannel.EMAIL,
                address="test@example.com",
            )

            # Send notification
            result = await client.send_notification(notification, recipient)

            # Verify success
            assert result.recipient_id == "test-456"
            assert result.channel == NotificationChannel.EMAIL
            assert result.status == DeliveryStatus.DELIVERED
            assert "successfully" in result.message

            # Verify sync method was called
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_exception(self):
        """Test email notification sending with exception."""
        config = {"enabled": True}
        client = EmailNotificationClient(config)

        # Mock the sync email sending method to raise exception
        with (
            patch.object(client, "_send_email_sync", side_effect=Exception("SMTP Error")),
            patch(
                "src.notifications.broadcaster.channel_clients.email_client.logger"
            ) as mock_logger,
        ):
            # Create test notification and recipient
            notification = ChangeNotification(change_summary="Test change")
            recipient = NotificationRecipient(
                stakeholder_id="test-error",
                name="Error User",
                channel=NotificationChannel.EMAIL,
                address="error@example.com",
            )

            # Send notification
            result = await client.send_notification(notification, recipient)

            # Verify error handling
            assert result.recipient_id == "test-error"
            assert result.channel == NotificationChannel.EMAIL
            assert result.status == DeliveryStatus.FAILED
            assert "failed" in result.message
            assert "SMTP Error" in result.error_details

            # Verify error was logged
            mock_logger.error.assert_called()

    def test_send_email_sync_with_tls_and_auth(self):
        """Test synchronous email sending with TLS and authentication."""
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "test@gmail.com",
            "smtp_password": "password",
            "email_from": "sender@example.com",
            "use_tls": True,
            "enabled": True,
        }
        client = EmailNotificationClient(config)

        # Mock SMTP server
        with (
            patch(
                "src.notifications.broadcaster.channel_clients.email_client.smtplib.SMTP"
            ) as mock_smtp_class,
            patch(
                "src.notifications.broadcaster.channel_clients.email_client.logger"
            ) as mock_logger,
        ):
            mock_server = Mock()
            mock_smtp_class.return_value.__enter__.return_value = mock_server

            # Send email
            client._send_email_sync(
                "recipient@example.com",
                "Test Subject",
                "<html>Test HTML</html>",
                "Test Text",
            )

            # Verify SMTP operations
            mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@gmail.com", "password")
            mock_server.send_message.assert_called_once()

            # Verify success logging
            mock_logger.info.assert_called()

    def test_send_email_sync_without_tls_and_auth(self):
        """Test synchronous email sending without TLS and authentication."""
        config = {
            "smtp_server": "localhost",
            "smtp_port": 25,
            "use_tls": False,
            "enabled": True,
        }
        client = EmailNotificationClient(config)

        # Mock SMTP server
        with patch(
            "src.notifications.broadcaster.channel_clients.email_client.smtplib.SMTP"
        ) as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_class.return_value.__enter__.return_value = mock_server

            # Send email
            client._send_email_sync(
                "recipient@example.com",
                "Test Subject",
                "<html>Test HTML</html>",
                "Test Text",
            )

            # Verify SMTP operations (no TLS, no auth)
            mock_smtp_class.assert_called_once_with("localhost", 25)
            mock_server.starttls.assert_not_called()
            mock_server.login.assert_not_called()
            mock_server.send_message.assert_called_once()

    def test_generate_subject_with_priority(self):
        """Test email subject generation with different priorities."""
        config = {"enabled": True}
        client = EmailNotificationClient(config)

        # Test different priorities
        priorities_and_emojis = [
            (NotificationPriority.CRITICAL, "🚨"),
            (NotificationPriority.HIGH, "⚠️"),
            (NotificationPriority.MEDIUM, "📢"),
            (NotificationPriority.LOW, "ℹ️"),
        ]

        for priority, expected_emoji in priorities_and_emojis:
            notification = ChangeNotification(
                change_summary="Test change",
                priority=priority,
                match_context={"lag1namn": "Home Team", "lag2namn": "Away Team"},
            )

            subject = client._generate_subject(notification)

            # Verify subject format
            assert expected_emoji in subject
            assert "FOGIS:" in subject
            assert "Test change" in subject
            assert "Home Team vs Away Team" in subject

    def test_generate_subject_unknown_teams(self):
        """Test email subject generation with unknown teams."""
        config = {"enabled": True}
        client = EmailNotificationClient(config)

        notification = ChangeNotification(
            change_summary="Test change", match_context={}  # No team info
        )

        subject = client._generate_subject(notification)

        # Verify unknown teams handling
        assert "Unknown vs Unknown" in subject

    def test_generate_html_body(self):
        """Test HTML email body generation."""
        config = {"enabled": True}
        client = EmailNotificationClient(config)

        notification = ChangeNotification(
            change_summary="Referee change",
            priority=NotificationPriority.HIGH,
            match_context={
                "lag1namn": "Team A",
                "lag2namn": "Team B",
                "matchdate": "2024-01-15",
                "matchtime": "19:00",
            },
        )
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
        )

        html_body = client._generate_html_body(notification, recipient)

        # Verify HTML content
        assert isinstance(html_body, str)
        assert len(html_body) > 0
        assert "Team A" in html_body or "Team B" in html_body

    def test_generate_text_body(self):
        """Test plain text email body generation."""
        config = {"enabled": True}
        client = EmailNotificationClient(config)

        notification = ChangeNotification(
            change_summary="Time change",
            field_changes=[{"field": "matchtime", "old_value": "18:00", "new_value": "19:00"}],
        )
        recipient = NotificationRecipient(
            stakeholder_id="test-456",
            name="Test User",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
        )

        text_body = client._generate_text_body(notification, recipient)

        # Verify text content
        assert isinstance(text_body, str)
        assert len(text_body) > 0
        assert "Time change" in text_body


@pytest.mark.unit
class TestDiscordClientCoverage:
    """Comprehensive tests for DiscordNotificationClient to increase coverage from 25% to 80%+."""

    def test_discord_client_initialization(self):
        """Test discord client initialization."""
        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "bot_username": "FOGIS Bot",
            "bot_avatar_url": "https://example.com/avatar.png",
            "enabled": True,
        }

        client = DiscordNotificationClient(config)

        # Verify configuration
        assert client.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert client.bot_username == "FOGIS Bot"
        assert client.bot_avatar_url == "https://example.com/avatar.png"
        assert client.enabled is True

    def test_discord_client_initialization_defaults(self):
        """Test discord client initialization with defaults."""
        config = {}

        client = DiscordNotificationClient(config)

        # Verify defaults
        assert client.webhook_url == ""
        assert client.bot_username == "FOGIS Bot"
        assert client.bot_avatar_url == ""
        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_send_notification_disabled(self):
        """Test sending notification when discord client is disabled."""
        config = {"enabled": False}
        client = DiscordNotificationClient(config)

        notification = ChangeNotification(change_summary="Test change")
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.DISCORD,
            address="https://discord.com/webhook",
        )

        result = await client.send_notification(notification, recipient)

        # Verify disabled result
        assert result.status == DeliveryStatus.FAILED
        assert "disabled" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test successful discord notification sending."""
        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "enabled": True,
        }
        client = DiscordNotificationClient(config)

        # Mock urllib request
        with patch(
            "src.notifications.broadcaster.channel_clients.discord_client.urlopen"
        ) as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b'{"id": "message_123"}'
            mock_response.getcode.return_value = 200
            mock_response.status = 200  # Add status attribute
            mock_urlopen.return_value.__enter__.return_value = mock_response

            notification = ChangeNotification(
                change_summary="Referee change", priority=NotificationPriority.HIGH
            )
            recipient = NotificationRecipient(
                stakeholder_id="test-456",
                name="Discord User",
                channel=NotificationChannel.DISCORD,
                address="https://discord.com/webhook",
            )

            result = await client.send_notification(notification, recipient)

            # Verify success
            assert result.status == DeliveryStatus.DELIVERED
            assert "successfully" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_http_error(self):
        """Test discord notification sending with HTTP error."""
        config = {
            "webhook_url": "https://discord.com/api/webhooks/123/abc",
            "enabled": True,
        }
        client = DiscordNotificationClient(config)

        # Mock HTTP request with error
        with (
            patch(
                "src.notifications.broadcaster.channel_clients.discord_client.urlopen"
            ) as mock_urlopen,
            patch(
                "src.notifications.broadcaster.channel_clients.discord_client.logger"
            ) as mock_logger,
        ):
            # Mock HTTP error
            from urllib.error import HTTPError

            mock_urlopen.side_effect = HTTPError(
                url="https://discord.com/webhook",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            )

            notification = ChangeNotification(change_summary="Test change")
            recipient = NotificationRecipient(
                stakeholder_id="test-error",
                name="Error User",
                channel=NotificationChannel.DISCORD,
                address="https://discord.com/webhook",
            )

            result = await client.send_notification(notification, recipient)

            # Verify error handling
            assert result.status == DeliveryStatus.FAILED
            assert "failed" in result.message
            mock_logger.error.assert_called()


@pytest.mark.unit
class TestWebhookClientCoverage:
    """Comprehensive tests for WebhookNotificationClient to increase coverage from 30% to 80%+."""

    def test_webhook_client_initialization(self):
        """Test webhook client initialization."""
        config = {
            "timeout": 30,
            "retry_attempts": 3,
            "headers": {"Content-Type": "application/json"},
            "enabled": True,
        }

        client = WebhookNotificationClient(config)

        # Verify configuration
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.custom_headers == {"Content-Type": "application/json"}
        assert client.enabled is True

    def test_webhook_client_initialization_defaults(self):
        """Test webhook client initialization with defaults."""
        config = {}

        client = WebhookNotificationClient(config)

        # Verify defaults
        assert client.timeout == 30
        assert client.retry_attempts == 3
        assert client.custom_headers == {}
        assert client.enabled is False

    @pytest.mark.asyncio
    async def test_send_notification_disabled(self):
        """Test sending notification when webhook client is disabled."""
        config = {"enabled": False}
        client = WebhookNotificationClient(config)

        notification = ChangeNotification(change_summary="Test change")
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.WEBHOOK,
            address="https://example.com/webhook",
        )

        result = await client.send_notification(notification, recipient)

        # Verify disabled result
        assert result.status == DeliveryStatus.FAILED
        assert "disabled" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test successful webhook notification sending."""
        config = {"enabled": True, "timeout": 30}
        client = WebhookNotificationClient(config)

        # Mock HTTP request
        with patch(
            "src.notifications.broadcaster.channel_clients.webhook_client.urlopen"
        ) as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b"OK"
            mock_response.getcode.return_value = 200
            mock_response.status = 200  # Add status attribute
            mock_urlopen.return_value.__enter__.return_value = mock_response

            notification = ChangeNotification(change_summary="Venue change")
            recipient = NotificationRecipient(
                stakeholder_id="test-789",
                name="Webhook User",
                channel=NotificationChannel.WEBHOOK,
                address="https://example.com/webhook",
            )

            result = await client.send_notification(notification, recipient)

            # Verify success
            assert result.status == DeliveryStatus.DELIVERED
            assert "successfully" in result.message

    @pytest.mark.asyncio
    async def test_send_notification_with_retry(self):
        """Test webhook notification sending with retry logic."""
        config = {"enabled": True, "retry_attempts": 2}
        client = WebhookNotificationClient(config)

        # Mock HTTP request with multiple failures to test retry logic
        with patch(
            "src.notifications.broadcaster.channel_clients.webhook_client.urlopen"
        ) as mock_urlopen:
            from urllib.error import HTTPError

            # All calls fail to test retry logic
            mock_urlopen.side_effect = HTTPError(
                url="https://example.com/webhook",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            )

            notification = ChangeNotification(change_summary="Test change")
            recipient = NotificationRecipient(
                stakeholder_id="test-retry",
                name="Retry User",
                channel=NotificationChannel.WEBHOOK,
                address="https://example.com/webhook",
            )

            result = await client.send_notification(notification, recipient)

            # Verify retry logic was executed (multiple calls to urlopen)
            assert mock_urlopen.call_count == 2  # Should have tried 2 times
            assert result.status == DeliveryStatus.FAILED  # Should fail after retries

    @pytest.mark.asyncio
    async def test_send_notification_max_retries_exceeded(self):
        """Test webhook notification sending when max retries exceeded."""
        config = {"enabled": True, "retry_attempts": 1}
        client = WebhookNotificationClient(config)

        # Mock HTTP request to always fail
        with patch(
            "src.notifications.broadcaster.channel_clients.webhook_client.urlopen"
        ) as mock_urlopen:
            from urllib.error import HTTPError

            # Always fail with HTTP error
            mock_urlopen.side_effect = HTTPError(
                url="https://example.com/webhook",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            )

            notification = ChangeNotification(change_summary="Test change")
            recipient = NotificationRecipient(
                stakeholder_id="test-fail",
                name="Fail User",
                channel=NotificationChannel.WEBHOOK,
                address="https://example.com/webhook",
            )

            result = await client.send_notification(notification, recipient)

            # Verify failure after retries
            assert result.status == DeliveryStatus.FAILED
            assert "failed" in result.message
