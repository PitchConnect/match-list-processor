"""Tests for the persistent app module."""

import os
from unittest.mock import Mock, patch

import pytest

from src.app_persistent import PersistentMatchListProcessorApp


class TestPersistentMatchListProcessorApp:
    """Test cases for the PersistentMatchListProcessorApp."""

    @pytest.fixture
    def mock_services(self):
        """Create mock services for testing."""
        return {
            "api_client": Mock(),
            "phonebook_service": Mock(),
            "data_manager": Mock(),
            "match_comparator": Mock(),
            "match_processor": Mock(),
            "avatar_service": Mock(),
            "storage_service": Mock(),
        }

    @pytest.fixture
    def app_instance(self, mock_services):
        """Create an app instance with mocked dependencies."""
        with (
            patch(
                "src.app_persistent.DockerNetworkApiClient",
                return_value=mock_services["api_client"],
            ),
            patch(
                "src.app_persistent.FogisPhonebookSyncService",
                return_value=mock_services["phonebook_service"],
            ),
            patch(
                "src.app_persistent.MatchDataManager",
                return_value=mock_services["data_manager"],
            ),
            patch(
                "src.app_persistent.MatchComparator",
                return_value=mock_services["match_comparator"],
            ),
            patch(
                "src.app_persistent.MatchProcessor",
                return_value=mock_services["match_processor"],
            ),
            patch(
                "src.app_persistent.WhatsAppAvatarService",
                return_value=mock_services["avatar_service"],
            ),
            patch(
                "src.app_persistent.GoogleDriveStorageService",
                return_value=mock_services["storage_service"],
            ),
        ):

            app = PersistentMatchListProcessorApp()
            return app

    def test_init(self):
        """Test app initialization."""
        with (
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.MatchComparator"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
        ):

            app = PersistentMatchListProcessorApp()
            assert app.running is True

    def test_app_attributes(self, app_instance):
        """Test that app instance has expected attributes."""
        assert hasattr(app_instance, "running")
        assert hasattr(app_instance, "run_mode")
        assert hasattr(app_instance, "service_interval")
        assert app_instance.running is True

    @patch("src.app_persistent.sys.exit")
    def test_signal_handler(self, mock_exit, app_instance):
        """Test signal handler sets running to False."""
        import signal

        # Initially running should be True
        assert app_instance.running is True

        # Call signal handler
        app_instance._signal_handler(signal.SIGTERM, None)

        # Should set running to False
        assert app_instance.running is False
        # Should call sys.exit(0)
        mock_exit.assert_called_once_with(0)

    def test_service_mode_configuration(self):
        """Test service mode configuration from environment."""
        with (
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.MatchComparator"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch.dict(os.environ, {"RUN_MODE": "service", "SERVICE_INTERVAL": "600"}),
        ):

            app = PersistentMatchListProcessorApp()
            assert app.run_mode == "service"
            assert app.service_interval == 600

    def test_oneshot_mode_configuration(self):
        """Test oneshot mode configuration (default)."""
        with (
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.MatchComparator"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch.dict(os.environ, {}, clear=True),
        ):

            app = PersistentMatchListProcessorApp()
            assert app.run_mode == "oneshot"
            assert app.service_interval == 300  # default
