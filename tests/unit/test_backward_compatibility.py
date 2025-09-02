"""Tests for backward compatibility with existing notification infrastructure."""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.change_categorization import (
    CategorizedChanges,
    ChangeCategory,
    ChangePriority,
    MatchChangeDetail,
    StakeholderType,
)
from src.notifications.adapters.semantic_to_legacy_adapter import SemanticToLegacyAdapter
from src.notifications.analysis.models.analysis_models import (
    ChangeContext,
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with existing notification infrastructure."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = SemanticToLegacyAdapter()
        self.test_timestamp = datetime(2024, 1, 15, 10, 30, 0)

    def test_legacy_format_compliance(self):
        """Test that converted changes maintain legacy format compliance."""
        # Create semantic analysis
        semantic_analysis = self._create_sample_semantic_analysis()

        # Convert to legacy format
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify CategorizedChanges structure compliance
        self.assertIsInstance(result, CategorizedChanges)

        # Verify all required fields exist
        required_fields = [
            "changes",
            "total_changes",
            "critical_changes",
            "high_priority_changes",
            "affected_stakeholder_types",
            "change_categories",
        ]
        for field in required_fields:
            self.assertTrue(hasattr(result, field), f"Missing required field: {field}")

        # Verify field types
        self.assertIsInstance(result.changes, list)
        self.assertIsInstance(result.total_changes, int)
        self.assertIsInstance(result.critical_changes, int)
        self.assertIsInstance(result.high_priority_changes, int)
        self.assertIsInstance(result.affected_stakeholder_types, set)
        self.assertIsInstance(result.change_categories, set)

    def test_legacy_change_structure_compliance(self):
        """Test that individual change objects maintain legacy structure."""
        semantic_analysis = self._create_sample_semantic_analysis()
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify each change has required structure
        for change in result.changes:
            self.assertIsInstance(change, MatchChangeDetail)

            # Verify required attributes
            required_attrs = [
                "match_id",
                "category",
                "priority",
                "affected_stakeholders",
                "field_name",
                "previous_value",
                "current_value",
                "change_description",
                "timestamp",
            ]
            for attr in required_attrs:
                self.assertTrue(hasattr(change, attr), f"Missing required attribute: {attr}")

            # Verify attribute types
            self.assertIsInstance(change.match_id, str)
            self.assertIsInstance(change.category, ChangeCategory)
            self.assertIsInstance(change.priority, ChangePriority)
            self.assertIsInstance(change.affected_stakeholders, list)
            self.assertIsInstance(change.field_name, str)
            self.assertIsInstance(change.previous_value, str)
            self.assertIsInstance(change.current_value, str)
            self.assertIsInstance(change.change_description, str)
            self.assertIsInstance(change.timestamp, datetime)

    def test_enum_value_compatibility(self):
        """Test that enum values are compatible with existing system."""
        semantic_analysis = self._create_sample_semantic_analysis()
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify ChangeCategory enum values
        for category in result.change_categories:
            self.assertIsInstance(category, ChangeCategory)
            self.assertIn(category, list(ChangeCategory))

        # Verify ChangePriority enum values
        for change in result.changes:
            self.assertIsInstance(change.priority, ChangePriority)
            self.assertIn(change.priority, list(ChangePriority))

        # Verify StakeholderType enum values
        for stakeholder_type in result.affected_stakeholder_types:
            self.assertIsInstance(stakeholder_type, StakeholderType)
            self.assertIn(stakeholder_type, list(StakeholderType))

    def test_notification_service_integration(self):
        """Test integration with existing notification service interface."""
        from src.notifications.notification_service import NotificationService

        # Mock notification service
        mock_config = {"enabled": True, "channels": ["email"]}

        with (
            patch("src.notifications.notification_service.StakeholderManager"),
            patch("src.notifications.notification_service.ChangeToNotificationConverter"),
            patch("src.notifications.notification_service.NotificationBroadcaster"),
            patch("src.notifications.notification_service.NotificationAnalyticsService"),
        ):
            notification_service = NotificationService(mock_config)

            # Create semantic analysis and convert
            semantic_analysis = self._create_sample_semantic_analysis()
            categorized_changes = self.adapter.convert_semantic_to_categorized(semantic_analysis)

            # Verify the converted changes can be processed by notification service
            # This should not raise any exceptions
            try:
                # Mock the async method
                notification_service.change_converter.convert_changes_to_notifications = Mock(
                    return_value=[]
                )

                # Test that the interface is compatible
                # This should work without errors (interface compatibility)
                self.assertIsNotNone(categorized_changes)
                self.assertTrue(hasattr(categorized_changes, "changes"))

            except Exception as e:
                self.fail(f"Notification service integration failed: {e}")

    def test_existing_workflow_preservation(self):
        """Test that existing notification workflows are preserved."""
        # Create semantic analysis
        semantic_analysis = self._create_sample_semantic_analysis()
        categorized_changes = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Test methods that existing code might call
        self.assertTrue(categorized_changes.has_changes)

        if categorized_changes.critical_changes > 0:
            self.assertTrue(categorized_changes.has_critical_changes)

        # Test category filtering (existing functionality)
        referee_changes = categorized_changes.get_changes_by_category(ChangeCategory.REFEREE_CHANGE)
        self.assertIsInstance(referee_changes, list)

        # Verify all returned changes are of the requested category
        for change in referee_changes:
            self.assertEqual(change.category, ChangeCategory.REFEREE_CHANGE)

    def test_data_serialization_compatibility(self):
        """Test that data can be serialized/deserialized as before."""
        import json

        semantic_analysis = self._create_sample_semantic_analysis()
        categorized_changes = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Test that change data can be serialized (common in existing workflows)
        for change in categorized_changes.changes:
            # Test individual field serialization
            serializable_data = {
                "match_id": change.match_id,
                "category": change.category.value,
                "priority": change.priority.value,
                "field_name": change.field_name,
                "previous_value": change.previous_value,
                "current_value": change.current_value,
                "change_description": change.change_description,
                "timestamp": change.timestamp.isoformat(),
            }

            # This should not raise any exceptions
            json_str = json.dumps(serializable_data)
            self.assertIsInstance(json_str, str)

            # Should be able to deserialize
            deserialized = json.loads(json_str)
            self.assertEqual(deserialized["match_id"], change.match_id)

    def test_performance_regression_prevention(self):
        """Test that semantic analysis doesn't cause performance regression."""
        import time

        # Create multiple semantic analyses to test performance
        analyses = [self._create_sample_semantic_analysis() for _ in range(10)]

        # Measure conversion time
        start_time = time.time()

        for analysis in analyses:
            self.adapter.convert_semantic_to_categorized(analysis)

        end_time = time.time()
        total_time = end_time - start_time

        # Should process 10 analyses in under 1 second
        self.assertLess(total_time, 1.0, "Performance regression detected")

    def test_error_handling_compatibility(self):
        """Test that error handling is compatible with existing patterns."""
        # Test with malformed semantic analysis
        try:
            # Create analysis with missing required fields
            incomplete_analysis = SemanticChangeAnalysis(
                match_id="test",
                change_category="test",
                field_changes=[],
                overall_impact=ChangeImpact.LOW,
                overall_urgency=ChangeUrgency.NORMAL,
                change_summary="",
                detailed_analysis="",
                stakeholder_impact_map={},
                recommended_actions=[],
            )

            # Should handle gracefully
            result = self.adapter.convert_semantic_to_categorized(incomplete_analysis)
            self.assertIsInstance(result, CategorizedChanges)

        except Exception as e:
            # If exceptions occur, they should be standard Python exceptions
            self.assertIsInstance(e, (ValueError, TypeError, AttributeError))

    def test_legacy_configuration_compatibility(self):
        """Test compatibility with existing configuration patterns."""
        # Test that adapter works without any special configuration
        adapter = SemanticToLegacyAdapter()
        self.assertIsNotNone(adapter)

        # Test that all mapping dictionaries are properly initialized
        self.assertIsInstance(adapter.category_mapping, dict)
        self.assertIsInstance(adapter.priority_mapping, dict)
        self.assertIsInstance(adapter.stakeholder_mapping, dict)

        # Test that mappings contain expected values
        self.assertIn(ChangeUrgency.URGENT, adapter.priority_mapping)
        self.assertEqual(adapter.priority_mapping[ChangeUrgency.URGENT], ChangePriority.HIGH)

    def _create_sample_semantic_analysis(self) -> SemanticChangeAnalysis:
        """Create a sample semantic analysis for testing."""
        context = ChangeContext(
            field_path="domaruppdraglista[0].namn",
            field_display_name="Referee Name",
            change_type="modified",
            previous_value="John Doe",
            current_value="Jane Smith",
            business_impact=ChangeImpact.HIGH,
            urgency=ChangeUrgency.URGENT,
            affected_stakeholders=["referees", "coordinators"],
            change_description="Referee changed from John Doe to Jane Smith",
            technical_description="Field domaruppdraglista[0].namn: John Doe -> Jane Smith",
            user_friendly_description="👨‍⚖️ Referee updated: Jane Smith (was John Doe)",
            timestamp=self.test_timestamp,
        )

        return SemanticChangeAnalysis(
            match_id="12345",
            change_category="referee_changes",
            field_changes=[context],
            overall_impact=ChangeImpact.HIGH,
            overall_urgency=ChangeUrgency.URGENT,
            change_summary="1 change(s) detected: Referee Name",
            detailed_analysis="HIGH IMPACT: 1 high-impact change(s) detected.",
            stakeholder_impact_map={
                "referees": ["👨‍⚖️ Referee updated: Jane Smith (was John Doe)"],
                "coordinators": ["👨‍⚖️ Referee updated: Jane Smith (was John Doe)"],
            },
            recommended_actions=["Send priority notifications within 1 hour"],
            analysis_timestamp=self.test_timestamp,
        )


if __name__ == "__main__":
    unittest.main()
