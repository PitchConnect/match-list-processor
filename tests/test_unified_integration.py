"""Integration tests for the unified processor system."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from src.app_unified import UnifiedMatchListProcessorApp
from src.core.unified_processor import UnifiedMatchProcessor


class TestUnifiedIntegration(unittest.TestCase):
    """Integration tests for the unified processor system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_matches_file = os.path.join(self.temp_dir, "test_matches.json")

        # Sample match data
        self.sample_matches = [
            {
                "matchid": "12345",
                "matchnr": "1",
                "speldatum": "2025-09-01",
                "avsparkstid": "14:00",
                "lag1lagid": "100",
                "lag1namn": "Team A",
                "lag2lagid": "200",
                "lag2namn": "Team B",
                "anlaggningnamn": "Stadium A",
                "lag1foreningid": "1001",
                "lag2foreningid": "2001",
                "domaruppdraglista": [
                    {
                        "domareid": "ref1",
                        "personnamn": "John Referee",
                        "domarrollnamn": "Huvuddomare",
                        "epostadress": "john@example.com",
                        "mobiltelefon": "123456789",
                    }
                ],
            }
        ]

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_matches_file):
            os.remove(self.temp_matches_file)
        os.rmdir(self.temp_dir)

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.MatchProcessor")
    @patch("src.core.unified_processor.MatchDataManager")
    def test_unified_app_service_mode_config(
        self, mock_data_manager, mock_processor, mock_storage, mock_avatar, mock_api_client
    ):
        """Test unified app service mode configuration."""

        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):

            app = UnifiedMatchListProcessorApp()

            self.assertEqual(app.run_mode, "oneshot")  # Default mode
            self.assertEqual(app.service_interval, 300)  # Default 5 minutes
            self.assertTrue(app.is_test_mode)  # Verify test mode detection

    @patch("src.web.health_server.create_health_server")
    @patch.dict(
        os.environ,
        {
            "RUN_MODE": "service",
            "SERVICE_INTERVAL": "5",
            "PYTEST_CURRENT_TEST": "test_service_mode_safe_execution",
            "CI": "true",
        },
    )
    def test_service_mode_safe_execution(self, mock_health_server):
        """Test that service mode runs safely in test environment without hanging."""
        mock_health_server.return_value = MagicMock()

        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient") as mock_api,
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):
            # Setup API mock
            mock_api.return_value.fetch_matches_list.return_value = self.sample_matches

            app = UnifiedMatchListProcessorApp()

            # Verify test mode is detected
            self.assertTrue(app.is_test_mode)
            self.assertEqual(app.run_mode, "service")

            # This should run once and exit (not hang) due to test mode detection
            app._run_as_service()

            # Verify it completed without hanging
            self.assertTrue(app.running)  # Should still be True since we didn't call shutdown

    def test_change_detector_file_persistence(self):
        """Test that change detector properly persists and loads match data."""
        from src.core.change_detector import GranularChangeDetector

        detector = GranularChangeDetector(self.temp_matches_file)

        # Save matches
        detector.save_current_matches(self.sample_matches)

        # Verify file exists
        self.assertTrue(os.path.exists(self.temp_matches_file))

        # Load matches
        loaded_matches = detector.load_previous_matches()

        # Verify loaded matches
        self.assertEqual(len(loaded_matches), 1)
        self.assertEqual(loaded_matches[0]["matchid"], "12345")
        self.assertEqual(loaded_matches[0]["lag1namn"], "Team A")


if __name__ == "__main__":
    unittest.main()
