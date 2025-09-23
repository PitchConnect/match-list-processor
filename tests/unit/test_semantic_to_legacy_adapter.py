"""Unit tests for SemanticToLegacyAdapter."""

import unittest
from datetime import datetime

from src.core.change_categorization import (
    CategorizedChanges,
    ChangeCategory,
    ChangePriority,
    StakeholderType,
)
from src.notifications.adapters.semantic_to_legacy_adapter import SemanticToLegacyAdapter
from src.notifications.analysis.models.analysis_models import (
    ChangeContext,
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)


class TestSemanticToLegacyAdapter(unittest.TestCase):
    """Test cases for SemanticToLegacyAdapter."""

    def setUp(self):
        """Set up test fixtures."""
        self.adapter = SemanticToLegacyAdapter()
        self.test_timestamp = datetime(2024, 1, 15, 10, 30, 0)

    def test_initialization(self):
        """Test adapter initialization."""
        self.assertIsInstance(self.adapter, SemanticToLegacyAdapter)
        self.assertIsNotNone(self.adapter.category_mapping)
        self.assertIsNotNone(self.adapter.priority_mapping)
        self.assertIsNotNone(self.adapter.stakeholder_mapping)

    def test_convert_referee_changes(self):
        """Test conversion of referee changes."""
        # Create semantic analysis with referee change
        referee_context = ChangeContext(
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

        semantic_analysis = SemanticChangeAnalysis(
            match_id="12345",
            change_category="referee_changes",
            field_changes=[referee_context],
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

        # Convert to legacy format
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify result structure
        self.assertIsInstance(result, CategorizedChanges)
        self.assertEqual(result.total_changes, 1)
        self.assertEqual(result.high_priority_changes, 1)
        self.assertEqual(result.critical_changes, 0)

        # Verify change details
        self.assertEqual(len(result.changes), 1)
        change = result.changes[0]
        self.assertEqual(change.match_id, "12345")
        self.assertEqual(change.category, ChangeCategory.REFEREE_CHANGE)
        self.assertEqual(change.priority, ChangePriority.HIGH)
        self.assertEqual(change.field_name, "domaruppdraglista[0].namn")
        self.assertEqual(change.previous_value, "John Doe")
        self.assertEqual(change.current_value, "Jane Smith")

        # Verify stakeholders
        self.assertIn(StakeholderType.REFEREES, result.affected_stakeholder_types)
        self.assertIn(StakeholderType.COORDINATORS, result.affected_stakeholder_types)

        # Verify categories
        self.assertIn(ChangeCategory.REFEREE_CHANGE, result.change_categories)

    def test_convert_time_changes(self):
        """Test conversion of time changes."""
        time_context = ChangeContext(
            field_path="tid",
            field_display_name="Match Time",
            change_type="modified",
            previous_value="15:00",
            current_value="16:00",
            business_impact=ChangeImpact.HIGH,
            urgency=ChangeUrgency.IMMEDIATE,
            affected_stakeholders=["teams", "referees", "coordinators"],
            change_description="Match time changed from 15:00 to 16:00",
            technical_description="Field tid: 15:00 -> 16:00",
            user_friendly_description="🕐 Match time updated to 16:00",
            timestamp=self.test_timestamp,
        )

        semantic_analysis = SemanticChangeAnalysis(
            match_id="67890",
            change_category="time_changes",
            field_changes=[time_context],
            overall_impact=ChangeImpact.HIGH,
            overall_urgency=ChangeUrgency.IMMEDIATE,
            change_summary="1 change(s) detected: Match Time",
            detailed_analysis="CRITICAL: 1 critical change(s) requiring immediate attention.",
            stakeholder_impact_map={
                "teams": ["🕐 Match time updated to 16:00"],
                "referees": ["🕐 Match time updated to 16:00"],
                "coordinators": ["🕐 Match time updated to 16:00"],
            },
            recommended_actions=["Send immediate notifications to all affected stakeholders"],
            analysis_timestamp=self.test_timestamp,
        )

        # Convert to legacy format
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify result
        self.assertEqual(result.total_changes, 1)
        self.assertEqual(result.critical_changes, 1)
        self.assertEqual(result.high_priority_changes, 0)

        # Verify change details
        change = result.changes[0]
        self.assertEqual(change.category, ChangeCategory.TIME_CHANGE)
        self.assertEqual(change.priority, ChangePriority.CRITICAL)

        # Verify all stakeholder types are included
        self.assertIn(StakeholderType.TEAMS, result.affected_stakeholder_types)
        self.assertIn(StakeholderType.REFEREES, result.affected_stakeholder_types)
        self.assertIn(StakeholderType.COORDINATORS, result.affected_stakeholder_types)

    def test_convert_venue_changes(self):
        """Test conversion of venue changes."""
        venue_context = ChangeContext(
            field_path="anlaggningnamn",
            field_display_name="Venue",
            change_type="modified",
            previous_value="Stadium A",
            current_value="Stadium B",
            business_impact=ChangeImpact.MEDIUM,
            urgency=ChangeUrgency.NORMAL,
            affected_stakeholders=["teams", "coordinators"],
            change_description="Venue changed from Stadium A to Stadium B",
            technical_description="Field anlaggningnamn: Stadium A -> Stadium B",
            user_friendly_description="🏟️ Venue updated to Stadium B",
            timestamp=self.test_timestamp,
        )

        semantic_analysis = SemanticChangeAnalysis(
            match_id="11111",
            change_category="venue_changes",
            field_changes=[venue_context],
            overall_impact=ChangeImpact.MEDIUM,
            overall_urgency=ChangeUrgency.NORMAL,
            change_summary="1 change(s) detected: Venue",
            detailed_analysis="Standard changes detected with normal impact.",
            stakeholder_impact_map={
                "teams": ["🏟️ Venue updated to Stadium B"],
                "coordinators": ["🏟️ Venue updated to Stadium B"],
            },
            recommended_actions=["Update venue coordination systems"],
            analysis_timestamp=self.test_timestamp,
        )

        # Convert to legacy format
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify result
        change = result.changes[0]
        self.assertEqual(change.category, ChangeCategory.VENUE_CHANGE)
        self.assertEqual(change.priority, ChangePriority.MEDIUM)

    def test_preserve_stakeholder_mapping(self):
        """Test stakeholder mapping preservation."""
        # Test various stakeholder names
        test_cases = [
            (["referees"], {StakeholderType.REFEREES}),
            (["teams"], {StakeholderType.TEAMS}),
            (["coordinators"], {StakeholderType.COORDINATORS}),
            (["all"], {StakeholderType.ALL}),
            (["referees", "teams"], {StakeholderType.REFEREES, StakeholderType.TEAMS}),
            (
                ["unknown_stakeholder"],
                {StakeholderType.COORDINATORS},
            ),  # Default mapping
        ]

        for input_stakeholders, expected_types in test_cases:
            with self.subTest(stakeholders=input_stakeholders):
                result = self.adapter._map_stakeholders_to_legacy(input_stakeholders)
                self.assertEqual(result, expected_types)

    def test_urgency_to_priority_mapping(self):
        """Test urgency to priority mapping."""
        test_cases = [
            (ChangeUrgency.IMMEDIATE, ChangePriority.CRITICAL),
            (ChangeUrgency.URGENT, ChangePriority.HIGH),
            (ChangeUrgency.NORMAL, ChangePriority.MEDIUM),
            (ChangeUrgency.FUTURE, ChangePriority.LOW),
        ]

        for urgency, expected_priority in test_cases:
            with self.subTest(urgency=urgency):
                result = self.adapter._map_urgency_to_priority(urgency)
                self.assertEqual(result, expected_priority)

    def test_backward_compatibility(self):
        """Test backward compatibility with existing notification infrastructure."""
        # Create a complex semantic analysis
        contexts = [
            ChangeContext(
                field_path="domaruppdraglista[0].namn",
                field_display_name="Referee Name",
                change_type="modified",
                previous_value="John Doe",
                current_value="Jane Smith",
                business_impact=ChangeImpact.HIGH,
                urgency=ChangeUrgency.URGENT,
                affected_stakeholders=["referees"],
                change_description="Referee changed",
                technical_description="Technical description",
                user_friendly_description="User friendly description",
                timestamp=self.test_timestamp,
            ),
            ChangeContext(
                field_path="tid",
                field_display_name="Match Time",
                change_type="modified",
                previous_value="15:00",
                current_value="16:00",
                business_impact=ChangeImpact.CRITICAL,
                urgency=ChangeUrgency.IMMEDIATE,
                affected_stakeholders=["all"],
                change_description="Time changed",
                technical_description="Technical description",
                user_friendly_description="User friendly description",
                timestamp=self.test_timestamp,
            ),
        ]

        semantic_analysis = SemanticChangeAnalysis(
            match_id="test123",
            change_category="mixed_changes",
            field_changes=contexts,
            overall_impact=ChangeImpact.CRITICAL,
            overall_urgency=ChangeUrgency.IMMEDIATE,
            change_summary="2 changes detected",
            detailed_analysis="Mixed changes",
            stakeholder_impact_map={"referees": ["change1"], "all": ["change2"]},
            recommended_actions=["action1", "action2"],
            analysis_timestamp=self.test_timestamp,
        )

        # Convert and verify all required fields exist
        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        # Verify all required CategorizedChanges fields
        self.assertTrue(hasattr(result, "changes"))
        self.assertTrue(hasattr(result, "total_changes"))
        self.assertTrue(hasattr(result, "critical_changes"))
        self.assertTrue(hasattr(result, "high_priority_changes"))
        self.assertTrue(hasattr(result, "affected_stakeholder_types"))
        self.assertTrue(hasattr(result, "change_categories"))

        # Verify all changes have required fields
        for change in result.changes:
            self.assertTrue(hasattr(change, "match_id"))
            self.assertTrue(hasattr(change, "category"))
            self.assertTrue(hasattr(change, "priority"))
            self.assertTrue(hasattr(change, "affected_stakeholders"))
            self.assertTrue(hasattr(change, "field_name"))
            self.assertTrue(hasattr(change, "previous_value"))
            self.assertTrue(hasattr(change, "current_value"))
            self.assertTrue(hasattr(change, "change_description"))
            self.assertTrue(hasattr(change, "timestamp"))

    def test_serialize_complex_values(self):
        """Test serialization of complex values."""
        test_cases = [
            (None, ""),
            ("simple string", "simple string"),
            (123, "123"),
            ({"key": "value"}, '{"key": "value"}'),
            ([1, 2, 3], "[1, 2, 3]"),
            (datetime(2024, 1, 15, 10, 30), "2024-01-15T10:30:00"),
        ]

        for input_value, expected_output in test_cases:
            with self.subTest(value=input_value):
                result = self.adapter._serialize_value(input_value)
                self.assertEqual(result, expected_output)

    def test_empty_semantic_analysis(self):
        """Test handling of empty semantic analysis."""
        semantic_analysis = SemanticChangeAnalysis(
            match_id="empty123",
            change_category="no_changes",
            field_changes=[],
            overall_impact=ChangeImpact.INFORMATIONAL,
            overall_urgency=ChangeUrgency.NORMAL,
            change_summary="No changes detected",
            detailed_analysis="No changes were detected in this match.",
            stakeholder_impact_map={},
            recommended_actions=[],
            analysis_timestamp=self.test_timestamp,
        )

        result = self.adapter.convert_semantic_to_categorized(semantic_analysis)

        self.assertEqual(result.total_changes, 0)
        self.assertEqual(result.critical_changes, 0)
        self.assertEqual(result.high_priority_changes, 0)
        self.assertEqual(len(result.changes), 0)
        self.assertEqual(len(result.affected_stakeholder_types), 0)
        self.assertEqual(len(result.change_categories), 0)

    def test_field_path_category_mapping(self):
        """Test field path to category mapping logic."""
        test_cases = [
            ("domaruppdraglista[0].namn", ChangeCategory.REFEREE_CHANGE),
            ("tid", ChangeCategory.TIME_CHANGE),
            ("avsparkstid", ChangeCategory.TIME_CHANGE),
            ("speldatum", ChangeCategory.DATE_CHANGE),
            ("datum", ChangeCategory.DATE_CHANGE),
            ("anlaggningnamn", ChangeCategory.VENUE_CHANGE),
            ("venue", ChangeCategory.VENUE_CHANGE),
            ("hemmalag", ChangeCategory.TEAM_CHANGE),
            ("bortalag", ChangeCategory.TEAM_CHANGE),
            ("status", ChangeCategory.STATUS_CHANGE),
            ("installd", ChangeCategory.STATUS_CHANGE),
            ("unknown_field", ChangeCategory.UNKNOWN),
        ]

        for field_path, expected_category in test_cases:
            with self.subTest(field_path=field_path):
                context = ChangeContext(
                    field_path=field_path,
                    field_display_name="Test Field",
                    change_type="modified",
                    previous_value="old",
                    current_value="new",
                    business_impact=ChangeImpact.LOW,
                    urgency=ChangeUrgency.NORMAL,
                    affected_stakeholders=["coordinators"],
                    change_description="Test change",
                    technical_description="Technical description",
                    user_friendly_description="User friendly description",
                )

                result = self.adapter._map_semantic_to_legacy_category(context)
                self.assertEqual(result, expected_category)


if __name__ == "__main__":
    unittest.main()
