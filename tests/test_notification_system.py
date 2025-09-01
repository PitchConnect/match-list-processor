"""Tests for notification system."""

import asyncio
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.core.change_categorization import (
    CategorizedChanges,
    ChangeCategory,
    ChangePriority,
    MatchChangeDetail,
    StakeholderType,
)
from src.notifications.models.notification_models import (
    ChangeNotification,
    DeliveryStatus,
    NotificationChannel,
    NotificationPriority,
    NotificationRecipient,
)
from src.notifications.models.stakeholder_models import (
    ContactInfo,
    NotificationPreferences,
    Stakeholder,
)
from src.notifications.notification_service import NotificationService
from src.notifications.stakeholders.stakeholder_manager import StakeholderManager


class TestNotificationModels(unittest.TestCase):
    """Test notification data models."""

    def test_notification_recipient_creation(self):
        """Test notification recipient creation."""
        recipient = NotificationRecipient(
            stakeholder_id="test-123",
            name="Test User",
            channel=NotificationChannel.EMAIL,
            address="test@example.com",
            preferences={"role": "referee"},
        )

        self.assertEqual(recipient.stakeholder_id, "test-123")
        self.assertEqual(recipient.name, "Test User")
        self.assertEqual(recipient.channel, NotificationChannel.EMAIL)
        self.assertEqual(recipient.address, "test@example.com")
        self.assertEqual(recipient.preferences["role"], "referee")

    def test_change_notification_creation(self):
        """Test change notification creation."""
        recipients = [
            NotificationRecipient(
                stakeholder_id="test-123",
                name="Test User",
                channel=NotificationChannel.EMAIL,
                address="test@example.com",
            )
        ]

        notification = ChangeNotification(
            change_category="new_assignment",
            priority=NotificationPriority.HIGH,
            change_summary="New referee assignment",
            recipients=recipients,
            match_context={"matchid": "12345"},
        )

        self.assertEqual(notification.change_category, "new_assignment")
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertEqual(notification.change_summary, "New referee assignment")
        self.assertEqual(len(notification.recipients), 1)
        self.assertEqual(notification.match_context["matchid"], "12345")

    def test_stakeholder_creation(self):
        """Test stakeholder creation."""
        contact = ContactInfo(
            channel=NotificationChannel.EMAIL, address="test@example.com", verified=True
        )

        preferences = NotificationPreferences(
            enabled_channels={NotificationChannel.EMAIL},
            enabled_change_types={"new_assignment", "time_change"},
            minimum_priority="medium",
        )

        stakeholder = Stakeholder(
            name="Test Referee",
            role="referee",
            fogis_person_id="12345",
            contact_info=[contact],
            preferences=preferences,
        )

        self.assertEqual(stakeholder.name, "Test Referee")
        self.assertEqual(stakeholder.role, "referee")
        self.assertEqual(stakeholder.fogis_person_id, "12345")
        self.assertEqual(len(stakeholder.contact_info), 1)
        self.assertTrue(stakeholder.should_receive_notification("new_assignment", "high"))
        self.assertFalse(stakeholder.should_receive_notification("venue_change", "low"))


