"""Tests for enhanced change categorization system."""

from datetime import datetime, timezone
from unittest.mock import patch

from src.core.change_categorization import (
    CategorizedChanges,
    ChangeCategory,
    ChangePriority,
    GranularChangeDetector,
    MatchChangeDetail,
    StakeholderType,
)


class TestChangeCategorizationEnums:
    """Test change categorization enums."""

    def test_change_category_values(self):
        """Test ChangeCategory enum values."""
        assert ChangeCategory.NEW_ASSIGNMENT.value == "new_assignment"
        assert ChangeCategory.REFEREE_CHANGE.value == "referee_change"
        assert ChangeCategory.TIME_CHANGE.value == "time_change"
        assert ChangeCategory.VENUE_CHANGE.value == "venue_change"
        assert ChangeCategory.CANCELLATION.value == "cancellation"

    def test_change_priority_values(self):
        """Test ChangePriority enum values."""
        assert ChangePriority.CRITICAL.value == "critical"
        assert ChangePriority.HIGH.value == "high"
        assert ChangePriority.MEDIUM.value == "medium"
        assert ChangePriority.LOW.value == "low"

    def test_stakeholder_type_values(self):
        """Test StakeholderType enum values."""
        assert StakeholderType.REFEREES.value == "referees"
        assert StakeholderType.COORDINATORS.value == "coordinators"
        assert StakeholderType.TEAMS.value == "teams"
        assert StakeholderType.ALL.value == "all"


class TestMatchChangeDetail:
    """Test MatchChangeDetail dataclass."""

    def test_match_change_detail_creation(self):
        """Test creating a MatchChangeDetail instance."""
        change = MatchChangeDetail(
            match_id="123456",
            match_nr="001",
            category=ChangeCategory.REFEREE_CHANGE,
            priority=ChangePriority.HIGH,
            affected_stakeholders=[StakeholderType.REFEREES],
            field_name="domaruppdraglista",
            previous_value=None,
            current_value=[{"name": "John Doe"}],
            change_description="New referee assigned",
            timestamp=datetime.now(timezone.utc),
        )

        assert change.match_id == "123456"
        assert change.category == ChangeCategory.REFEREE_CHANGE
        assert change.priority == ChangePriority.HIGH
        assert StakeholderType.REFEREES in change.affected_stakeholders

    def test_match_change_detail_to_dict(self):
        """Test converting MatchChangeDetail to dictionary."""
        timestamp = datetime.now(timezone.utc)
        change = MatchChangeDetail(
            match_id="123456",
            match_nr="001",
            category=ChangeCategory.TIME_CHANGE,
            priority=ChangePriority.HIGH,
            affected_stakeholders=[StakeholderType.ALL],
            field_name="avsparkstid",
            previous_value="14:00",
            current_value="15:00",
            change_description="Time changed",
            timestamp=timestamp,
        )

        result = change.to_dict()

        assert result["match_id"] == "123456"
        assert result["category"] == "time_change"
        assert result["priority"] == "high"
        assert result["affected_stakeholders"] == ["all"]
        assert result["timestamp"] == timestamp.isoformat()


