"""
Comprehensive tests for referee change detection in GranularChangeDetector.

This test suite specifically addresses Issue #75 - ensuring referee changes
are properly detected and trigger Redis publishing for calendar updates.
"""

import json
import os
import tempfile
import unittest

from src.core.change_detector import GranularChangeDetector


class TestRefereeChangeDetection(unittest.TestCase):
    """Test cases specifically for referee change detection (Issue #75)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_matches.json")
        self.detector = GranularChangeDetector(self.temp_file)

        # Base match with one referee
        self.base_match = {
            "matchid": "6143017",
            "matchnr": "M001",
            "speldatum": "2025-10-04",
            "avsparkstid": "15:00",
            "lag1lagid": 100,
            "lag1namn": "Alingsås IF FF",
            "lag2lagid": 200,
            "lag2namn": "BK Häcken FF",
            "anlaggningnamn": "Test Arena",
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

    def test_referee_addition_detected(self):
        """Test that adding a referee is detected as a change (Issue #75 scenario)."""
        # Save initial state with 3 referees
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Add main referee (Dom)
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

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected
        self.assertTrue(changes.has_changes, "Referee addition should be detected as a change")
        self.assertEqual(len(changes.updated_matches), 1, "Should have 1 updated match")

        # Verify it's a referee change
        change_record = changes.updated_matches[0]
        self.assertTrue(
            change_record["changes"]["referees"], "Change should be flagged as referee change"
        )

    def test_referee_removal_detected(self):
        """Test that removing a referee is detected as a change."""
        # Save initial state with 3 referees
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Remove one referee
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

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected
        self.assertTrue(changes.has_changes, "Referee removal should be detected as a change")
        self.assertEqual(len(changes.updated_matches), 1)

        change_record = changes.updated_matches[0]
        self.assertTrue(change_record["changes"]["referees"])

    def test_referee_replacement_detected(self):
        """Test that replacing a referee (same count, different person) is detected."""
        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Replace one referee with another
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
                "domarid": 1999,  # Different referee ID
                "personnamn": "New Referee",
                "domarrollnamn": "4:e dom",
            },
        ]

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected
        self.assertTrue(changes.has_changes, "Referee replacement should be detected")
        self.assertEqual(len(changes.updated_matches), 1)

        change_record = changes.updated_matches[0]
        self.assertTrue(change_record["changes"]["referees"])

    def test_no_referee_change_when_same(self):
        """Test that no change is detected when referees remain the same."""
        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Same referees (even if order is different)
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"] = [
            {
                "domarid": 1003,
                "personnamn": "Bartek Svaberg",
                "domarrollnamn": "4:e dom",
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
        ]

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify no change detected
        self.assertFalse(changes.has_changes, "No change should be detected for same referees")

    def test_referee_change_with_empty_initial_list(self):
        """Test detecting referee addition when initial list was empty."""
        # Save initial state with no referees
        match_no_refs = self.base_match.copy()
        match_no_refs["domaruppdraglista"] = []

        with open(self.temp_file, "w") as f:
            json.dump([match_no_refs], f)

        # Add referees
        modified_match = self.base_match.copy()  # Has 3 referees

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected
        self.assertTrue(changes.has_changes, "Adding referees to empty list should be detected")
        self.assertEqual(len(changes.updated_matches), 1)

        change_record = changes.updated_matches[0]
        self.assertTrue(change_record["changes"]["referees"])

    def test_referee_change_to_empty_list(self):
        """Test detecting referee removal when all referees are removed."""
        # Save initial state with referees
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Remove all referees
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"] = []

        # Detect changes
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected
        self.assertTrue(changes.has_changes, "Removing all referees should be detected")
        self.assertEqual(len(changes.updated_matches), 1)

        change_record = changes.updated_matches[0]
        self.assertTrue(change_record["changes"]["referees"])

    def test_referee_change_includes_correct_field_name(self):
        """Test that the correct field name 'domarid' is used (not 'domareid')."""
        # This test verifies the fix for Issue #75

        # Save initial state
        with open(self.temp_file, "w") as f:
            json.dump([self.base_match], f)

        # Add a referee
        modified_match = self.base_match.copy()
        modified_match["domaruppdraglista"].append(
            {
                "domarid": 1004,  # Using correct field name
                "personnamn": "New Referee",
                "domarrollnamn": "Dom",
            }
        )

        # Detect changes - should work with correct field name
        changes = self.detector.detect_changes([modified_match])

        # Verify change was detected (proves we're using correct field name)
        self.assertTrue(changes.has_changes)
        self.assertEqual(len(changes.updated_matches), 1)


if __name__ == "__main__":
    unittest.main()