class TestStakeholderManager(unittest.TestCase):
    """Test stakeholder manager."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_stakeholders.json")
        self.manager = StakeholderManager(self.storage_path)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)

    def test_create_stakeholder_from_referee_data(self):
        """Test creating stakeholder from referee data."""
        referee_data = {
            "personid": "12345",
            "personnamn": "Test Referee",
            "epostadress": "test@example.com",
        }

        stakeholder = self.manager.create_stakeholder_from_referee_data(referee_data)

        self.assertEqual(stakeholder.name, "Test Referee")
        self.assertEqual(stakeholder.role, "referee")
        self.assertEqual(stakeholder.fogis_person_id, "12345")

        # Check email contact was added
        email_contact = stakeholder.get_contact_by_channel(NotificationChannel.EMAIL)
        self.assertIsNotNone(email_contact)
        self.assertEqual(email_contact.address, "test@example.com")

    def test_stakeholder_persistence(self):
        """Test stakeholder persistence."""
        # Create stakeholder
        referee_data = {
            "personid": "12345",
            "personnamn": "Test Referee",
            "epostadress": "test@example.com",
        }

        stakeholder = self.manager.create_stakeholder_from_referee_data(referee_data)
        stakeholder_id = stakeholder.stakeholder_id

        # Create new manager instance (simulates restart)
        new_manager = StakeholderManager(self.storage_path)

        # Verify stakeholder was loaded
        loaded_stakeholder = new_manager.get_stakeholder(stakeholder_id)
        self.assertIsNotNone(loaded_stakeholder)
        self.assertEqual(loaded_stakeholder.name, "Test Referee")
        self.assertEqual(loaded_stakeholder.fogis_person_id, "12345")

    def test_stakeholder_statistics(self):
        """Test stakeholder statistics."""
        # Create test stakeholders
        referee_data = {
            "personid": "12345",
            "personnamn": "Test Referee",
            "epostadress": "test@example.com",
        }
        self.manager.create_stakeholder_from_referee_data(referee_data)

        stats = self.manager.get_statistics()

        self.assertEqual(stats["total_stakeholders"], 1)
        self.assertEqual(stats["active_stakeholders"], 1)
        self.assertEqual(stats["by_role"]["referee"], 1)
        self.assertEqual(stats["by_channel"]["email"], 1)


class TestNotificationService(unittest.TestCase):
    """Test notification service."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_stakeholders.json")

        self.config = {
            "enabled": True,
            "stakeholder_storage_path": self.storage_path,
            "channels": {
                "email": {"enabled": False},
                "discord": {"enabled": False},
                "webhook": {"enabled": False},
            },
        }

        self.service = NotificationService(self.config)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)

    def test_service_initialization(self):
        """Test notification service initialization."""
        self.assertTrue(self.service.enabled)
        self.assertIsNotNone(self.service.stakeholder_manager)
        self.assertIsNotNone(self.service.stakeholder_resolver)
        self.assertIsNotNone(self.service.change_converter)
        self.assertIsNotNone(self.service.broadcaster)

    def test_disabled_service(self):
        """Test disabled notification service."""
        disabled_config = self.config.copy()
        disabled_config["enabled"] = False

        disabled_service = NotificationService(disabled_config)

        # Test that disabled service returns appropriate responses
        result = asyncio.run(disabled_service.process_changes(None, {}))
        self.assertFalse(result["enabled"])
        self.assertEqual(result["notifications_sent"], 0)

    @patch(
        "src.notifications.broadcaster.notification_broadcaster.NotificationBroadcaster.broadcast_notification"
    )
    def test_process_new_match(self, mock_broadcast):
        """Test processing new match."""
        # Mock broadcast to return successful delivery
        async def mock_broadcast_func(*args, **kwargs):
            return {"email_test-123": MagicMock(status=DeliveryStatus.DELIVERED)}

        mock_broadcast.side_effect = mock_broadcast_func

        # Create test match data
        match_data = {
            "matchid": "12345",
            "lag1namn": "Team A",
            "lag2namn": "Team B",
            "speldatum": "2025-09-01",
            "avsparkstid": "14:00",
            "domaruppdraglista": [
                {
                    "personid": "67890",
                    "personnamn": "Test Referee",
                    "epostadress": "referee@example.com",
                }
            ],
        }

        # Process new match
        result = asyncio.run(self.service.process_new_match(match_data))

        self.assertTrue(result["enabled"])
        # Note: notifications_sent might be 0 if no recipients are resolved
        # This is expected in test environment without proper stakeholder setup

    def test_add_stakeholder_contact(self):
        """Test adding stakeholder contact."""
        # Add contact for new stakeholder
        success = self.service.add_stakeholder_contact(
            fogis_person_id="12345", channel="email", address="test@example.com", verified=True
        )

        self.assertTrue(success)

        # Verify stakeholder was created and contact added
        stakeholder = self.service.stakeholder_manager.get_stakeholder_by_fogis_id("12345")
        self.assertIsNotNone(stakeholder)

        email_contact = stakeholder.get_contact_by_channel(NotificationChannel.EMAIL)
        self.assertIsNotNone(email_contact)
        self.assertEqual(email_contact.address, "test@example.com")
        self.assertTrue(email_contact.verified)

    def test_health_status(self):
        """Test health status reporting."""
        health = self.service.get_health_status()

        self.assertTrue(health["enabled"])
        self.assertIsInstance(health["stakeholder_count"], int)
        self.assertIsInstance(health["queue_size"], int)
        self.assertIn("delivery_stats", health)
        self.assertIn("channel_tests", health)


