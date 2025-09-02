"""Integration tests for semantic analysis to notification delivery workflow."""

import unittest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from src.core.unified_processor import UnifiedMatchProcessor
from src.notifications.adapters.semantic_to_legacy_adapter import SemanticToLegacyAdapter
from src.notifications.analysis.models.analysis_models import (
    ChangeContext,
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)
from src.notifications.analysis.semantic_analyzer import SemanticChangeAnalyzer


class TestSemanticNotificationIntegration(unittest.TestCase):
    """Integration tests for semantic analysis to notification delivery."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_timestamp = datetime(2024, 1, 15, 10, 30, 0)

        # Sample match data
        self.prev_match = {
            "matchid": "12345",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "tid": "15:00",
            "domaruppdraglista": [{"id": "ref1", "namn": "John Doe"}],
        }

        self.curr_match = {
            "matchid": "12345",
            "hemmalag": "Team A",
            "bortalag": "Team B",
            "speldatum": "2024-01-15",
            "tid": "16:00",  # Time changed
            "domaruppdraglista": [
                {"id": "ref1", "namn": "John Doe"},
                {"id": "ref2", "namn": "Jane Smith"},  # New referee
            ],
        }

    @patch.dict("os.environ", {"ENABLE_SEMANTIC_ANALYSIS": "true"})
    def test_end_to_end_semantic_to_notification(self):
        """Test complete flow from semantic analysis to notification delivery."""
        # Mock notification service
        mock_notification_service = Mock()
        mock_notification_service.process_changes = AsyncMock(
            return_value={
                "enabled": True,
                "notifications_sent": 2,
                "delivery_results": {"success": True},
            }
        )

        # Mock other services
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch(
                "src.core.unified_processor.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            # Create processor with semantic analysis enabled
            processor = UnifiedMatchProcessor(
                notification_config={"enabled": True, "channels": ["email"]}
            )

            # Verify semantic analysis is enabled
            self.assertTrue(processor.use_semantic_analysis)
            self.assertIsNotNone(processor.semantic_analyzer)
            self.assertIsNotNone(processor.semantic_adapter)

            # Mock change detection to return changes
            mock_changes = Mock()
            mock_changes.has_changes = True
            mock_changes.changed_matches = ["12345"]

            # Mock change detector methods
            processor.change_detector.load_previous_matches = Mock(return_value=[self.prev_match])
            processor.change_detector._convert_to_dict = Mock(
                side_effect=[
                    {"12345": self.prev_match},  # Previous matches
                    {"12345": self.curr_match},  # Current matches
                ]
            )

            # Test semantic analysis integration
            result = processor._perform_semantic_analysis(mock_changes, [self.curr_match])

            # Verify semantic analysis was performed
            self.assertIsNotNone(result)

            # Verify the result is a CategorizedChanges object
            from src.core.change_categorization import CategorizedChanges

            self.assertIsInstance(result, CategorizedChanges)

            # Verify changes were detected and converted
            self.assertGreater(result.total_changes, 0)

    def test_semantic_analysis_with_delivery_monitoring(self):
        """Test semantic analysis integration with delivery monitoring."""
        # Create semantic analyzer and adapter
        analyzer = SemanticChangeAnalyzer()
        adapter = SemanticToLegacyAdapter()

        # Perform semantic analysis
        semantic_analysis = analyzer.analyze_match_changes(self.prev_match, self.curr_match)

        # Verify semantic analysis results
        self.assertIsInstance(semantic_analysis, SemanticChangeAnalysis)
        self.assertEqual(semantic_analysis.match_id, "12345")
        self.assertGreater(len(semantic_analysis.field_changes), 0)

        # Convert to legacy format
        categorized_changes = adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify conversion preserved semantic information
        self.assertGreater(categorized_changes.total_changes, 0)

        # Verify change details contain semantic context
        for change in categorized_changes.changes:
            self.assertIsNotNone(change.match_id)
            self.assertIsNotNone(change.category)
            self.assertIsNotNone(change.priority)
            self.assertIsNotNone(change.change_description)

    @patch.dict("os.environ", {"ENABLE_SEMANTIC_ANALYSIS": "false"})
    def test_fallback_to_legacy_detection(self):
        """Test fallback to legacy detection when semantic analysis is disabled."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
        ):
            # Create processor with semantic analysis disabled
            processor = UnifiedMatchProcessor()

            # Verify semantic analysis is disabled
            self.assertFalse(processor.use_semantic_analysis)
            self.assertFalse(hasattr(processor, "semantic_analyzer"))

    @patch.dict("os.environ", {"ENABLE_SEMANTIC_ANALYSIS": "true", "FALLBACK_TO_LEGACY": "true"})
    def test_semantic_analysis_error_fallback(self):
        """Test fallback to legacy when semantic analysis fails."""
        # Mock notification service
        mock_notification_service = Mock()
        mock_notification_service.process_changes = AsyncMock(
            return_value={"enabled": True, "notifications_sent": 1}
        )

        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch(
                "src.core.unified_processor.NotificationService",
                return_value=mock_notification_service,
            ),
        ):
            processor = UnifiedMatchProcessor(
                notification_config={"enabled": True, "channels": ["email"]}
            )

            # Mock semantic analyzer to raise an exception
            processor.semantic_analyzer.analyze_match_changes = Mock(
                side_effect=Exception("Semantic analysis failed")
            )

            # Mock changes with categorized_changes for fallback
            mock_changes = Mock()
            mock_changes.has_changes = True
            mock_changes.categorized_changes = Mock()
            mock_changes.categorized_changes.changes = []

            # Test notification sending with fallback
            result = processor._send_notifications(mock_changes, [self.curr_match])

            # Verify fallback was used
            self.assertIsNotNone(result)
            self.assertFalse(result.get("semantic_analysis", True))

    def test_performance_with_semantic_analysis(self):
        """Test performance impact of semantic analysis."""
        import time

        analyzer = SemanticChangeAnalyzer()
        adapter = SemanticToLegacyAdapter()

        # Measure semantic analysis performance
        start_time = time.time()

        semantic_analysis = analyzer.analyze_match_changes(self.prev_match, self.curr_match)
        categorized_changes = adapter.convert_semantic_to_categorized(semantic_analysis)

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify performance is reasonable (should be under 1 second for simple changes)
        self.assertLess(processing_time, 1.0, "Semantic analysis took too long")

        # Verify results are still correct
        self.assertIsInstance(categorized_changes, type(categorized_changes))
        self.assertGreater(categorized_changes.total_changes, 0)

    def test_complex_multi_field_changes(self):
        """Test semantic analysis with complex multi-field changes."""
        # Create a match with multiple changes
        complex_curr_match = {
            "matchid": "12345",
            "hemmalag": "Team A",
            "bortalag": "Team C",  # Team changed
            "speldatum": "2024-01-16",  # Date changed
            "tid": "16:00",  # Time changed
            "anlaggningnamn": "Stadium B",  # Venue changed
            "domaruppdraglista": [
                {"id": "ref2", "namn": "Jane Smith"},  # Referee changed
            ],
        }

        analyzer = SemanticChangeAnalyzer()
        adapter = SemanticToLegacyAdapter()

        # Perform analysis
        semantic_analysis = analyzer.analyze_match_changes(self.prev_match, complex_curr_match)
        categorized_changes = adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify multiple changes were detected
        self.assertGreater(categorized_changes.total_changes, 1)

        # Verify different change categories are present
        self.assertGreater(len(categorized_changes.change_categories), 1)

        # Verify stakeholders are properly mapped
        self.assertGreater(len(categorized_changes.affected_stakeholder_types), 0)

    def test_edge_cases_and_error_scenarios(self):
        """Test edge cases and error scenarios."""
        adapter = SemanticToLegacyAdapter()

        # Test with empty field changes
        empty_analysis = SemanticChangeAnalysis(
            match_id="empty",
            change_category="no_changes",
            field_changes=[],
            overall_impact=ChangeImpact.INFORMATIONAL,
            overall_urgency=ChangeUrgency.NORMAL,
            change_summary="No changes",
            detailed_analysis="No changes detected",
            stakeholder_impact_map={},
            recommended_actions=[],
            analysis_timestamp=self.test_timestamp,
        )

        result = adapter.convert_semantic_to_categorized(empty_analysis)
        self.assertEqual(result.total_changes, 0)

        # Test with None values
        context_with_none = ChangeContext(
            field_path="test_field",
            field_display_name="Test Field",
            change_type="modified",
            previous_value=None,
            current_value=None,
            business_impact=ChangeImpact.LOW,
            urgency=ChangeUrgency.NORMAL,
            affected_stakeholders=[],
            change_description="Test change",
            technical_description="Technical description",
            user_friendly_description="User friendly description",
            timestamp=self.test_timestamp,
        )

        analysis_with_none = SemanticChangeAnalysis(
            match_id="test_none",
            change_category="general_changes",
            field_changes=[context_with_none],
            overall_impact=ChangeImpact.LOW,
            overall_urgency=ChangeUrgency.NORMAL,
            change_summary="Test change",
            detailed_analysis="Test analysis",
            stakeholder_impact_map={},
            recommended_actions=[],
            analysis_timestamp=self.test_timestamp,
        )

        result = adapter.convert_semantic_to_categorized(analysis_with_none)
        self.assertEqual(result.total_changes, 1)

        # Verify None values are handled properly
        change = result.changes[0]
        self.assertEqual(change.previous_value, "")
        self.assertEqual(change.current_value, "")

    def test_configuration_driven_behavior(self):
        """Test configuration-driven behavior of semantic analysis."""
        # Test with semantic analysis enabled
        with patch.dict("os.environ", {"ENABLE_SEMANTIC_ANALYSIS": "true"}):
            with (
                patch("src.core.unified_processor.DockerNetworkApiClient"),
                patch("src.core.unified_processor.WhatsAppAvatarService"),
                patch("src.core.unified_processor.GoogleDriveStorageService"),
                patch("src.core.unified_processor.FogisPhonebookSyncService"),
            ):
                processor = UnifiedMatchProcessor()
                self.assertTrue(processor.use_semantic_analysis)

        # Test with semantic analysis disabled
        with patch.dict("os.environ", {"ENABLE_SEMANTIC_ANALYSIS": "false"}):
            with (
                patch("src.core.unified_processor.DockerNetworkApiClient"),
                patch("src.core.unified_processor.WhatsAppAvatarService"),
                patch("src.core.unified_processor.GoogleDriveStorageService"),
                patch("src.core.unified_processor.FogisPhonebookSyncService"),
            ):
                processor = UnifiedMatchProcessor()
                self.assertFalse(processor.use_semantic_analysis)

        # Test fallback configuration
        with patch.dict("os.environ", {"FALLBACK_TO_LEGACY": "false"}):
            with (
                patch("src.core.unified_processor.DockerNetworkApiClient"),
                patch("src.core.unified_processor.WhatsAppAvatarService"),
                patch("src.core.unified_processor.GoogleDriveStorageService"),
                patch("src.core.unified_processor.FogisPhonebookSyncService"),
            ):
                processor = UnifiedMatchProcessor()
                self.assertFalse(processor.fallback_to_legacy)


if __name__ == "__main__":
    unittest.main()
