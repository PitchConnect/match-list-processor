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
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    @patch("src.core.unified_processor.MatchProcessor")
    @patch("src.core.unified_processor.MatchDataManager")
    def test_end_to_end_processing_with_new_matches(
        self,
        mock_data_manager,
        mock_match_processor,
        mock_phonebook,
        mock_storage,
        mock_avatar,
        mock_api,
    ):
        """Test end-to-end processing when new matches are detected."""
        # Setup mocks
        mock_api_instance = mock_api.return_value
        mock_api_instance.get_matches.return_value = self.sample_matches

        mock_data_manager_instance = mock_data_manager.return_value
        mock_data_manager_instance.load_previous_matches.return_value = []

        mock_match_processor_instance = mock_match_processor.return_value
        mock_match_processor_instance.process_match.return_value = {
            "success": True,
            "description_url": "http://example.com/desc.txt",
            "group_info_url": "http://example.com/info.txt",
            "avatar_url": "http://example.com/avatar.png",
            "error_message": None,
        }

        mock_phonebook_instance = mock_phonebook.return_value
        mock_phonebook_instance.sync_contacts.return_value = True

        # Create unified processor
        processor = UnifiedMatchProcessor(self.temp_matches_file)

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify results
        self.assertTrue(result.processed)
        self.assertIsNotNone(result.changes)
        self.assertTrue(result.changes.has_changes)
        self.assertEqual(len(result.changes.new_matches), 1)
        self.assertEqual(len(result.errors), 0)

        # Verify API was called
        mock_api_instance.get_matches.assert_called_once()

        # Verify match processing was called
        mock_match_processor_instance.process_match.assert_called_once()

        # Verify calendar sync was triggered
        mock_phonebook_instance.sync_contacts.assert_called_once()

        # Verify matches were saved
        mock_data_manager_instance.save_current_matches.assert_called_once()

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    @patch("src.core.unified_processor.MatchProcessor")
    @patch("src.core.unified_processor.MatchDataManager")
    def test_end_to_end_processing_no_changes(
        self,
        mock_data_manager,
        mock_match_processor,
        mock_phonebook,
        mock_storage,
        mock_avatar,
        mock_api,
    ):
        """Test end-to-end processing when no changes are detected."""
        # Setup mocks - same matches for previous and current
        mock_api_instance = mock_api.return_value
        mock_api_instance.get_matches.return_value = self.sample_matches

        mock_data_manager_instance = mock_data_manager.return_value
        mock_data_manager_instance.load_previous_matches.return_value = self.sample_matches

        # Save initial matches to file
        with open(self.temp_matches_file, "w") as f:
            json.dump(self.sample_matches, f)

        # Create unified processor
        processor = UnifiedMatchProcessor(self.temp_matches_file)

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify results
        self.assertFalse(result.processed)
        self.assertIsNotNone(result.changes)
        self.assertFalse(result.changes.has_changes)
        self.assertEqual(len(result.errors), 0)

        # Verify API was called
        mock_api_instance.get_matches.assert_called_once()

        # Verify match processing was NOT called (no changes)
        mock_match_processor.return_value.process_match.assert_not_called()

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    @patch("src.core.unified_processor.MatchProcessor")
    @patch("src.core.unified_processor.MatchDataManager")
    def test_end_to_end_processing_with_match_updates(
        self,
        mock_data_manager,
        mock_match_processor,
        mock_phonebook,
        mock_storage,
        mock_avatar,
        mock_api,
    ):
        """Test end-to-end processing when matches are updated."""
        # Setup previous matches
        previous_matches = [self.sample_matches[0].copy()]

        # Setup current matches with time change
        current_matches = [self.sample_matches[0].copy()]
        current_matches[0]["avsparkstid"] = "16:00"  # Changed time

        # Save previous matches to file
        with open(self.temp_matches_file, "w") as f:
            json.dump(previous_matches, f)

        # Setup mocks
        mock_api_instance = mock_api.return_value
        mock_api_instance.get_matches.return_value = current_matches

        mock_data_manager_instance = mock_data_manager.return_value
        mock_data_manager_instance.load_previous_matches.return_value = previous_matches

        mock_match_processor_instance = mock_match_processor.return_value
        mock_match_processor_instance.process_match.return_value = {
            "success": True,
            "description_url": "http://example.com/desc.txt",
            "group_info_url": "http://example.com/info.txt",
            "avatar_url": "http://example.com/avatar.png",
            "error_message": None,
        }

        mock_phonebook_instance = mock_phonebook.return_value
        mock_phonebook_instance.sync_contacts.return_value = True

        # Create unified processor
        processor = UnifiedMatchProcessor(self.temp_matches_file)

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify results
        self.assertTrue(result.processed)
        self.assertIsNotNone(result.changes)
        self.assertTrue(result.changes.has_changes)
        self.assertEqual(len(result.changes.updated_matches), 1)
        self.assertEqual(len(result.errors), 0)

        # Verify change details
        change_record = result.changes.updated_matches[0]
        self.assertEqual(change_record["match_id"], "12345")
        self.assertTrue(change_record["changes"]["basic"])
        self.assertEqual(change_record["previous"]["time"], "14:00")
        self.assertEqual(change_record["current"]["time"], "16:00")

    @patch("src.web.health_server.create_health_server")
    @patch.dict(
        os.environ,
        {
            "RUN_MODE": "oneshot",
            "PROCESSOR_MODE": "unified",
            "PYTEST_CURRENT_TEST": "test_unified_app_initialization",
        },
    )
    def test_unified_app_initialization(self, mock_health_server):
        """Test unified app initialization."""
        mock_health_server.return_value = MagicMock()

        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):

            app = UnifiedMatchListProcessorApp()

            self.assertIsNotNone(app.unified_processor)
            self.assertEqual(app.run_mode, "oneshot")
            self.assertTrue(app.running)
            self.assertTrue(app.is_test_mode)  # Verify test mode detection
            self.assertIsNone(app.health_server)  # Health server should be None in test mode

    @patch("src.web.health_server.create_health_server")
    @patch.dict(
        os.environ,
        {
            "RUN_MODE": "service",
            "SERVICE_INTERVAL": "60",
            "PYTEST_CURRENT_TEST": "test_unified_app_service_mode_config",
        },
    )
    def test_unified_app_service_mode_config(self, mock_health_server):
        """Test unified app service mode configuration."""
        mock_health_server.return_value = MagicMock()

        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):

            app = UnifiedMatchListProcessorApp()

            self.assertEqual(app.run_mode, "service")
            self.assertEqual(app.service_interval, 60)
            self.assertTrue(app.is_test_mode)  # Verify test mode detection

    @patch("src.web.health_server.create_health_server")
    @patch.dict(
        os.environ,
        {
            "RUN_MODE": "service",
            "SERVICE_INTERVAL": "5",
            "PYTEST_CURRENT_TEST": "test_service_mode_safe_execution",
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
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
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
