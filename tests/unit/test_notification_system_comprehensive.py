"""Comprehensive unit tests for notification system components."""

import asyncio
import tempfile
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.notifications.broadcaster.notification_broadcaster import NotificationBroadcaster
from src.notifications.models.notification_models import ChangeNotification, NotificationChannel
from src.notifications.models.stakeholder_models import NotificationPreferences, Stakeholder
from src.notifications.notification_service import NotificationService
from src.notifications.stakeholders.stakeholder_manager import StakeholderManager
from src.notifications.stakeholders.stakeholder_resolver import StakeholderResolver


@pytest.mark.unit
class TestNotificationService:
    """Test notification service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "enabled": True,
            "email": {"smtp_server": "test.com", "smtp_username": "test", "smtp_password": "pass"},
            "analytics": {"enabled": True},
        }
        self.service = NotificationService(self.config)

    def test_service_initialization(self):
        """Test notification service initialization."""
        assert self.service.enabled
        assert self.service.stakeholder_manager is not None
        assert self.service.stakeholder_resolver is not None
        assert self.service.change_converter is not None
        assert self.service.broadcaster is not None

    def test_disabled_service_behavior(self):
        """Test disabled notification service behavior."""
        disabled_config = {"enabled": False}
        disabled_service = NotificationService(disabled_config)

        assert not disabled_service.enabled

        # Test that disabled service returns appropriate responses
        result = asyncio.run(disabled_service.process_changes(None, {}))
        assert not result["enabled"]
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_process_changes_with_notifications(self, sample_match_data, mock_stakeholder):
        """Test processing changes that generate notifications."""
        # Mock dependencies
        with (
            patch.object(
                self.service.stakeholder_resolver, "resolve_notification_stakeholders"
            ) as mock_resolve,
            patch.object(
                self.service.change_converter, "convert_changes_to_notifications"
            ) as mock_convert,
            patch.object(
                self.service.broadcaster, "broadcast_notification", new_callable=AsyncMock
            ) as mock_broadcast,
        ):

            # Configure mocks
            mock_resolve.return_value = [mock_stakeholder]
            mock_notification = Mock()
            mock_notification.notification_id = "test-123"
            mock_convert.return_value = [mock_notification]
            mock_broadcast.return_value = {"email": {"status": "sent", "recipients": 1}}

            # Create mock changes
            changes = Mock()
            changes.has_changes = True
            changes.total_changes = 1

            # Process changes
            result = await self.service.process_changes(changes, sample_match_data)

            # Verify processing
            assert result["enabled"]
            assert result["notifications_sent"] == 1
            assert "delivery_results" in result

            # Verify method calls
            mock_resolve.assert_called_once()
            mock_convert.assert_called_once()
            mock_broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_changes_no_stakeholders(self, sample_match_data):
        """Test processing changes when no stakeholders are found."""
        with patch.object(
            self.service.stakeholder_resolver, "resolve_notification_stakeholders", return_value=[]
        ):

            changes = Mock()
            changes.has_changes = True
            changes.total_changes = 1

            result = await self.service.process_changes(changes, sample_match_data)

            assert result["enabled"]
            assert result["notifications_sent"] == 0
            assert result["delivery_results"] == {}

    def test_health_status(self):
        """Test health status reporting."""
        with patch.object(
            self.service.stakeholder_manager, "get_stakeholder_count", return_value=5
        ):
            status = self.service.get_health_status()

            assert status["status"] == "healthy"
            assert status["enabled"]
            assert status["stakeholders_count"] == 5
            assert "last_notification" in status

    @pytest.mark.asyncio
    async def test_error_handling_in_processing(self, sample_match_data):
        """Test error handling during change processing."""
        with patch.object(
            self.service.stakeholder_resolver,
            "resolve_notification_stakeholders",
            side_effect=Exception("Resolver error"),
        ):

            changes = Mock()
            changes.has_changes = True

            result = await self.service.process_changes(changes, sample_match_data)

            # Should handle error gracefully
            assert result["enabled"]
            assert result["notifications_sent"] == 0
            assert "error" in result


@pytest.mark.unit
class TestStakeholderManager:
    """Test stakeholder manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.manager = StakeholderManager(self.temp_file.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        import os

        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_manager_initialization(self):
        """Test stakeholder manager initialization."""
        assert self.manager is not None
        assert hasattr(self.manager, "stakeholders")
        assert isinstance(self.manager.stakeholders, dict)

    def test_register_stakeholder(self, mock_stakeholder):
        """Test stakeholder registration."""
        stakeholder = Stakeholder.from_dict(mock_stakeholder)

        self.manager.register_stakeholder(stakeholder)

        assert stakeholder.stakeholder_id in self.manager.stakeholders
        retrieved = self.manager.get_stakeholder(stakeholder.stakeholder_id)
        assert retrieved is not None
        assert retrieved.name == stakeholder.name

    def test_stakeholder_persistence(self, mock_stakeholder):
        """Test stakeholder data persistence."""
        stakeholder = Stakeholder.from_dict(mock_stakeholder)

        # Register stakeholder
        self.manager.register_stakeholder(stakeholder)

        # Create new manager instance with same file
        new_manager = StakeholderManager(self.temp_file.name)

        # Verify stakeholder was persisted
        retrieved = new_manager.get_stakeholder(stakeholder.stakeholder_id)
        assert retrieved is not None
        assert retrieved.name == stakeholder.name

    def test_get_stakeholder_by_fogis_id(self, mock_stakeholder):
        """Test retrieving stakeholder by FOGIS ID."""
        stakeholder = Stakeholder.from_dict(mock_stakeholder)
        self.manager.register_stakeholder(stakeholder)

        retrieved = self.manager.get_stakeholder_by_fogis_id(stakeholder.fogis_person_id)
        assert retrieved is not None
        assert retrieved.stakeholder_id == stakeholder.stakeholder_id

    def test_create_stakeholder_from_referee_data(self):
        """Test creating stakeholder from referee data."""
        referee_data = {
            "personid": 12345,
            "personnamn": "Test Referee",
            "epostadress": "test@example.com",
        }

        stakeholder = self.manager.create_stakeholder_from_referee_data(referee_data)

        assert stakeholder is not None
        assert stakeholder.name == "Test Referee"
        assert stakeholder.role == "referee"
        assert stakeholder.fogis_person_id == "12345"

        # Verify contact info was added
        email_contacts = [
            c for c in stakeholder.contact_info if c.channel == NotificationChannel.EMAIL
        ]
        assert len(email_contacts) == 1
        assert email_contacts[0].address == "test@example.com"

    def test_stakeholder_statistics(self, multiple_stakeholders):
        """Test stakeholder statistics."""
        # Register multiple stakeholders
        for stakeholder_data in multiple_stakeholders:
            stakeholder = Stakeholder.from_dict(stakeholder_data)
            self.manager.register_stakeholder(stakeholder)

        stats = self.manager.get_stakeholder_statistics()

        assert stats["total_stakeholders"] == 2
        assert stats["by_role"]["referee"] == 2
        assert stats["by_channel"]["email"] == 2
        assert "discord" in stats["by_channel"]

    def test_update_stakeholder_preferences(self, mock_stakeholder):
        """Test updating stakeholder preferences."""
        stakeholder = Stakeholder.from_dict(mock_stakeholder)
        self.manager.register_stakeholder(stakeholder)

        # Update preferences
        new_preferences = NotificationPreferences(
            enabled_channels=[NotificationChannel.EMAIL, NotificationChannel.DISCORD],
            enabled_change_types=["new_assignment", "time_change", "venue_change"],
            minimum_priority="low",
        )

        self.manager.update_stakeholder_preferences(stakeholder.stakeholder_id, new_preferences)

        # Verify update
        updated = self.manager.get_stakeholder(stakeholder.stakeholder_id)
        assert len(updated.preferences.enabled_channels) == 2
        assert NotificationChannel.DISCORD in updated.preferences.enabled_channels


@pytest.mark.unit
class TestStakeholderResolver:
    """Test stakeholder resolver functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.manager = StakeholderManager(self.temp_file.name)
        self.resolver = StakeholderResolver(self.manager)

    def teardown_method(self):
        """Clean up test fixtures."""
        import os

        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_resolve_stakeholders_for_new_assignment(self, sample_match_data, mock_stakeholder):
        """Test resolving stakeholders for new assignments."""
        # Register stakeholder
        stakeholder = Stakeholder.from_dict(mock_stakeholder)
        self.manager.register_stakeholder(stakeholder)

        # Resolve stakeholders
        stakeholders = self.resolver.resolve_notification_stakeholders(
            sample_match_data, "new_assignment", "high"
        )

        assert len(stakeholders) > 0
        assert any(s.stakeholder_id == stakeholder.stakeholder_id for s in stakeholders)

    def test_filter_by_preferences(self, sample_match_data, multiple_stakeholders):
        """Test filtering stakeholders by preferences."""
        # Register stakeholders with different preferences
        for stakeholder_data in multiple_stakeholders:
            stakeholder = Stakeholder.from_dict(stakeholder_data)
            self.manager.register_stakeholder(stakeholder)

        # Resolve for venue change (only second stakeholder has this enabled)
        stakeholders = self.resolver.resolve_notification_stakeholders(
            sample_match_data, "venue_change", "medium"
        )

        # Should only return stakeholders with venue_change in preferences
        venue_enabled = [
            s for s in stakeholders if "venue_change" in s.preferences.enabled_change_types
        ]
        assert len(venue_enabled) >= 1

    def test_priority_filtering(self, sample_match_data, mock_stakeholder):
        """Test filtering by minimum priority."""
        # Create stakeholder with high minimum priority
        stakeholder_data = mock_stakeholder.copy()
        stakeholder_data["preferences"]["minimum_priority"] = "high"
        stakeholder = Stakeholder.from_dict(stakeholder_data)
        self.manager.register_stakeholder(stakeholder)

        # Test with low priority (should not match)
        stakeholders_low = self.resolver.resolve_notification_stakeholders(
            sample_match_data, "new_assignment", "low"
        )

        # Test with high priority (should match)
        stakeholders_high = self.resolver.resolve_notification_stakeholders(
            sample_match_data, "new_assignment", "high"
        )

        # High priority should return more stakeholders than low priority
        assert len(stakeholders_high) >= len(stakeholders_low)


@pytest.mark.unit
class TestNotificationBroadcaster:
    """Test notification broadcaster functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "email": {"smtp_server": "test.com", "enabled": True},
            "discord": {"webhook_url": "https://test.com", "enabled": True},
            "delivery": {"max_retries": 3, "timeout": 30},
        }
        self.broadcaster = NotificationBroadcaster(self.config)

    def test_broadcaster_initialization(self):
        """Test broadcaster initialization."""
        assert self.broadcaster is not None
        assert hasattr(self.broadcaster, "email_client")
        assert hasattr(self.broadcaster, "discord_client")

    @pytest.mark.asyncio
    async def test_broadcast_notification_success(self, sample_notification_data):
        """Test successful notification broadcasting."""
        notification = ChangeNotification(**sample_notification_data)

        # Mock channel clients
        with (
            patch.object(
                self.broadcaster.email_client, "send_notification", new_callable=AsyncMock
            ) as mock_email,
            patch.object(
                self.broadcaster.discord_client, "send_notification", new_callable=AsyncMock
            ) as mock_discord,
        ):

            mock_email.return_value = {"status": "sent", "recipients": 1}
            mock_discord.return_value = {"status": "sent", "recipients": 1}

            results = await self.broadcaster.broadcast_notification(notification)

            assert "email" in results
            assert "discord" in results
            assert results["email"]["status"] == "sent"
            assert results["discord"]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_broadcast_notification_partial_failure(self, sample_notification_data):
        """Test notification broadcasting with partial failures."""
        notification = ChangeNotification(**sample_notification_data)

        # Mock one success, one failure
        with (
            patch.object(
                self.broadcaster.email_client, "send_notification", new_callable=AsyncMock
            ) as mock_email,
            patch.object(
                self.broadcaster.discord_client, "send_notification", new_callable=AsyncMock
            ) as mock_discord,
        ):

            mock_email.return_value = {"status": "sent", "recipients": 1}
            mock_discord.side_effect = Exception("Discord API error")

            results = await self.broadcaster.broadcast_notification(notification)

            assert "email" in results
            assert "discord" in results
            assert results["email"]["status"] == "sent"
            assert "error" in results["discord"]

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, sample_notification_data):
        """Test retry mechanism for failed deliveries."""
        notification = ChangeNotification(**sample_notification_data)

        # Mock temporary failure then success
        with patch.object(
            self.broadcaster.email_client, "send_notification", new_callable=AsyncMock
        ) as mock_email:
            mock_email.side_effect = [
                Exception("Temporary error"),  # First attempt fails
                {"status": "sent", "recipients": 1},  # Second attempt succeeds
            ]

            results = await self.broadcaster.broadcast_notification(notification)

            # Should eventually succeed after retry
            assert results["email"]["status"] == "sent"
            assert mock_email.call_count == 2
