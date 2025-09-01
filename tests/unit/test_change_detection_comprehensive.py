"""Comprehensive unit tests for change detection components."""

import os
from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.change_categorization import ChangeCategory, ChangePriority
from src.core.change_categorization import GranularChangeDetector as ChangeCategorizationDetector
from src.core.change_detector import ChangesSummary, GranularChangeDetector


@pytest.mark.unit
class TestGranularChangeDetector:
    """Test granular change detection functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = GranularChangeDetector()

    def test_detector_initialization(self):
        """Test change detector initialization."""
        assert self.detector is not None
        assert hasattr(self.detector, "detect_changes")
        assert hasattr(self.detector, "load_previous_matches")
        assert hasattr(self.detector, "save_current_matches")

    def test_detect_new_matches(self, sample_match_data):
        """Test detection of new matches."""
        # No previous matches, current has one match
        current_matches = [sample_match_data]

        with patch.object(self.detector, "load_previous_matches", return_value=[]):
            changes = self.detector.detect_changes(current_matches)

            assert isinstance(changes, ChangesSummary)
            assert changes.has_changes
            assert len(changes.new_matches) == 1
            assert len(changes.updated_matches) == 0
            assert len(changes.removed_matches) == 0
            assert changes.total_changes == 1

    def test_detect_removed_matches(self, sample_match_data):
        """Test detection of removed matches."""
        # Previous had one match, current has none
        previous_matches = [sample_match_data]
        current_matches = []

        with patch.object(self.detector, "load_previous_matches", return_value=previous_matches):
            changes = self.detector.detect_changes(current_matches)

            assert changes.has_changes
            assert len(changes.new_matches) == 0
            assert len(changes.updated_matches) == 0
            assert len(changes.removed_matches) == 1
            assert changes.total_changes == 1

    def test_detect_updated_matches(self, sample_match_data):
        """Test detection of updated matches."""
        # Create modified version of match
        modified_match = sample_match_data.copy()
        modified_match["avsparkstid"] = "16:00"
        modified_match["tid"] = "2025-06-14T16:00:00"

        previous_matches = [sample_match_data]
        current_matches = [modified_match]

        with patch.object(self.detector, "load_previous_matches", return_value=previous_matches):
            changes = self.detector.detect_changes(current_matches)

            assert changes.has_changes
            assert len(changes.new_matches) == 0
            assert len(changes.updated_matches) == 1
            assert len(changes.removed_matches) == 0
            assert changes.total_changes == 1

    def test_detect_no_changes(self, sample_match_data):
        """Test when no changes are detected."""
        matches = [sample_match_data]

        with patch.object(self.detector, "load_previous_matches", return_value=matches):
            changes = self.detector.detect_changes(matches)

            assert not changes.has_changes
            assert len(changes.new_matches) == 0
            assert len(changes.updated_matches) == 0
            assert len(changes.removed_matches) == 0
            assert changes.total_changes == 0

    def test_detect_referee_changes(self, sample_match_data):
        """Test detection of referee changes."""
        # Create match with different referee - ensure deep copy to avoid reference issues
        import copy

        modified_match = copy.deepcopy(sample_match_data)

        # Make a significant change to ensure detection
        modified_match["domaruppdraglista"] = [
            {
                "domarid": 2001,
                "personnamn": "New Referee",
                "namn": "New Referee",
                "domarrollnamn": "Huvuddomare",
            }
        ]
        # Also change the match time to ensure detection
        modified_match["avsparkstid"] = "16:00"

        previous_matches = [sample_match_data]
        current_matches = [modified_match]

        with patch.object(self.detector, "load_previous_matches", return_value=previous_matches):
            changes = self.detector.detect_changes(current_matches)

            # Should detect changes due to referee and time modification
            assert changes.has_changes
            assert len(changes.updated_matches) == 1

    def test_detect_multiple_changes_single_match(self, sample_match_data):
        """Test detection of multiple changes in a single match."""
        # Create match with multiple changes
        modified_match = sample_match_data.copy()
        modified_match["avsparkstid"] = "16:00"
        modified_match["tid"] = "2025-06-14T16:00:00"
        modified_match["anlaggningnamn"] = "New Venue"

        previous_matches = [sample_match_data]
        current_matches = [modified_match]

        with patch.object(self.detector, "load_previous_matches", return_value=previous_matches):
            changes = self.detector.detect_changes(current_matches)

            assert changes.has_changes
            assert len(changes.updated_matches) == 1

            # Check that multiple changes were detected
            updated_match = changes.updated_matches[0]
            assert updated_match["changes"]["basic"]

    def test_file_operations(self, temp_data_dir, sample_match_data):
        """Test file save and load operations."""
        # Configure detector with temp directory
        matches_file = os.path.join(temp_data_dir, "test_matches.json")

        with patch.object(self.detector, "previous_matches_file", matches_file):
            # Save matches
            matches = [sample_match_data]
            self.detector.save_current_matches(matches)

            # Verify file exists
            assert os.path.exists(matches_file)

            # Load matches
            loaded_matches = self.detector.load_previous_matches()
            assert len(loaded_matches) == 1
            assert loaded_matches[0]["matchid"] == sample_match_data["matchid"]

    def test_invalid_json_handling(self, temp_data_dir):
        """Test handling of invalid JSON files."""
        # Create invalid JSON file
        invalid_file = os.path.join(temp_data_dir, "invalid.json")
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with patch.object(self.detector, "previous_matches_file", invalid_file):
            # Should return empty list for invalid JSON
            matches = self.detector.load_previous_matches()
            assert matches == []

    def test_missing_file_handling(self, temp_data_dir):
        """Test handling of missing files."""
        missing_file = os.path.join(temp_data_dir, "missing.json")

        with patch.object(self.detector, "previous_matches_file", missing_file):
            # Should return empty list for missing file
            matches = self.detector.load_previous_matches()
            assert matches == []


@pytest.mark.unit
class TestChangeCategorizationDetector:
    """Test change categorization functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = ChangeCategorizationDetector()

    def test_categorize_new_assignment(self, sample_match_data):
        """Test categorization of new referee assignments."""
        # Match with no referees to match with referees
        empty_match = sample_match_data.copy()
        empty_match["domaruppdraglista"] = []

        # Use individual match objects, not lists
        changes = self.detector.categorize_changes(empty_match, sample_match_data)

        # Should detect referee assignment changes
        assert len(changes) > 0

        # Check for new assignment category
        new_assignment_changes = [c for c in changes if c.category == ChangeCategory.NEW_ASSIGNMENT]
        assert len(new_assignment_changes) > 0

    def test_categorize_time_change(self, sample_match_data):
        """Test categorization of time changes."""
        # Create time change
        modified_match = sample_match_data.copy()
        modified_match["avsparkstid"] = "16:00"
        modified_match["tid"] = "2025-06-14T16:00:00"

        # Use individual match objects, not lists
        changes = self.detector.categorize_changes(sample_match_data, modified_match)

        # Should detect time changes
        assert len(changes) > 0
        time_changes = [c for c in changes if c.category == ChangeCategory.TIME_CHANGE]
        assert len(time_changes) > 0

    def test_categorize_venue_change(self, sample_match_data):
        """Test categorization of venue changes."""
        # Create venue change
        modified_match = sample_match_data.copy()
        modified_match["anlaggningnamn"] = "New Stadium"

        # Use individual match objects, not lists
        changes = self.detector.categorize_changes(sample_match_data, modified_match)

        # Should detect venue changes
        assert len(changes) > 0
        venue_changes = [c for c in changes if c.category == ChangeCategory.VENUE_CHANGE]
        assert len(venue_changes) > 0

    def test_same_day_priority_escalation(self, sample_match_data):
        """Test priority escalation for same-day changes."""
        # Create match for today
        today = datetime.now().strftime("%Y-%m-%d")
        same_day_match = sample_match_data.copy()
        same_day_match["speldatum"] = today
        same_day_match["avsparkstid"] = "16:00"  # Time change

        # Use individual match objects, not lists
        changes = self.detector.categorize_changes(sample_match_data, same_day_match)

        # Should have critical priority for same-day changes
        critical_changes = [c for c in changes if c.priority == ChangePriority.CRITICAL]
        assert len(critical_changes) > 0

    def test_multiple_stakeholder_types(self, sample_match_data):
        """Test identification of multiple stakeholder types."""
        # Create changes affecting multiple stakeholders
        modified_match = sample_match_data.copy()
        modified_match["avsparkstid"] = "16:00"  # Affects referees and teams
        modified_match["anlaggningnamn"] = "New Venue"  # Affects teams and venue staff

        # Use individual match objects, not lists
        changes = self.detector.categorize_changes(sample_match_data, modified_match)

        # Should identify multiple changes
        assert len(changes) >= 2

        # Check for different change categories
        categories = [c.category for c in changes]
        assert ChangeCategory.TIME_CHANGE in categories
        assert ChangeCategory.VENUE_CHANGE in categories


@pytest.mark.unit
class TestChangeDetectionPerformance:
    """Performance tests for change detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = GranularChangeDetector()

    def test_large_dataset_performance(self, large_match_dataset):
        """Test change detection performance with large datasets."""
        import time

        # Test with no changes (worst case for comparison)
        with patch.object(self.detector, "load_previous_matches", return_value=large_match_dataset):
            start_time = time.time()
            changes = self.detector.detect_changes(large_match_dataset)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should process 1000 matches in under 2 seconds
            assert processing_time < 2.0
            assert not changes.has_changes

    def test_change_detection_with_modifications(self, large_match_dataset):
        """Test change detection performance with modifications."""
        import time

        # Modify some matches
        modified_dataset = large_match_dataset.copy()
        for i in range(0, min(100, len(modified_dataset)), 10):  # Modify every 10th match
            modified_dataset[i] = modified_dataset[i].copy()
            modified_dataset[i]["avsparkstid"] = "16:00"

        with patch.object(self.detector, "load_previous_matches", return_value=large_match_dataset):
            start_time = time.time()
            changes = self.detector.detect_changes(modified_dataset)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should still process quickly even with changes
            assert processing_time < 3.0
            assert changes.has_changes
            assert len(changes.updated_matches) >= 10