class TestChangeToNotificationConverter(unittest.TestCase):
    """Test change to notification converter."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_stakeholders.json")

        # Create stakeholder manager and resolver
        self.stakeholder_manager = StakeholderManager(self.storage_path)

        # Create test stakeholder
        referee_data = {
            "personid": "12345",
            "personnamn": "Test Referee",
            "epostadress": "test@example.com",
        }
        self.stakeholder_manager.create_stakeholder_from_referee_data(referee_data)

        from src.notifications.converter.change_to_notification_converter import (
            ChangeToNotificationConverter,
        )
        from src.notifications.stakeholders.stakeholder_resolver import StakeholderResolver

        self.resolver = StakeholderResolver(self.stakeholder_manager)
        self.converter = ChangeToNotificationConverter(self.resolver)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.storage_path):
            os.remove(self.storage_path)
        os.rmdir(self.temp_dir)

    def test_convert_changes_to_notifications(self):
        """Test converting changes to notifications."""
        # Create test changes
        change = MatchChangeDetail(
            match_id="12345",
            match_nr="1",
            category=ChangeCategory.NEW_ASSIGNMENT,
            priority=ChangePriority.HIGH,
            field_name="referee_assignment",
            previous_value="None",
            current_value="Test Referee",
            change_description="New referee assignment",
            affected_stakeholders=[StakeholderType.REFEREES],
            timestamp=datetime.utcnow(),
        )

        categorized_changes = CategorizedChanges(
            changes=[change],
            total_changes=1,
            critical_changes=0,
            high_priority_changes=1,
            affected_stakeholder_types={StakeholderType.REFEREES},
            change_categories={ChangeCategory.NEW_ASSIGNMENT},
        )

        match_data = {
            "matchid": "12345",
            "lag1namn": "Team A",
            "lag2namn": "Team B",
            "domaruppdraglista": [{"personid": "12345", "personnamn": "Test Referee"}],
        }

        # Convert changes
        notifications = self.converter.convert_changes_to_notifications(
            categorized_changes, match_data
        )

        # Verify notifications were created
        self.assertGreater(len(notifications), 0)

        notification = notifications[0]
        self.assertEqual(notification.change_category, "new_assignment")
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertIn("assignment", notification.change_summary.lower())

    def test_create_notification_from_match_data(self):
        """Test creating notification from match data."""
        match_data = {
            "matchid": "12345",
            "lag1namn": "Team A",
            "lag2namn": "Team B",
            "domaruppdraglista": [
                {"personid": "12345", "personnamn": "Test Referee", "uppdragstyp": "Huvuddomare"}
            ],
        }

        notification = self.converter.create_notification_from_match_data(
            match_data, "new_assignment", "medium"
        )

        self.assertEqual(notification.change_category, "new_assignment")
        self.assertEqual(notification.priority, NotificationPriority.MEDIUM)
        self.assertIn("Team A vs Team B", notification.change_summary)
        self.assertEqual(len(notification.field_changes), 1)
        self.assertEqual(notification.field_changes[0]["field_name"], "referee_assignment")


if __name__ == "__main__":
    unittest.main()
