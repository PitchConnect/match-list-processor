"""Additional tests to boost Milestone 1 coverage above 84% threshold."""

from datetime import datetime

import pytest

from src.notifications.analysis.analyzers import (
    RefereeAssignmentAnalyzer,
    StatusChangeAnalyzer,
    TeamChangeAnalyzer,
    TimeChangeAnalyzer,
    VenueChangeAnalyzer,
)
from src.notifications.analysis.models.analysis_models import (
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)
from src.notifications.analysis.models.change_context import ChangeContext
from src.notifications.monitoring.models import (
    DeliveryAttempt,
    DeliveryResult,
    DeliveryStatus,
    FailureReason,
    NotificationDeliveryRecord,
    NotificationHealthStatus,
)


@pytest.mark.unit
class TestMilestone1CoverageBoost:
    """Additional tests to boost coverage for Milestone 1 implementation."""

    def test_change_context_serialization(self):
        """Test ChangeContext serialization methods."""
        context = ChangeContext(
            field_path="test.field",
            field_display_name="Test Field",
            change_type="modified",
            previous_value="old",
            current_value="new",
            business_impact=ChangeImpact.HIGH,
            urgency=ChangeUrgency.URGENT,
            affected_stakeholders=["teams"],
            change_description="Test change",
            technical_description="Technical test",
            user_friendly_description="User friendly test",
        )

        # Test to_dict
        context_dict = context.to_dict()
        assert context_dict["field_path"] == "test.field"
        assert context_dict["business_impact"] == "high"
        assert context_dict["urgency"] == "urgent"

        # Test from_dict
        restored_context = ChangeContext.from_dict(context_dict)
        assert restored_context.field_path == context.field_path
        assert restored_context.business_impact == context.business_impact
        assert restored_context.urgency == context.urgency

    def test_semantic_analysis_properties(self):
        """Test SemanticChangeAnalysis properties and methods."""
        # Create analysis with critical changes
        critical_change = ChangeContext(
            field_path="status",
            field_display_name="Status",
            change_type="modified",
            previous_value="scheduled",
            current_value="cancelled",
            business_impact=ChangeImpact.CRITICAL,
            urgency=ChangeUrgency.IMMEDIATE,
            affected_stakeholders=["teams"],
            change_description="Match cancelled",
            technical_description="Status changed",
            user_friendly_description="Match cancelled",
        )

        analysis = SemanticChangeAnalysis(
            match_id="test_123",
            change_category="status_changes",
            field_changes=[critical_change],
            overall_impact=ChangeImpact.CRITICAL,
            overall_urgency=ChangeUrgency.IMMEDIATE,
            change_summary="Critical change detected",
            detailed_analysis="Match cancelled",
            stakeholder_impact_map={"teams": ["Match cancelled"]},
            recommended_actions=["Notify immediately"],
        )

        # Test properties
        assert analysis.has_critical_changes is True
        assert analysis.requires_immediate_action is True

        # Test filtering methods
        critical_changes = analysis.get_changes_by_impact(ChangeImpact.CRITICAL)
        assert len(critical_changes) == 1
        assert critical_changes[0] == critical_change

        immediate_changes = analysis.get_changes_by_urgency(ChangeUrgency.IMMEDIATE)
        assert len(immediate_changes) == 1
        assert immediate_changes[0] == critical_change

        # Test with no critical changes
        low_change = ChangeContext(
            field_path="note",
            field_display_name="Note",
            change_type="modified",
            previous_value="old note",
            current_value="new note",
            business_impact=ChangeImpact.LOW,
            urgency=ChangeUrgency.NORMAL,
            affected_stakeholders=["coordinators"],
            change_description="Note updated",
            technical_description="Note field changed",
            user_friendly_description="Note updated",
        )

        low_analysis = SemanticChangeAnalysis(
            match_id="test_456",
            change_category="general_changes",
            field_changes=[low_change],
            overall_impact=ChangeImpact.LOW,
            overall_urgency=ChangeUrgency.NORMAL,
            change_summary="Minor change",
            detailed_analysis="Note updated",
            stakeholder_impact_map={"coordinators": ["Note updated"]},
            recommended_actions=["Update records"],
        )

        assert low_analysis.has_critical_changes is False
        assert low_analysis.requires_immediate_action is False

    def test_delivery_models_serialization(self):
        """Test delivery monitoring model serialization."""
        # Test DeliveryAttempt
        attempt = DeliveryAttempt(
            attempt_number=1,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            status=DeliveryStatus.DELIVERED,
            response_time_ms=150,
            error_message=None,
            failure_reason=None,
        )

        attempt_dict = attempt.to_dict()
        assert attempt_dict["attempt_number"] == 1
        assert attempt_dict["status"] == "delivered"
        assert attempt_dict["response_time_ms"] == 150

        restored_attempt = DeliveryAttempt.from_dict(attempt_dict)
        assert restored_attempt.attempt_number == attempt.attempt_number
        assert restored_attempt.status == attempt.status

        # Test NotificationDeliveryRecord
        record = NotificationDeliveryRecord(
            notification_id="test_notification",
            channel="email",
            recipient="test@example.com",
            created_at=datetime(2024, 1, 15, 10, 0, 0),
            final_status=DeliveryStatus.PENDING,
        )

        record.add_attempt(attempt)

        record_dict = record.to_dict()
        assert record_dict["notification_id"] == "test_notification"
        assert record_dict["channel"] == "email"
        assert len(record_dict["attempts"]) == 1

        restored_record = NotificationDeliveryRecord.from_dict(record_dict)
        assert restored_record.notification_id == record.notification_id
        assert restored_record.total_attempts == record.total_attempts
        assert len(restored_record.attempts) == 1

    def test_delivery_result_properties(self):
        """Test DeliveryResult properties."""
        # Test successful result
        success_result = DeliveryResult(status=DeliveryStatus.DELIVERED, response_time_ms=100)
        assert success_result.success is True

        # Test failed result
        failed_result = DeliveryResult(
            status=DeliveryStatus.FAILED,
            error="Network timeout",
            failure_reason=FailureReason.TIMEOUT,
        )
        assert failed_result.success is False

        # Test sent result
        sent_result = DeliveryResult(status=DeliveryStatus.SENT, response_time_ms=200)
        assert sent_result.success is True

    def test_notification_health_status_serialization(self):
        """Test NotificationHealthStatus serialization."""
        health_status = NotificationHealthStatus(
            status="healthy",
            issues=[],
            last_check=datetime(2024, 1, 15, 12, 0, 0),
            stats={"success_rate": 0.95},
        )

        health_dict = health_status.to_dict()
        assert health_dict["status"] == "healthy"
        assert health_dict["issues"] == []
        assert health_dict["stats"]["success_rate"] == 0.95

    def test_analyzer_edge_cases(self):
        """Test analyzer edge cases and error handling."""
        # Test RefereeAssignmentAnalyzer with empty data
        referee_analyzer = RefereeAssignmentAnalyzer()

        changes = referee_analyzer.analyze_change(
            "domaruppdraglista", None, [], {"matchid": "test"}  # Empty previous  # Empty current
        )
        assert isinstance(changes, list)

        # Test with malformed referee data
        changes = referee_analyzer.analyze_change(
            "domaruppdraglista", "invalid_data", {"invalid": "structure"}, {"matchid": "test"}
        )
        assert isinstance(changes, list)

        # Test TimeChangeAnalyzer with invalid dates
        time_analyzer = TimeChangeAnalyzer()

        changes = time_analyzer.analyze_change(
            "speldatum", "invalid_date", "also_invalid", {"matchid": "test"}
        )
        assert len(changes) == 1
        assert changes[0].field_display_name == "Match Date"

        # Test VenueChangeAnalyzer
        venue_analyzer = VenueChangeAnalyzer()

        changes = venue_analyzer.analyze_change(
            "arena", "Old Stadium", "New Stadium", {"matchid": "test", "speldatum": "2024-01-15"}
        )
        assert len(changes) == 1
        assert "Old Stadium" in changes[0].change_description
        assert "New Stadium" in changes[0].change_description

        # Test TeamChangeAnalyzer
        team_analyzer = TeamChangeAnalyzer()

        changes = team_analyzer.analyze_change(
            "hemmalag", "Team A", "Team B", {"matchid": "test", "speldatum": "2024-01-15"}
        )
        assert len(changes) == 1
        assert changes[0].field_display_name == "Home Team"

        # Test StatusChangeAnalyzer
        status_analyzer = StatusChangeAnalyzer()

        changes = status_analyzer.analyze_change(
            "status", "scheduled", "cancelled", {"matchid": "test", "speldatum": "2024-01-15"}
        )
        assert len(changes) == 1
        assert changes[0].business_impact == ChangeImpact.CRITICAL

    def test_analyzer_helper_methods(self):
        """Test analyzer helper methods."""
        from src.notifications.analysis.base_analyzer import FieldAnalyzer

        # Create a concrete analyzer for testing
        class TestAnalyzer(FieldAnalyzer):
            def can_analyze(self, field_path: str) -> bool:
                return True

            def analyze_change(self, field_path: str, prev_value, curr_value, match_context):
                return []

        analyzer = TestAnalyzer()

        # Test urgency assessment
        today = datetime.now().strftime("%Y-%m-%d")
        urgency = analyzer.assess_urgency(today)
        assert urgency == ChangeUrgency.IMMEDIATE

        # Test date formatting
        formatted_date = analyzer.format_date_friendly("2024-01-15")
        assert "January" in formatted_date
        assert "2024" in formatted_date

        # Test team name extraction
        match_context = {"hemmalag": "Home Team", "bortalag": "Away Team"}
        home, away = analyzer.extract_team_names(match_context)
        assert home == "Home Team"
        assert away == "Away Team"

        # Test with missing team names
        empty_context = {}
        home, away = analyzer.extract_team_names(empty_context)
        assert home == "Home Team"  # Default value
        assert away == "Away Team"  # Default value

        # Test match date extraction
        date_context = {"speldatum": "2024-01-15"}
        extracted_date = analyzer.extract_match_date(date_context)
        assert extracted_date == "2024-01-15"

        # Test with missing date
        no_date_context = {}
        extracted_date = analyzer.extract_match_date(no_date_context)
        assert extracted_date  # Should return today's date

    def test_time_analyzer_calculations(self):
        """Test TimeChangeAnalyzer calculation methods."""
        time_analyzer = TimeChangeAnalyzer()

        # Test date difference calculation
        diff = time_analyzer._calculate_date_difference("2024-01-15", "2024-01-16")
        assert "moved forward by 1 day" in diff

        diff = time_analyzer._calculate_date_difference("2024-01-16", "2024-01-15")
        assert "moved back by 1 day" in diff

        diff = time_analyzer._calculate_date_difference("2024-01-15", "2024-01-15")
        assert "same date" in diff

        # Test time difference calculation
        diff = time_analyzer._calculate_time_difference("15:00", "16:00")
        assert "moved later by 1h 0m" in diff

        diff = time_analyzer._calculate_time_difference("16:00", "15:00")
        assert "moved earlier by 1h 0m" in diff

        diff = time_analyzer._calculate_time_difference("15:00", "15:00")
        assert "same time" in diff

        # Test with invalid time formats
        diff = time_analyzer._calculate_time_difference("invalid", "also_invalid")
        assert diff == "updated"
