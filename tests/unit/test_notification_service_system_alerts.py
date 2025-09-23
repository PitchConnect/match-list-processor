"""Unit tests for notification service system alert functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.notifications.models.notification_models import NotificationChannel, NotificationPriority
from src.notifications.notification_service import NotificationService


class TestNotificationServiceSystemAlerts:
    """Test system alert functionality in notification service."""

    @pytest.fixture
    def mock_stakeholder_manager(self):
        """Create mock stakeholder manager."""
        manager = Mock()

        # Create mock admin stakeholder
        admin_stakeholder = Mock()
        admin_stakeholder.stakeholder_id = "admin-1"
        admin_stakeholder.role = "Administrator"
        admin_stakeholder.name = "System Administrator"
        admin_stakeholder.contact_info = [
            Mock(
                channel=NotificationChannel.EMAIL,
                address="admin@example.com",
                active=True,
            ),
            Mock(channel=NotificationChannel.DISCORD, address="webhook-url", active=True),
        ]

        manager.get_all_stakeholders.return_value = [admin_stakeholder]
        return manager

    @pytest.fixture
    def mock_broadcaster(self):
        """Create mock notification broadcaster."""
        broadcaster = AsyncMock()
        broadcaster.broadcast_notification.return_value = {
            "status": "success",
            "delivered": 2,
            "failed": 0,
        }
        return broadcaster

    @pytest.fixture
    def notification_service(self, mock_stakeholder_manager, mock_broadcaster):
        """Create notification service with mocked dependencies."""
        config = {"enabled": True, "stakeholder_storage_path": "test_stakeholders.json"}
        service = NotificationService(config)
        service.stakeholder_manager = mock_stakeholder_manager
        service.broadcaster = mock_broadcaster
        service.enabled = True
        return service

    @pytest.mark.asyncio
    async def test_send_system_alert_critical(self, notification_service):
        """Test sending critical system alert."""
        alert_data = {
            "alert_type": "authentication_failure",
            "service": "fogis-api-client",
            "severity": "critical",
            "message": "FOGIS API authentication failed",
            "error_details": "HTTP 401: Unauthorized",
            "timestamp": "2025-01-01T12:00:00Z",
            "recovery_actions": ["Check credentials", "Verify account status"],
            "affected_functionality": ["Match processing suspended"],
        }

        result = await notification_service.send_system_alert(alert_data)

        assert result["enabled"] is True
        assert result["notifications_sent"] == 1
        assert result["alert_type"] == "authentication_failure"
        assert result["service"] == "fogis-api-client"
        assert result["severity"] == "critical"

        # Verify broadcaster was called
        notification_service.broadcaster.broadcast_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_system_alert_disabled_service(self, notification_service):
        """Test system alert when service is disabled."""
        notification_service.enabled = False

        alert_data = {
            "alert_type": "test_alert",
            "service": "test-service",
            "severity": "critical",
            "message": "Test message",
        }

        result = await notification_service.send_system_alert(alert_data)

        assert result["enabled"] is False
        assert result["notifications_sent"] == 0
        notification_service.broadcaster.broadcast_notification.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_system_alert_no_recipients(self, notification_service):
        """Test system alert when no recipients are found."""
        # Mock empty stakeholder list
        notification_service.stakeholder_manager.get_all_stakeholders.return_value = []

        alert_data = {
            "alert_type": "test_alert",
            "service": "test-service",
            "severity": "critical",
            "message": "Test message",
        }

        result = await notification_service.send_system_alert(alert_data)

        assert result["enabled"] is True
        assert result["notifications_sent"] == 0
        notification_service.broadcaster.broadcast_notification.assert_not_called()

    def test_create_system_alert_notification_critical(self, notification_service):
        """Test creating critical system alert notification."""
        alert_data = {
            "alert_type": "authentication_failure",
            "service": "fogis-api-client",
            "severity": "critical",
            "message": "FOGIS API authentication failed",
            "error_details": "HTTP 401: Unauthorized",
            "timestamp": "2025-01-01T12:00:00Z",
            "recovery_actions": ["Check credentials"],
            "affected_functionality": ["Match processing suspended"],
        }

        notification = notification_service._create_system_alert_notification(alert_data)

        assert "🚨 fogis-api-client Alert: authentication_failure" in notification.change_summary
        assert "FOGIS API authentication failed" in notification.change_summary
        assert notification.priority == NotificationPriority.CRITICAL
        assert notification.match_context["alert_type"] == "authentication_failure"
        assert notification.match_context["service"] == "fogis-api-client"
        assert notification.match_context["severity"] == "critical"
        assert len(notification.recipients) == 2  # email + discord

    def test_create_system_alert_notification_severity_mapping(self, notification_service):
        """Test severity to priority mapping."""
        test_cases = [
            ("critical", NotificationPriority.CRITICAL),
            ("high", NotificationPriority.HIGH),
            ("medium", NotificationPriority.MEDIUM),
            ("low", NotificationPriority.LOW),
            ("unknown", NotificationPriority.MEDIUM),  # Default
        ]

        for severity, expected_priority in test_cases:
            alert_data = {
                "alert_type": "test_alert",
                "service": "test-service",
                "severity": severity,
                "message": "Test message",
            }

            notification = notification_service._create_system_alert_notification(alert_data)
            assert notification.priority == expected_priority

    def test_resolve_system_alert_recipients_admin_stakeholders(self, notification_service):
        """Test resolving recipients for admin stakeholders."""
        # Create mixed stakeholders
        admin_stakeholder = Mock()
        admin_stakeholder.stakeholder_id = "admin-1"
        admin_stakeholder.role = "Administrator"
        admin_stakeholder.name = "System Administrator"
        admin_stakeholder.contact_info = [
            Mock(
                channel=NotificationChannel.EMAIL,
                address="admin@example.com",
                active=True,
            )
        ]

        user_stakeholder = Mock()
        user_stakeholder.stakeholder_id = "user-1"
        user_stakeholder.role = "User"
        user_stakeholder.name = "Regular User"
        user_stakeholder.contact_info = [
            Mock(
                channel=NotificationChannel.EMAIL,
                address="user@example.com",
                active=True,
            )
        ]

        notification_service.stakeholder_manager.get_all_stakeholders.return_value = [
            admin_stakeholder,
            user_stakeholder,
        ]

        alert_data = {"severity": "high"}
        recipients = notification_service._resolve_system_alert_recipients(alert_data)

        # Should only include admin
        assert len(recipients) == 1
        assert recipients[0].stakeholder_id == "admin-1"

    def test_resolve_system_alert_recipients_critical_fallback(self, notification_service):
        """Test that critical alerts go to all stakeholders if no admins found."""
        # Create non-admin stakeholders
        user_stakeholder = Mock()
        user_stakeholder.stakeholder_id = "user-1"
        user_stakeholder.role = "User"
        user_stakeholder.name = "Regular User"
        user_stakeholder.contact_info = [
            Mock(
                channel=NotificationChannel.EMAIL,
                address="user@example.com",
                active=True,
            )
        ]

        notification_service.stakeholder_manager.get_all_stakeholders.return_value = [
            user_stakeholder
        ]

        alert_data = {"severity": "critical"}
        recipients = notification_service._resolve_system_alert_recipients(alert_data)

        # Should include all stakeholders for critical alerts
        assert len(recipients) == 1
        assert recipients[0].stakeholder_id == "user-1"

    def test_resolve_system_alert_recipients_disabled_contacts(self, notification_service):
        """Test that disabled contacts are excluded."""
        admin_stakeholder = Mock()
        admin_stakeholder.stakeholder_id = "admin-1"
        admin_stakeholder.role = "Administrator"
        admin_stakeholder.name = "System Administrator"
        admin_stakeholder.contact_info = [
            Mock(
                channel=NotificationChannel.EMAIL,
                address="admin@example.com",
                active=True,
            ),
            Mock(
                channel=NotificationChannel.DISCORD, address="webhook-url", active=False
            ),  # Disabled
        ]

        notification_service.stakeholder_manager.get_all_stakeholders.return_value = [
            admin_stakeholder
        ]

        alert_data = {"severity": "high"}
        recipients = notification_service._resolve_system_alert_recipients(alert_data)

        # Should only include enabled contact
        assert len(recipients) == 1
        assert recipients[0].channel == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_send_system_alert_error_handling(self, notification_service):
        """Test error handling in send_system_alert."""
        # Make _send_notifications raise an exception
        with patch.object(
            notification_service,
            "_send_notifications",
            side_effect=Exception("Test error"),
        ):
            alert_data = {
                "alert_type": "test_alert",
                "service": "test-service",
                "severity": "critical",
                "message": "Test message",
            }

            result = await notification_service.send_system_alert(alert_data)

            assert result["enabled"] is True
            assert result["notifications_sent"] == 0
            assert "error" in result
            assert result["error"] == "Test error"

    def test_create_system_alert_notification_metadata(self, notification_service):
        """Test that all metadata is properly included in notification."""
        alert_data = {
            "alert_type": "service_failure",
            "service": "google-drive-service",
            "severity": "high",
            "message": "Service unavailable",
            "error_details": "HTTP 503: Service Unavailable",
            "timestamp": "2025-01-01T12:00:00Z",
            "recovery_actions": ["Check service status", "Retry later"],
            "affected_functionality": ["File uploads suspended"],
        }

        notification = notification_service._create_system_alert_notification(alert_data)

        context = notification.match_context
        assert context["alert_type"] == "service_failure"
        assert context["service"] == "google-drive-service"
        assert context["severity"] == "high"
        assert context["timestamp"] == "2025-01-01T12:00:00Z"
        assert context["error_details"] == "HTTP 503: Service Unavailable"
        assert context["recovery_actions"] == ["Check service status", "Retry later"]
        assert context["affected_functionality"] == ["File uploads suspended"]

    @pytest.mark.asyncio
    async def test_send_system_alert_delivery_results(self, notification_service):
        """Test that delivery results are included in response."""
        mock_delivery_results = {
            "notification_0": {"status": "success", "delivered": 2, "failed": 0}
        }

        with patch.object(
            notification_service,
            "_send_notifications",
            return_value=mock_delivery_results,
        ):
            alert_data = {
                "alert_type": "test_alert",
                "service": "test-service",
                "severity": "critical",
                "message": "Test message",
            }

            result = await notification_service.send_system_alert(alert_data)

            assert result["delivery_results"] == mock_delivery_results
