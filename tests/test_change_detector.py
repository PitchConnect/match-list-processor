"""Tests for the enhanced change detector."""

import json
import os
import tempfile
import unittest

from src.core.change_detector import ChangesSummary, GranularChangeDetector


class TestGranularChangeDetector(unittest.TestCase):
    """Test cases for the GranularChangeDetector class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_matches.json")
        self.detector = GranularChangeDetector(self.temp_file)

        # Sample match data for testing
        self.sample_match = {
            "matchid": "12345",
            "matchnr": "1",
            "speldatum": "2025-09-01",
            "avsparkstid": "14:00",
            "lag1lagid": "100",
            "lag1namn": "Team A",
            "lag2lagid": "200",
            "lag2namn": "Team B",
            "anlaggningnamn": "Stadium A",
            "installd": False,
            "avbruten": False,
            "uppskjuten": False,
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

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        os.rmdir(self.temp_dir)

    def test_detect_changes_no_previous_matches(self):
        """Test change detection when no previous matches exist."""
        current_matches = [self.sample_match]

        changes = self.detector.detect_changes(current_matches)

        self.assertIsInstance(changes, ChangesSummary)
        self.assertTrue(changes.has_changes)
        self.assertEqual(changes.total_changes, 1)
        self.assertEqual(len(changes.new_matches), 1)
        self.assertEqual(len(changes.updated_matches), 0)
        self.assertEqual(len(changes.removed_matches), 0)

    def test_detect_changes_no_changes(self):
        """Test change detection when no changes occurred."""
        # Save initial matches
        with open(self.temp_file, "w") as f:
            json.dump([self.sample_match], f)

        # Detect changes with same matches
        current_matches = [self.sample_match]
        changes = self.detector.detect_changes(current_matches)

        self.assertFalse(changes.has_changes)
        self.assertEqual(changes.total_changes, 0)

    def test_detect_basic_field_changes(self):
        """Test detection of basic field changes."""
        # Save initial matches
        with open(self.temp_file, "w") as f:
            json.dump([self.sample_match], f)

        # Create modified match with time change
        modified_match = self.sample_match.copy()
        modified_match["avsparkstid"] = "16:00"

        current_matches = [modified_match]
        changes = self.detector.detect_changes(current_matches)

        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.updated_matches), 1)

        # Check change details
        change_record = changes.updated_matches[0]
        self.assertEqual(change_record["match_id"], "12345")
        self.assertTrue(change_record["changes"]["basic"])
        self.assertFalse(change_record["changes"]["referees"])

    def test_detect_referee_changes(self):
        """Test detection of referee assignment changes."""
        # Save initial matches
        with open(self.temp_file, "w") as f:
            json.dump([self.sample_match], f)

        # Create modified match with additional referee
        modified_match = self.sample_match.copy()
        modified_match["domaruppdraglista"] = [
            {
                "domareid": "ref1",
                "personnamn": "John Referee",
                "domarrollnamn": "Huvuddomare",
                "epostadress": "john@example.com",
                "mobiltelefon": "123456789",
            },
            {
                "domareid": "ref2",
                "personnamn": "Jane Assistant",
                "domarrollnamn": "Assisterande dommare",
                "epostadress": "jane@example.com",
                "mobiltelefon": "987654321",
            },
        ]

        current_matches = [modified_match]
        changes = self.detector.detect_changes(current_matches)

        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.updated_matches), 1)

        # Check change details
        change_record = changes.updated_matches[0]
        self.assertFalse(change_record["changes"]["basic"])
        self.assertTrue(change_record["changes"]["referees"])

    def test_detect_new_matches(self):
        """Test detection of new matches."""
        # Save initial matches
        with open(self.temp_file, "w") as f:
            json.dump([self.sample_match], f)

        # Add new match
        new_match = self.sample_match.copy()
        new_match["matchid"] = "67890"
        new_match["matchnr"] = "2"

        current_matches = [self.sample_match, new_match]
        changes = self.detector.detect_changes(current_matches)

        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.new_matches), 1)
        self.assertEqual(len(changes.updated_matches), 0)
        self.assertEqual(changes.new_matches[0]["matchid"], "67890")

    def test_detect_removed_matches(self):
        """Test detection of removed matches."""
        # Save initial matches with two matches
        new_match = self.sample_match.copy()
        new_match["matchid"] = "67890"
        new_match["matchnr"] = "2"

        with open(self.temp_file, "w") as f:
            json.dump([self.sample_match, new_match], f)

        # Current matches with only one match (one removed)
        current_matches = [self.sample_match]
        changes = self.detector.detect_changes(current_matches)

        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.removed_matches), 1)
        self.assertEqual(len(changes.updated_matches), 0)
        self.assertEqual(changes.removed_matches[0]["matchid"], "67890")

    def test_save_and_load_matches(self):
        """Test saving and loading matches."""
        matches = [self.sample_match]

        # Save matches
        self.detector.save_current_matches(matches)

        # Load matches
        loaded_matches = self.detector.load_previous_matches()

        self.assertEqual(len(loaded_matches), 1)
        self.assertEqual(loaded_matches[0]["matchid"], "12345")

    def test_load_matches_file_not_exists(self):
        """Test loading matches when file doesn't exist."""
        # Use non-existent file
        detector = GranularChangeDetector("non_existent_file.json")
        matches = detector.load_previous_matches()

        self.assertEqual(matches, [])

    def test_load_matches_invalid_json(self):
        """Test loading matches with invalid JSON."""
        # Write invalid JSON
        with open(self.temp_file, "w") as f:
            f.write("invalid json content")

        matches = self.detector.load_previous_matches()

        self.assertEqual(matches, [])

    def test_extract_match_details(self):
        """Test extraction of match details for change tracking."""
        details = self.detector._extract_match_details(self.sample_match)

        self.assertEqual(details["date"], "2025-09-01")
        self.assertEqual(details["time"], "14:00")
        self.assertEqual(details["home_team"]["name"], "Team A")
        self.assertEqual(details["away_team"]["name"], "Team B")
        self.assertEqual(details["venue"], "Stadium A")
        self.assertEqual(len(details["referees"]), 1)
        self.assertEqual(details["referees"][0]["name"], "John Referee")

    def test_convert_to_dict(self):
        """Test conversion of match list to dictionary."""
        matches = [self.sample_match]
        match_dict = self.detector._convert_to_dict(matches)

        self.assertIn("12345", match_dict)
        self.assertEqual(match_dict["12345"]["matchid"], "12345")

    def test_convert_to_dict_missing_matchid(self):
        """Test conversion with missing match ID."""
        invalid_match = {"matchnr": "1", "lag1namn": "Team A"}
        matches = [invalid_match]

        match_dict = self.detector._convert_to_dict(matches)

        # Should skip matches without matchid
        self.assertEqual(len(match_dict), 0)

    def test_enhanced_granular_categorization_new_matches(self):
        """Test enhanced granular categorization for new matches."""
        from src.core.change_categorization import ChangeCategory, StakeholderType

        # Test with new match containing referee assignments
        current_matches = [
            {
                "matchid": "123",
                "matchnr": 1,
                "domaruppdraglista": [
                    {
                        "personid": 456,
                        "personnamn": "Test Referee",
                        "uppdragstyp": "Huvuddomare",
                    }
                ],
                "speldatum": "2025-09-01",
                "avsparkstid": "14:00",
                "anlaggningnamn": "Test Arena",
                "lag1namn": "Team A",
                "lag2namn": "Team B",
                "serienamn": "Test League",
            }
        ]

        # Detect changes (no previous matches)
        changes = self.detector.detect_changes(current_matches)

        # Verify basic change detection
        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.new_matches), 1)
        self.assertEqual(len(changes.updated_matches), 0)

        # Verify granular categorization
        self.assertIsNotNone(changes.categorized_changes)
        self.assertGreater(changes.categorized_changes.total_changes, 0)

        # Check for NEW_ASSIGNMENT category
        new_assignment_changes = changes.categorized_changes.get_changes_by_category(
            ChangeCategory.NEW_ASSIGNMENT
        )
        self.assertGreater(len(new_assignment_changes), 0)

        # Verify stakeholder types are identified
        self.assertIn(
            StakeholderType.REFEREES,
            changes.categorized_changes.affected_stakeholder_types,
        )
        self.assertIn(
            StakeholderType.COORDINATORS,
            changes.categorized_changes.affected_stakeholder_types,
        )

        # Verify change categories are identified
        self.assertIn(ChangeCategory.NEW_ASSIGNMENT, changes.categorized_changes.change_categories)


if __name__ == "__main__":
    unittest.main()
