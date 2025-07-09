"""Tests for the persistent app module with calendar sync integration."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from src.app_persistent import PersistentMatchListProcessorApp


class TestPersistentMatchListProcessorAppPersistent:
    """Test cases for the persistent PersistentMatchListProcessorApp with calendar sync."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def app_instance(self, temp_dir):
        """Create an app instance with mocked dependencies."""
        with (
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.MatchComparator"),
            patch("src.app_persistent.MatchProcessor"),
        ):

            app = PersistentMatchListProcessorApp(data_dir=temp_dir)
            return app

    def test_init(self, temp_dir):
        """Test app initialization."""
        with (
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.MatchComparator"),
            patch("src.app_persistent.MatchProcessor"),
        ):

            app = PersistentMatchListProcessorApp(data_dir=temp_dir)
            assert app.data_dir == temp_dir

    @patch("src.app_persistent.requests.post")
    def test_trigger_calendar_sync_success(self, mock_post, app_instance):
        """Test successful calendar sync trigger."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response

        # Set environment variable
        with patch.dict(os.environ, {"CALENDAR_SYNC_URL": "http://test-calendar:5003/sync"}):
            app_instance._trigger_calendar_sync()

        # Verify the request was made correctly
        mock_post.assert_called_once_with("http://test-calendar:5003/sync", json={}, timeout=60)

    def test_signal_handler(self, app_instance):
        """Test signal handler sets running to False."""
        import signal

        # Initially running should be True
        assert app_instance.running is True

        # Call signal handler
        app_instance._signal_handler(signal.SIGTERM, None)

        # Should set running to False
        assert app_instance.running is False
