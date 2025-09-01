"""Tests for Milestone 1 semantic analysis implementation."""

from datetime import datetime

import pytest

from src.notifications.analysis.models.analysis_models import (
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)
from src.notifications.analysis.semantic_analyzer import SemanticChangeAnalyzer


@pytest.mark.unit
class TestSemanticChangeAnalyzer:
    """Test semantic change analyzer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SemanticChangeAnalyzer()

        self.sample_prev_match = {
            "matchid": "12345",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "tid": "15:00",
            "domaruppdraglista": [{"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"}],
        }

        self.sample_curr_match = {
            "matchid": "12345",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "tid": "16:00",  # Time changed
            "domaruppdraglista": [
                {"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"},
                {
                    "id": "ref2",
                    "namn": "Jane Smith",
                    "uppdragstyp": "Assisterande dommare",
                },  # New referee
            ],
        }

    def test_analyze_match_changes_with_time_and_referee_changes(self):
        """Test analysis of match with time and referee changes."""
        analysis = self.analyzer.analyze_match_changes(
            self.sample_prev_match, self.sample_curr_match
        )

        assert isinstance(analysis, SemanticChangeAnalysis)
        assert analysis.match_id == "12345"
        assert len(analysis.field_changes) >= 2  # Time change + referee addition

        # Check that we have both time and referee changes
        change_types = [change.field_display_name for change in analysis.field_changes]
        assert any("Time" in change_type for change_type in change_types)
        assert any("Referee" in change_type for change_type in change_types)

    def test_analyze_no_changes(self):
        """Test analysis when no changes are detected."""
        analysis = self.analyzer.analyze_match_changes(
            self.sample_prev_match, self.sample_prev_match  # Same data
        )

        assert analysis.change_category == "no_changes"
        assert len(analysis.field_changes) == 0
        assert analysis.overall_impact == ChangeImpact.INFORMATIONAL
        assert analysis.change_summary == "No changes detected"

    def test_analyze_referee_assignment_changes(self):
        """Test analysis of referee assignment changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()

        # Add new referee
        curr_match["domaruppdraglista"] = [
            {"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"},
            {"id": "ref2", "namn": "Jane Smith", "uppdragstyp": "Assisterande dommare"},
        ]

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        assert analysis.change_category == "referee_changes"
        assert len(analysis.field_changes) >= 1

        # Check referee change details
        referee_changes = [c for c in analysis.field_changes if "Referee" in c.field_display_name]
        assert len(referee_changes) >= 1
        assert referee_changes[0].change_type == "added"
        assert "Jane Smith" in referee_changes[0].change_description

    def test_analyze_time_changes(self):
        """Test analysis of time changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()
        curr_match["tid"] = "17:00"  # Change time

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        assert analysis.change_category == "time_changes"
        time_changes = [c for c in analysis.field_changes if "Time" in c.field_display_name]
        assert len(time_changes) >= 1
        assert time_changes[0].change_type == "modified"
        assert "15:00" in time_changes[0].change_description
        assert "17:00" in time_changes[0].change_description

    def test_analyze_venue_changes(self):
        """Test analysis of venue changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()

        prev_match["arena"] = "Stadium A"
        curr_match["arena"] = "Stadium B"

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        venue_changes = [c for c in analysis.field_changes if "Venue" in c.field_display_name]
        assert len(venue_changes) >= 1
        assert venue_changes[0].change_type == "modified"
        assert "Stadium A" in venue_changes[0].change_description
        assert "Stadium B" in venue_changes[0].change_description

    def test_analyze_team_changes(self):
        """Test analysis of team changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()
        curr_match["hemmalag"] = "Team C"  # Change home team

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        team_changes = [c for c in analysis.field_changes if "Team" in c.field_display_name]
        assert len(team_changes) >= 1
        assert team_changes[0].change_type == "modified"
        assert "Team A" in team_changes[0].change_description
        assert "Team C" in team_changes[0].change_description

    def test_analyze_status_changes(self):
        """Test analysis of status changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()

        prev_match["status"] = "scheduled"
        curr_match["status"] = "cancelled"

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        status_changes = [c for c in analysis.field_changes if "Status" in c.field_display_name]
        assert len(status_changes) >= 1
        assert status_changes[0].change_type == "modified"
        assert (
            status_changes[0].business_impact == ChangeImpact.CRITICAL
        )  # Cancellation is critical

    def test_urgency_assessment_immediate(self):
        """Test urgency assessment for immediate changes."""
        # Match today
        today = datetime.now().strftime("%Y-%m-%d")
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()

        prev_match["speldatum"] = today
        curr_match["speldatum"] = today
        curr_match["tid"] = "17:00"  # Time change for today's match

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Should have immediate urgency for today's match
        time_changes = [c for c in analysis.field_changes if "Time" in c.field_display_name]
        assert len(time_changes) >= 1
        assert time_changes[0].urgency in [ChangeUrgency.IMMEDIATE, ChangeUrgency.URGENT]

    def test_stakeholder_impact_mapping(self):
        """Test stakeholder impact mapping."""
        analysis = self.analyzer.analyze_match_changes(
            self.sample_prev_match, self.sample_curr_match
        )

        assert isinstance(analysis.stakeholder_impact_map, dict)
        assert len(analysis.stakeholder_impact_map) > 0

        # Should have stakeholders affected by changes
        expected_stakeholders = ["teams", "referees", "coordinators"]
        for stakeholder in expected_stakeholders:
            if stakeholder in analysis.stakeholder_impact_map:
                assert isinstance(analysis.stakeholder_impact_map[stakeholder], list)
                assert len(analysis.stakeholder_impact_map[stakeholder]) > 0

    def test_recommended_actions_generation(self):
        """Test recommended actions generation."""
        analysis = self.analyzer.analyze_match_changes(
            self.sample_prev_match, self.sample_curr_match
        )

        assert isinstance(analysis.recommended_actions, list)
        assert len(analysis.recommended_actions) > 0

        # Should have specific actions based on change types
        actions_text = " ".join(analysis.recommended_actions).lower()
        assert any(keyword in actions_text for keyword in ["notify", "update", "send", "confirm"])

    def test_correlation_detection(self):
        """Test detection of correlated changes."""
        prev_match = self.sample_prev_match.copy()
        curr_match = self.sample_prev_match.copy()

        # Make multiple related changes
        curr_match["tid"] = "17:00"  # Time change
        curr_match["speldatum"] = "2024-01-16"  # Date change
        curr_match["arena"] = "New Stadium"  # Venue change

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Should detect multiple changes
        assert len(analysis.field_changes) >= 3

        # Should have appropriate overall impact
        assert analysis.overall_impact in [ChangeImpact.HIGH, ChangeImpact.CRITICAL]

    def test_change_context_properties(self):
        """Test change context properties and methods."""
        analysis = self.analyzer.analyze_match_changes(
            self.sample_prev_match, self.sample_curr_match
        )

        # Test analysis properties
        if analysis.field_changes:
            # Test has_critical_changes property
            critical_changes = analysis.get_changes_by_impact(ChangeImpact.CRITICAL)
            assert analysis.has_critical_changes == (len(critical_changes) > 0)

            # Test requires_immediate_action property
            expected_immediate = (
                analysis.overall_urgency == ChangeUrgency.IMMEDIATE
                or analysis.overall_impact == ChangeImpact.CRITICAL
            )
            assert analysis.requires_immediate_action == expected_immediate

    def test_field_change_detection(self):
        """Test detailed field change detection."""
        prev_match = {"a": {"b": {"c": "old_value"}}, "list": [1, 2, 3]}
        curr_match = {"a": {"b": {"c": "new_value"}}, "list": [1, 2, 3, 4]}

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Should detect nested field changes
        # Note: The actual field paths depend on the analyzer implementation
        # This test verifies that changes are detected at some level
        assert len(analysis.field_changes) > 0
