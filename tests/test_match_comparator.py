"""Tests for match comparison functionality."""

import pytest

from src.core.match_comparator import MatchComparator


class TestMatchComparator:
    """Test the MatchComparator class."""

    def test_convert_to_dict(self, sample_matches_list):
        """Test converting match list to dictionary."""
        result = MatchComparator.convert_to_dict(sample_matches_list)

        assert isinstance(result, dict)
        assert len(result) == 2
        assert 6169105 in result
        assert 6169106 in result
        assert result[6169105]["lag1namn"] == "IK Kongahälla"
        assert result[6169106]["lag1namn"] == "Team A"

    def test_convert_to_dict_empty_list(self):
        """Test converting empty list."""
        result = MatchComparator.convert_to_dict([])
        assert result == {}

    def test_detect_changes_new_matches(self, sample_match_data):
        """Test detecting new matches."""
        previous = {}
        current = {6169105: sample_match_data}

        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(previous, current)

        assert new_ids == {6169105}
        assert removed_ids == set()
        assert common_ids == set()

    def test_detect_changes_removed_matches(self, sample_match_data):
        """Test detecting removed matches."""
        previous = {6169105: sample_match_data}
        current = {}

        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(previous, current)

        assert new_ids == set()
        assert removed_ids == {6169105}
        assert common_ids == set()

    def test_detect_changes_common_matches(self, sample_match_data):
        """Test detecting common matches."""
        previous = {6169105: sample_match_data}
        current = {6169105: sample_match_data}

        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(previous, current)

        assert new_ids == set()
        assert removed_ids == set()
        assert common_ids == {6169105}

    def test_detect_changes_mixed_scenario(self, sample_matches_list):
        """Test detecting changes in mixed scenario."""
        match1, match2 = sample_matches_list
        match3 = match1.copy()
        match3["matchid"] = 6169107

        previous = {6169105: match1, 6169106: match2}
        current = {6169105: match1, 6169107: match3}

        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(previous, current)

        assert new_ids == {6169107}
        assert removed_ids == {6169106}
        assert common_ids == {6169105}

    def test_is_match_modified_no_changes(self, sample_match_data):
        """Test match modification detection with no changes."""
        result = MatchComparator.is_match_modified(sample_match_data, sample_match_data)
        assert result is False

    def test_is_match_modified_time_change(self, sample_match_data):
        """Test match modification detection with time change."""
        modified_match = sample_match_data.copy()
        modified_match["tid"] = "2025-06-14T16:00:00"

        result = MatchComparator.is_match_modified(sample_match_data, modified_match)
        assert result is True

    def test_is_match_modified_team_change(self, sample_match_data):
        """Test match modification detection with team change."""
        modified_match = sample_match_data.copy()
        modified_match["lag1lagid"] = 99999

        result = MatchComparator.is_match_modified(sample_match_data, modified_match)
        assert result is True

    def test_is_match_modified_venue_change(self, sample_match_data):
        """Test match modification detection with venue change."""
        modified_match = sample_match_data.copy()
        modified_match["anlaggningid"] = 99999

        result = MatchComparator.is_match_modified(sample_match_data, modified_match)
        assert result is True

    def test_is_match_modified_referee_count_change(self, sample_match_data):
        """Test match modification detection with referee count change."""
        modified_match = sample_match_data.copy()
        modified_match["domaruppdraglista"] = [sample_match_data["domaruppdraglista"][0]]

        result = MatchComparator.is_match_modified(sample_match_data, modified_match)
        assert result is True

    def test_is_match_modified_referee_change(self, sample_match_data):
        """Test match modification detection with different referees."""
        modified_match = sample_match_data.copy()
        modified_match["domaruppdraglista"] = [
            {"domarid": 9999, "personnamn": "New Referee", "domarrollnamn": "Huvuddomare"},
            sample_match_data["domaruppdraglista"][1],
        ]

        result = MatchComparator.is_match_modified(sample_match_data, modified_match)
        assert result is True

    def test_get_modification_details_time_change(self, sample_match_data):
        """Test getting modification details for time change."""
        modified_match = sample_match_data.copy()
        modified_match["tid"] = "2025-06-14T16:00:00"
        modified_match["tidsangivelse"] = "2025-06-14 16:00"

        details = MatchComparator.get_modification_details(sample_match_data, modified_match)

        assert len(details) == 1
        assert "Date/Time changed" in details[0]
        assert "2025-06-14 15:00" in details[0]
        assert "2025-06-14 16:00" in details[0]

    def test_get_modification_details_multiple_changes(self, sample_match_data):
        """Test getting modification details for multiple changes."""
        modified_match = sample_match_data.copy()
        modified_match["lag1lagid"] = 99999
        modified_match["anlaggningid"] = 88888

        details = MatchComparator.get_modification_details(sample_match_data, modified_match)

        assert len(details) == 2
        assert any("Home Team changed" in detail for detail in details)
        assert any("Venue changed" in detail for detail in details)

    def test_get_modification_details_no_changes(self, sample_match_data):
        """Test getting modification details with no changes."""
        details = MatchComparator.get_modification_details(sample_match_data, sample_match_data)
        assert details == []
