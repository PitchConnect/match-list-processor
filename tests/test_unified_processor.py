"""Tests for the unified processor."""

import tempfile
import unittest
from unittest.mock import patch

from src.core.change_detector import ChangesSummary
from src.core.unified_processor import ProcessingResult, UnifiedMatchProcessor


class TestUnifiedMatchProcessor(unittest.TestCase):
    """Test cases for the UnifiedMatchProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary file for testing
        self.temp_file = tempfile.mktemp(suffix=".json")

        # Mock all the services to avoid external dependencies
        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):

            self.processor = UnifiedMatchProcessor(self.temp_file)

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
                "domaruppdraglista": [],
            }
        ]

    def test_initialization(self):
        """Test processor initialization."""
        self.assertIsNotNone(self.processor.change_detector)
        self.assertIsNotNone(self.processor.api_client)
        self.assertIsNotNone(self.processor.match_processor)

    @patch("src.core.unified_processor.UnifiedMatchProcessor._fetch_current_matches")
    @patch("src.core.unified_processor.UnifiedMatchProcessor._process_changes")
    @patch("src.core.unified_processor.UnifiedMatchProcessor._trigger_downstream_services")
    def test_run_processing_cycle_with_changes(self, mock_trigger, mock_process, mock_fetch):
        """Test processing cycle when changes are detected."""
        # Setup mocks
        mock_fetch.return_value = self.sample_matches
        mock_process.return_value = True

        # Mock change detector to return changes
        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        with (
            patch.object(
                self.processor.change_detector, "detect_changes", return_value=mock_changes
            ),
            patch.object(self.processor.change_detector, "save_current_matches"),
        ):

            result = self.processor.run_processing_cycle()

        # Verify result
        self.assertIsInstance(result, ProcessingResult)
        self.assertTrue(result.processed)
        self.assertIsNotNone(result.changes)
        self.assertTrue(result.changes.has_changes)
        self.assertEqual(len(result.errors), 0)

        # Verify methods were called
        mock_fetch.assert_called_once()
        mock_process.assert_called_once()
        mock_trigger.assert_called_once()

    @patch("src.core.unified_processor.UnifiedMatchProcessor._fetch_current_matches")
    def test_run_processing_cycle_no_changes(self, mock_fetch):
        """Test processing cycle when no changes are detected."""
        # Setup mocks
        mock_fetch.return_value = self.sample_matches

        # Mock change detector to return no changes
        mock_changes = ChangesSummary(new_matches=[], updated_matches=[], removed_matches=[])

        with patch.object(
            self.processor.change_detector, "detect_changes", return_value=mock_changes
        ):
            result = self.processor.run_processing_cycle()

        # Verify result
        self.assertIsInstance(result, ProcessingResult)
        self.assertFalse(result.processed)
        self.assertIsNotNone(result.changes)
        self.assertFalse(result.changes.has_changes)
        self.assertEqual(len(result.errors), 0)

    @patch("src.core.unified_processor.UnifiedMatchProcessor._fetch_current_matches")
    def test_run_processing_cycle_no_matches_fetched(self, mock_fetch):
        """Test processing cycle when no matches are fetched from API."""
        mock_fetch.return_value = []

        result = self.processor.run_processing_cycle()

        self.assertFalse(result.processed)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("No matches fetched from API", result.errors[0])

    @patch("src.core.unified_processor.UnifiedMatchProcessor._fetch_current_matches")
    def test_run_processing_cycle_api_error(self, mock_fetch):
        """Test processing cycle when API fetch fails."""
        mock_fetch.side_effect = Exception("API Error")

        result = self.processor.run_processing_cycle()

        self.assertFalse(result.processed)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Processing cycle failed", result.errors[0])

    def test_fetch_current_matches_success(self):
        """Test successful fetching of current matches."""
        self.processor.api_client.get_matches.return_value = self.sample_matches

        matches = self.processor._fetch_current_matches()

        self.assertEqual(matches, self.sample_matches)
        self.processor.api_client.get_matches.assert_called_once()

    def test_fetch_current_matches_failure(self):
        """Test failed fetching of current matches."""
        self.processor.api_client.get_matches.side_effect = Exception("API Error")

        with self.assertRaises(Exception):
            self.processor._fetch_current_matches()

    @patch("src.core.unified_processor.UnifiedMatchProcessor._run_existing_processing_logic")
    def test_process_changes_success(self, mock_run_logic):
        """Test successful processing of changes."""
        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        result = self.processor._process_changes(mock_changes, self.sample_matches)

        self.assertTrue(result)
        mock_run_logic.assert_called_once_with(self.sample_matches)

    @patch("src.core.unified_processor.UnifiedMatchProcessor._run_existing_processing_logic")
    def test_process_changes_failure(self, mock_run_logic):
        """Test failed processing of changes."""
        mock_run_logic.side_effect = Exception("Processing Error")

        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        result = self.processor._process_changes(mock_changes, self.sample_matches)

        self.assertFalse(result)

    def test_run_existing_processing_logic(self):
        """Test running existing processing logic."""
        # Mock the data manager and comparator
        self.processor.data_manager.load_previous_matches.return_value = []

        # Mock match processor
        self.processor.match_processor.process_match.return_value = {
            "success": True,
            "error_message": None,
        }

        # Run processing logic
        self.processor._run_existing_processing_logic(self.sample_matches)

        # Verify calls
        self.processor.data_manager.load_previous_matches.assert_called_once()
        self.processor.data_manager.save_current_matches.assert_called_once_with(
            self.sample_matches
        )

    @patch("src.core.unified_processor.UnifiedMatchProcessor._trigger_calendar_sync")
    def test_trigger_downstream_services(self, mock_calendar_sync):
        """Test triggering downstream services."""
        mock_calendar_sync.return_value = True

        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        self.processor._trigger_downstream_services(mock_changes)

        mock_calendar_sync.assert_called_once_with(mock_changes)

    def test_trigger_calendar_sync_success(self):
        """Test successful calendar sync trigger."""
        self.processor.phonebook_service.sync_contacts.return_value = True

        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        result = self.processor._trigger_calendar_sync(mock_changes)

        self.assertTrue(result)
        self.processor.phonebook_service.sync_contacts.assert_called_once()

    def test_trigger_calendar_sync_failure(self):
        """Test failed calendar sync trigger."""
        self.processor.phonebook_service.sync_contacts.side_effect = Exception("Sync Error")

        mock_changes = ChangesSummary(
            new_matches=self.sample_matches, updated_matches=[], removed_matches=[]
        )

        result = self.processor._trigger_calendar_sync(mock_changes)

        self.assertFalse(result)

    def test_get_processing_stats(self):
        """Test getting processing statistics."""
        stats = self.processor.get_processing_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats["service_type"], "unified_processor")
        self.assertEqual(stats["change_detection"], "integrated")


class TestProcessingResult(unittest.TestCase):
    """Test cases for ProcessingResult class."""

    def test_processing_result_initialization(self):
        """Test ProcessingResult initialization."""
        result = ProcessingResult(processed=True, processing_time=1.5, errors=["error1", "error2"])

        self.assertTrue(result.processed)
        self.assertEqual(result.processing_time, 1.5)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(result.assets_generated, 0)
        self.assertFalse(result.calendar_synced)

    def test_processing_result_defaults(self):
        """Test ProcessingResult with default values."""
        result = ProcessingResult(processed=False)

        self.assertFalse(result.processed)
        self.assertIsNone(result.changes)
        self.assertEqual(result.processing_time, 0.0)
        self.assertEqual(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()