class TestCategorizedChanges:
    """Test CategorizedChanges dataclass."""

    def test_categorized_changes_creation(self):
        """Test creating a CategorizedChanges instance."""
        changes = [
            MatchChangeDetail(
                match_id="123",
                match_nr="001",
                category=ChangeCategory.REFEREE_CHANGE,
                priority=ChangePriority.HIGH,
                affected_stakeholders=[StakeholderType.REFEREES],
                field_name="domaruppdraglista",
                previous_value=None,
                current_value=[],
                change_description="Test change",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        categorized = CategorizedChanges(
            changes=changes,
            total_changes=1,
            critical_changes=0,
            high_priority_changes=1,
            affected_stakeholder_types={StakeholderType.REFEREES},
            change_categories={ChangeCategory.REFEREE_CHANGE},
        )

        assert categorized.total_changes == 1
        assert categorized.has_changes
        assert not categorized.has_critical_changes
        assert ChangeCategory.REFEREE_CHANGE in categorized.change_categories

    def test_get_changes_by_category(self):
        """Test filtering changes by category."""
        referee_change = MatchChangeDetail(
            match_id="123",
            match_nr="001",
            category=ChangeCategory.REFEREE_CHANGE,
            priority=ChangePriority.HIGH,
            affected_stakeholders=[StakeholderType.REFEREES],
            field_name="domaruppdraglista",
            previous_value=None,
            current_value=[],
            change_description="Referee change",
            timestamp=datetime.now(timezone.utc),
        )

        time_change = MatchChangeDetail(
            match_id="123",
            match_nr="001",
            category=ChangeCategory.TIME_CHANGE,
            priority=ChangePriority.HIGH,
            affected_stakeholders=[StakeholderType.ALL],
            field_name="avsparkstid",
            previous_value="14:00",
            current_value="15:00",
            change_description="Time change",
            timestamp=datetime.now(timezone.utc),
        )

        categorized = CategorizedChanges(
            changes=[referee_change, time_change],
            total_changes=2,
            critical_changes=0,
            high_priority_changes=2,
            affected_stakeholder_types={StakeholderType.REFEREES, StakeholderType.ALL},
            change_categories={ChangeCategory.REFEREE_CHANGE, ChangeCategory.TIME_CHANGE},
        )

        referee_changes = categorized.get_changes_by_category(ChangeCategory.REFEREE_CHANGE)
        assert len(referee_changes) == 1
        assert referee_changes[0].category == ChangeCategory.REFEREE_CHANGE

        time_changes = categorized.get_changes_by_category(ChangeCategory.TIME_CHANGE)
        assert len(time_changes) == 1
        assert time_changes[0].category == ChangeCategory.TIME_CHANGE


class TestGranularChangeDetector:
    """Test GranularChangeDetector class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = GranularChangeDetector()

    def test_categorize_referee_changes_new_assignment(self):
        """Test categorizing new referee assignments."""
        prev_match = {"matchid": "123456", "matchnr": "001", "domaruppdraglista": []}

        curr_match = {
            "matchid": "123456",
            "matchnr": "001",
            "domaruppdraglista": [
                {"domareid": "ref1", "personnamn": "John Doe", "domarrollnamn": "Domare"}
            ],
        }

        changes = self.detector.categorize_changes(prev_match, curr_match)

        assert len(changes) == 1
        assert changes[0].category == ChangeCategory.NEW_ASSIGNMENT
        assert changes[0].priority == ChangePriority.HIGH
        assert StakeholderType.REFEREES in changes[0].affected_stakeholders
        assert "New referee assignment" in changes[0].change_description

    def test_categorize_time_change(self):
        """Test categorizing time changes."""
        prev_match = {"matchid": "123456", "matchnr": "001", "avsparkstid": "14:00"}

        curr_match = {"matchid": "123456", "matchnr": "001", "avsparkstid": "15:00"}

        changes = self.detector.categorize_changes(prev_match, curr_match)

        assert len(changes) == 1
        assert changes[0].category == ChangeCategory.TIME_CHANGE
        assert changes[0].priority == ChangePriority.HIGH
        assert StakeholderType.ALL in changes[0].affected_stakeholders
        assert "time changed from 14:00 to 15:00" in changes[0].change_description

    def test_categorize_venue_change(self):
        """Test categorizing venue changes."""
        prev_match = {"matchid": "123456", "matchnr": "001", "anlaggningnamn": "Old Stadium"}

        curr_match = {"matchid": "123456", "matchnr": "001", "anlaggningnamn": "New Stadium"}

        changes = self.detector.categorize_changes(prev_match, curr_match)

        assert len(changes) == 1
        assert changes[0].category == ChangeCategory.VENUE_CHANGE
        assert changes[0].priority == ChangePriority.MEDIUM
        assert StakeholderType.ALL in changes[0].affected_stakeholders

    def test_categorize_cancellation(self):
        """Test categorizing match cancellations."""
        prev_match = {"matchid": "123456", "matchnr": "001", "installd": False}

        curr_match = {"matchid": "123456", "matchnr": "001", "installd": True}

        changes = self.detector.categorize_changes(prev_match, curr_match)

        assert len(changes) == 1
        assert changes[0].category == ChangeCategory.CANCELLATION
        assert changes[0].priority == ChangePriority.CRITICAL
        assert StakeholderType.ALL in changes[0].affected_stakeholders
        assert "Match cancelled" in changes[0].change_description

    @patch("src.core.change_categorization.datetime")
    def test_same_day_change_priority(self, mock_datetime):
        """Test that same-day changes get critical priority."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = datetime(2025, 8, 31).date()
        mock_datetime.strptime.return_value = datetime(2025, 8, 31)

        prev_match = {
            "matchid": "123456",
            "matchnr": "001",
            "avsparkstid": "14:00",
            "speldatum": "2025-08-31",  # Same day
        }

        curr_match = {
            "matchid": "123456",
            "matchnr": "001",
            "avsparkstid": "15:00",
            "speldatum": "2025-08-31",  # Same day
        }

        changes = self.detector.categorize_changes(prev_match, curr_match)

        assert len(changes) == 1
        assert changes[0].priority == ChangePriority.CRITICAL  # Same-day change

    def test_multiple_changes_in_single_match(self):
        """Test detecting multiple changes in a single match."""
        prev_match = {
            "matchid": "123456",
            "matchnr": "001",
            "avsparkstid": "14:00",
            "anlaggningnamn": "Old Stadium",
            "domaruppdraglista": [],
        }

        curr_match = {
            "matchid": "123456",
            "matchnr": "001",
            "avsparkstid": "15:00",
            "anlaggningnamn": "New Stadium",
            "domaruppdraglista": [
                {"domareid": "ref1", "personnamn": "John Doe", "domarrollnamn": "Domare"}
            ],
        }

        changes = self.detector.categorize_changes(prev_match, curr_match)

        # Should detect time change, venue change, and new referee assignment
        assert len(changes) == 3

        categories = {change.category for change in changes}
        assert ChangeCategory.TIME_CHANGE in categories
        assert ChangeCategory.VENUE_CHANGE in categories
        assert ChangeCategory.NEW_ASSIGNMENT in categories
