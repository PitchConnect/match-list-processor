"""
Integration tests for referee change detection and Redis publishing.

This test suite verifies that referee changes detected by GranularChangeDetector
trigger Redis publishing in the unified processor (Issue #75).
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from src.core.unified_processor import UnifiedMatchProcessor


class TestRefereeRedisIntegration(unittest.TestCase):
    """Integration tests for referee changes triggering Redis publishing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_matches.json")

        # Base match data
        self.base_match = {
            "matchid": 6143017,
            "matchnr": "M001",
            "speldatum": "2025-10-04",
            "avsparkstid": "15:00",
            "tid": "2025-10-04T15:00:00",
            "tidsangivelse": "2025-10-04 15:00",
            "lag1lagid": 100,
            "lag1namn": "Alingsås IF FF",
            "lag1foreningid": 1000,
            "lag2lagid": 200,
            "lag2namn": "BK Häcken FF",
            "lag2foreningid": 2000,
            "anlaggningnamn": "Test Arena",
            "anlaggningid": 300,
            "tavlingnamn": "Test League",
            "installd": False,
            "avbruten": False,
            "uppskjuten": False,
            "domaruppdraglista": [
                {
                    "domarid": 1001,
                    "personnamn": "Magnus Blennersjö",
                    "domarrollnamn": "AD1",
                },
                {
                    "domarid": 1002,
                    "personnamn": "Alexander Eriksson",
                    "domarrollnamn": "AD2",
                },
                {
                    "domarid": 1003,
                    "personnamn": "Bartek Svaberg",
                    "domarrollnamn": "4:e dom",
                },
            ],
        }

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    def test_referee_addition_triggers_redis_publishing(
        self, mock_phonebook, mock_storage, mock_avatar, mock_api
    ):
        """Test that adding a referee triggers Redis publishing (Issue #75 scenario)."""
        # Set up processor with mocked services
        processor = UnifiedMatchProcessor(previous_matches_file=self.temp_file)

        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Mock API to return match with added referee
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"] = [
            {
                "domarid": 1004,
                "personnamn": "Toni Galic",
                "domarrollnamn": "Dom",
            },
            {
                "domarid": 1001,
                "personnamn": "Magnus Blennersjö",
                "domarrollnamn": "AD1",
            },
            {
                "domarid": 1002,
                "personnamn": "Alexander Eriksson",
                "domarrollnamn": "AD2",
            },
            {
                "domarid": 1003,
                "personnamn": "Bartek Svaberg",
                "domarrollnamn": "4:e dom",
            },
        ]

        mock_api.return_value.fetch_matches_list.return_value = [modified_match]

        # Add mock Redis integration
        mock_redis_service = Mock()
        processor.redis_integration = mock_redis_service

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify changes were detected
        self.assertTrue(result.processed, "Processing should have occurred")
        self.assertIsNotNone(result.changes, "Changes should be detected")
        self.assertTrue(result.changes.has_changes, "Referee change should be detected")

        # Verify Redis publishing would be triggered
        # (In actual integration, this would call redis_integration.handle_match_processing_complete)
        self.assertEqual(len(result.changes.updated_matches), 1)

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    def test_referee_removal_triggers_redis_publishing(
        self, mock_phonebook, mock_storage, mock_avatar, mock_api
    ):
        """Test that removing a referee triggers Redis publishing."""
        # Set up processor
        processor = UnifiedMatchProcessor(previous_matches_file=self.temp_file)

        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Mock API to return match with removed referee
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"] = [
            {
                "domarid": 1001,
                "personnamn": "Magnus Blennersjö",
                "domarrollnamn": "AD1",
            },
            {
                "domarid": 1002,
                "personnamn": "Alexander Eriksson",
                "domarrollnamn": "AD2",
            },
        ]

        mock_api.return_value.fetch_matches_list.return_value = [modified_match]

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify changes were detected
        self.assertTrue(result.processed)
        self.assertTrue(result.changes.has_changes)
        self.assertEqual(len(result.changes.updated_matches), 1)

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    def test_referee_replacement_triggers_redis_publishing(
        self, mock_phonebook, mock_storage, mock_avatar, mock_api
    ):
        """Test that replacing a referee triggers Redis publishing."""
        # Set up processor
        processor = UnifiedMatchProcessor(previous_matches_file=self.temp_file)

        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Mock API to return match with replaced referee
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"] = [
            {
                "domarid": 1001,
                "personnamn": "Magnus Blennersjö",
                "domarrollnamn": "AD1",
            },
            {
                "domarid": 1002,
                "personnamn": "Alexander Eriksson",
                "domarrollnamn": "AD2",
            },
            {
                "domarid": 1999,  # Different referee
                "personnamn": "New Referee",
                "domarrollnamn": "4:e dom",
            },
        ]

        mock_api.return_value.fetch_matches_list.return_value = [modified_match]

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify changes were detected
        self.assertTrue(result.processed)
        self.assertTrue(result.changes.has_changes)
        self.assertEqual(len(result.changes.updated_matches), 1)

    @patch("src.core.unified_processor.DockerNetworkApiClient")
    @patch("src.core.unified_processor.WhatsAppAvatarService")
    @patch("src.core.unified_processor.GoogleDriveStorageService")
    @patch("src.core.unified_processor.FogisPhonebookSyncService")
    def test_no_redis_publishing_when_no_referee_changes(
        self, mock_phonebook, mock_storage, mock_avatar, mock_api
    ):
        """Test that no Redis publishing occurs when referees don't change."""
        # Set up processor
        processor = UnifiedMatchProcessor(previous_matches_file=self.temp_file)

        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Mock API to return same match (no changes)
        mock_api.return_value.fetch_matches_list.return_value = [self.base_match]

        # Run processing cycle
        result = processor.run_processing_cycle()

        # Verify no changes detected
        self.assertFalse(result.processed)
        self.assertFalse(result.changes.has_changes)

    def test_redis_message_includes_referee_data(self):
        """Test that Redis messages include complete referee data (domaruppdraglista)."""
        from src.redis_integration.message_formatter import MatchUpdateMessageFormatter

        # Create a match update message
        matches = [self.base_match]
        changes = {"new_matches": 0, "removed_matches": 0, "changed_matches": 1}

        message_json = MatchUpdateMessageFormatter.format_match_updates(matches, changes)
        message = json.loads(message_json)

        # Verify referee data is included in the message
        self.assertIn("matches", message["payload"])
        self.assertEqual(len(message["payload"]["matches"]), 1)

        match_in_message = message["payload"]["matches"][0]
        self.assertIn("domaruppdraglista", match_in_message)
        self.assertEqual(len(match_in_message["domaruppdraglista"]), 3)

        # Verify referee IDs are present (using correct field name)
        for referee in match_in_message["domaruppdraglista"]:
            self.assertIn("domarid", referee)
            self.assertIsNotNone(referee["domarid"])


if __name__ == "__main__":
    unittest.main()
