"""Integration tests for Milestone 1 implementation."""

import tempfile
from datetime import datetime, timezone

import pytest

from src.notifications.analysis.analyzers import (
    RefereeAssignmentAnalyzer,
    StatusChangeAnalyzer,
    TeamChangeAnalyzer,
    TimeChangeAnalyzer,
    VenueChangeAnalyzer,
)
from src.notifications.analysis.models.analysis_models import ChangeImpact, ChangeUrgency
from src.notifications.analysis.semantic_analyzer import SemanticChangeAnalyzer
from src.notifications.monitoring.delivery_monitor import DeliveryMonitor
from src.notifications.monitoring.health_checker import NotificationHealthChecker
from src.notifications.monitoring.models import DeliveryStatus, FailureReason


@pytest.mark.unit
class TestMilestone1Integration:
    """Integration tests for Milestone 1 features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = SemanticChangeAnalyzer()

        # Create temporary file for delivery monitor
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.delivery_monitor = DeliveryMonitor(storage_path=self.temp_file.name)

        self.health_checker = NotificationHealthChecker(delivery_monitor=self.delivery_monitor)

    def test_complete_semantic_analysis_workflow(self):
        """Test complete semantic analysis workflow with multiple changes."""
        prev_match = {
            "matchid": "integration_test",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "tid": "15:00",
            "arena": "Stadium A",
            "status": "scheduled",
            "domaruppdraglista": [{"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"}],
        }

        curr_match = {
            "matchid": "integration_test",
            "hemmalag": "Team A",
            "bortalag": "Team C",  # Team change
            "speldatum": "2024-01-16",  # Date change
            "tid": "16:00",  # Time change
            "arena": "Stadium B",  # Venue change
            "status": "confirmed",  # Status change
            "domaruppdraglista": [
                {"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"},
                {
                    "id": "ref2",
                    "namn": "Jane Smith",
                    "uppdragstyp": "Assisterande dommare",
                },  # New referee
            ],
        }

        # Perform semantic analysis
        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Verify comprehensive analysis
        assert analysis.match_id == "integration_test"
        assert len(analysis.field_changes) >= 5  # Multiple changes detected

        # Verify different change types are detected
        change_types = [change.field_display_name for change in analysis.field_changes]
        expected_types = ["Team", "Time", "Venue", "Status", "Referee"]

        for expected_type in expected_types:
            assert any(
                expected_type in change_type for change_type in change_types
            ), f"Missing {expected_type} change"

        # Verify stakeholder impact mapping
        assert len(analysis.stakeholder_impact_map) > 0
        assert "teams" in analysis.stakeholder_impact_map
        assert "referees" in analysis.stakeholder_impact_map

        # Verify recommended actions
        assert len(analysis.recommended_actions) > 0

        # Verify overall impact assessment (should be at least medium with multiple changes)
        assert analysis.overall_impact in [
            ChangeImpact.MEDIUM,
            ChangeImpact.HIGH,
            ChangeImpact.CRITICAL,
        ]

    def test_analyzer_specialization_coverage(self):
        """Test that all specialized analyzers are properly integrated."""
        # Test referee analyzer
        referee_analyzer = RefereeAssignmentAnalyzer()
        assert referee_analyzer.can_analyze("domaruppdraglista[0].namn")

        # Test time analyzer
        time_analyzer = TimeChangeAnalyzer()
        assert time_analyzer.can_analyze("speldatum")
        assert time_analyzer.can_analyze("tid")

        # Test venue analyzer
        venue_analyzer = VenueChangeAnalyzer()
        assert venue_analyzer.can_analyze("arena")
        assert venue_analyzer.can_analyze("plan")

        # Test team analyzer
        team_analyzer = TeamChangeAnalyzer()
        assert team_analyzer.can_analyze("hemmalag")
        assert team_analyzer.can_analyze("bortalag")

        # Test status analyzer
        status_analyzer = StatusChangeAnalyzer()
        assert status_analyzer.can_analyze("status")
        assert status_analyzer.can_analyze("matchstatus")

    def test_delivery_monitoring_integration(self):
        """Test delivery monitoring integration with retry mechanisms."""
        # Record successful delivery
        self.delivery_monitor.record_delivery_attempt(
            notification_id="integration_success",
            channel="email",
            recipient="success@example.com",
            status=DeliveryStatus.DELIVERED,
            response_time_ms=150,
        )

        # Record failed delivery with retry
        self.delivery_monitor.record_delivery_attempt(
            notification_id="integration_retry",
            channel="discord",
            recipient="retry_webhook",
            status=DeliveryStatus.FAILED,
            failure_reason=FailureReason.NETWORK_ERROR,
        )

        # Record non-retryable failure
        self.delivery_monitor.record_delivery_attempt(
            notification_id="integration_dead",
            channel="webhook",
            recipient="invalid_webhook",
            status=DeliveryStatus.FAILED,
            failure_reason=FailureReason.INVALID_RECIPIENT,
        )

        # Verify delivery records
        assert len(self.delivery_monitor.delivery_records) == 3

        # Verify retry queue
        assert len(self.delivery_monitor.retry_queue) == 1
        retry_item = self.delivery_monitor.retry_queue[0]
        assert retry_item["notification_id"] == "integration_retry"

        # Verify dead letter queue
        assert len(self.delivery_monitor.dead_letter_queue) == 1
        dead_item = self.delivery_monitor.dead_letter_queue[0]
        assert dead_item["notification_id"] == "integration_dead"

        # Test statistics
        stats = self.delivery_monitor.get_delivery_stats(24)
        assert stats["total_notifications"] == 3
        assert stats["delivered"] == 1
        assert stats["failed"] == 0  # Failed items move to retrying or dead_letter
        assert stats["dead_letter"] == 1
        assert stats["retrying"] == 1

    def test_health_monitoring_integration(self):
        """Test health monitoring integration."""
        # Add some delivery records for health assessment

        # Add successful deliveries
        for i in range(8):
            self.delivery_monitor.record_delivery_attempt(
                notification_id=f"health_success_{i}",
                channel="email",
                recipient=f"health{i}@example.com",
                status=DeliveryStatus.DELIVERED,
            )

        # Add failed deliveries
        for i in range(2):
            self.delivery_monitor.record_delivery_attempt(
                notification_id=f"health_failed_{i}",
                channel="discord",
                recipient=f"health_failed_{i}",
                status=DeliveryStatus.FAILED,
                failure_reason=FailureReason.NETWORK_ERROR,
            )

        # Check health status
        health = self.health_checker.check_overall_health()

        assert health.status in ["healthy", "degraded"]
        assert isinstance(health.issues, list)
        assert isinstance(health.stats, dict)
        assert health.last_check is not None

        # Verify delivery stats are included
        assert "delivery" in health.stats
        delivery_stats = health.stats["delivery"]
        assert delivery_stats["total_notifications"] == 10
        assert delivery_stats["success_rate"] == 0.8  # 8/10

    @pytest.mark.asyncio
    async def test_retry_queue_processing(self):
        """Test retry queue processing workflow."""
        # Add failed delivery that should be retried
        self.delivery_monitor.record_delivery_attempt(
            notification_id="retry_test",
            channel="webhook",
            recipient="https://example.com/webhook",
            status=DeliveryStatus.FAILED,
            failure_reason=FailureReason.TIMEOUT,
        )

        # Verify retry was scheduled
        assert len(self.delivery_monitor.retry_queue) == 1

        # Manually set retry time to past for testing
        self.delivery_monitor.retry_queue[0]["retry_time"] = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        )

        # Process retry queue
        ready_items = await self.delivery_monitor.process_retry_queue()

        # Verify item was returned for retry
        assert len(ready_items) == 1
        assert ready_items[0]["notification_id"] == "retry_test"

        # Verify item was removed from queue
        assert len(self.delivery_monitor.retry_queue) == 0

    def test_change_urgency_assessment(self):
        """Test urgency assessment across different analyzers."""
        # Test immediate urgency (today's match)
        today = datetime.now().strftime("%Y-%m-%d")

        prev_match = {"speldatum": today, "tid": "15:00"}
        curr_match = {"speldatum": today, "tid": "16:00"}

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Should have urgent or immediate urgency for today's match
        time_changes = [c for c in analysis.field_changes if "Time" in c.field_display_name]
        assert len(time_changes) > 0
        assert time_changes[0].urgency in [ChangeUrgency.IMMEDIATE, ChangeUrgency.URGENT]

    def test_stakeholder_impact_analysis(self):
        """Test stakeholder impact analysis across change types."""
        prev_match = {
            "matchid": "stakeholder_test",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "arena": "Stadium A",
            "domaruppdraglista": [{"id": "ref1", "namn": "John Doe", "uppdragstyp": "Huvuddomare"}],
        }

        curr_match = prev_match.copy()
        curr_match["arena"] = "Stadium B"  # Venue change affects many stakeholders

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Venue changes should affect multiple stakeholder types
        venue_changes = [c for c in analysis.field_changes if "Venue" in c.field_display_name]
        assert len(venue_changes) > 0

        venue_change = venue_changes[0]
        expected_stakeholders = ["teams", "referees", "coordinators", "venue", "spectators"]

        for stakeholder in expected_stakeholders:
            assert stakeholder in venue_change.affected_stakeholders

    def test_correlation_detection(self):
        """Test correlation detection for related changes."""
        prev_match = {
            "matchid": "correlation_test",
            "speldatum": "2024-01-15",
            "tid": "15:00",
            "arena": "Stadium A",
        }

        curr_match = {
            "matchid": "correlation_test",
            "speldatum": "2024-01-16",  # Date change
            "tid": "16:00",  # Time change
            "arena": "Stadium B",  # Venue change
        }

        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)

        # Should detect multiple related changes
        assert len(analysis.field_changes) >= 3

        # Should have high overall impact due to multiple changes
        assert analysis.overall_impact in [ChangeImpact.HIGH, ChangeImpact.CRITICAL]

        # Should have comprehensive recommended actions
        assert len(analysis.recommended_actions) >= 3

        # Should affect multiple stakeholder groups
        assert len(analysis.stakeholder_impact_map) >= 3

    def test_error_handling_and_resilience(self):
        """Test error handling and system resilience."""
        # Test with malformed match data
        prev_match = {"invalid": "data"}
        curr_match = {"also_invalid": "data"}

        # Should not crash and should handle gracefully
        analysis = self.analyzer.analyze_match_changes(prev_match, curr_match)
        assert analysis is not None
        assert analysis.match_id == "unknown"

        # Test delivery monitor with invalid data
        try:
            self.delivery_monitor.record_delivery_attempt(
                notification_id="",  # Empty ID
                channel="invalid_channel",
                recipient="",  # Empty recipient
                status=DeliveryStatus.FAILED,
            )
            # Should not crash
        except Exception as e:
            # If it does raise an exception, it should be handled gracefully
            assert isinstance(e, (ValueError, TypeError))

    def teardown_method(self):
        """Clean up test fixtures."""
        try:
            import os

            os.unlink(self.temp_file.name)
        except FileNotFoundError:
            pass
