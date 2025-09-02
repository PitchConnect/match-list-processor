"""Adapter to convert semantic analysis to legacy categorized changes format."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Set

from ...core.change_categorization import (
    CategorizedChanges,
    ChangeCategory,
    ChangePriority,
    MatchChangeDetail,
    StakeholderType,
)
from ..analysis.models.analysis_models import ChangeContext, ChangeUrgency, SemanticChangeAnalysis

logger = logging.getLogger(__name__)


class SemanticToLegacyAdapter:
    """
    Adapter to convert rich semantic analysis to legacy categorized changes format.

    This adapter bridges the gap between the new semantic analysis system and the
    existing notification infrastructure, preserving business intelligence while
    maintaining backward compatibility.
    """

    def __init__(self) -> None:
        """Initialize the semantic to legacy adapter."""
        self.category_mapping = self._build_category_mapping()
        self.priority_mapping = self._build_priority_mapping()
        self.stakeholder_mapping = self._build_stakeholder_mapping()

    def convert_semantic_to_categorized(
        self, semantic_analysis: SemanticChangeAnalysis
    ) -> CategorizedChanges:
        """
        Convert semantic analysis to legacy categorized changes format.

        Args:
            semantic_analysis: Rich semantic analysis object

        Returns:
            CategorizedChanges object compatible with existing notification system
        """
        logger.debug(f"Converting semantic analysis for match {semantic_analysis.match_id}")

        # Convert semantic change contexts to legacy change details
        legacy_changes = self._convert_change_contexts_to_changes(
            semantic_analysis.field_changes, semantic_analysis.match_id
        )

        # Calculate aggregated metrics
        total_changes = len(legacy_changes)
        critical_changes = sum(
            1 for change in legacy_changes if change.priority == ChangePriority.CRITICAL
        )
        high_priority_changes = sum(
            1 for change in legacy_changes if change.priority == ChangePriority.HIGH
        )

        # Map stakeholders to legacy format
        affected_stakeholder_types = self._map_stakeholders_to_legacy(
            list(semantic_analysis.stakeholder_impact_map.keys())
        )

        # Determine change categories from semantic analysis
        change_categories = self._extract_change_categories(semantic_analysis.field_changes)

        # Create categorized changes with preserved semantic metadata
        categorized_changes = CategorizedChanges(
            changes=legacy_changes,
            total_changes=total_changes,
            critical_changes=critical_changes,
            high_priority_changes=high_priority_changes,
            affected_stakeholder_types=affected_stakeholder_types,
            change_categories=change_categories,
        )

        # Preserve semantic analysis metadata for enhanced notifications
        self._preserve_semantic_metadata(categorized_changes, semantic_analysis)

        logger.info(
            f"Converted semantic analysis to {total_changes} legacy changes "
            f"({critical_changes} critical, {high_priority_changes} high priority)"
        )

        return categorized_changes

    def _convert_change_contexts_to_changes(
        self, field_changes: List[ChangeContext], match_id: str
    ) -> List[MatchChangeDetail]:
        """
        Convert semantic change contexts to legacy change objects.

        Args:
            field_changes: List of semantic change contexts
            match_id: Match identifier

        Returns:
            List of legacy MatchChangeDetail objects
        """
        legacy_changes = []

        for context in field_changes:
            # Map semantic category to legacy category
            legacy_category = self._map_semantic_to_legacy_category(context)

            # Map urgency to priority
            legacy_priority = self._map_urgency_to_priority(context.urgency)

            # Map stakeholders to legacy format
            legacy_stakeholders = self._map_stakeholders_to_legacy(context.affected_stakeholders)

            # Create legacy change detail with preserved semantic context
            legacy_change = MatchChangeDetail(
                match_id=match_id,
                match_nr=None,  # Not available in semantic context
                category=legacy_category,
                priority=legacy_priority,
                affected_stakeholders=list(legacy_stakeholders),
                field_name=context.field_path,
                previous_value=self._serialize_value(context.previous_value),
                current_value=self._serialize_value(context.current_value),
                change_description=context.change_description,
                timestamp=context.timestamp or datetime.utcnow(),
            )

            # Preserve semantic context in metadata (if supported)
            if hasattr(legacy_change, "metadata"):
                legacy_change.metadata = {
                    "semantic_context": {
                        "display_name": context.field_display_name,
                        "business_impact": context.business_impact.value,
                        "urgency": context.urgency.value,
                        "technical_description": context.technical_description,
                        "user_friendly_description": context.user_friendly_description,
                        "related_changes": context.related_changes,
                    }
                }

            legacy_changes.append(legacy_change)

        return legacy_changes

    def _map_semantic_to_legacy_category(self, context: ChangeContext) -> ChangeCategory:
        """
        Map semantic change context to legacy category.

        Args:
            context: Semantic change context

        Returns:
            Legacy ChangeCategory enum value
        """
        field_path = context.field_path.lower()

        # Field-based category mapping
        if any(
            referee_field in field_path for referee_field in ["domaruppdrag", "referee", "domare"]
        ):
            return ChangeCategory.REFEREE_CHANGE
        elif any(time_field in field_path for time_field in ["tid", "time", "avsparkstid"]):
            return ChangeCategory.TIME_CHANGE
        elif any(date_field in field_path for date_field in ["datum", "date", "speldatum"]):
            return ChangeCategory.DATE_CHANGE
        elif any(venue_field in field_path for venue_field in ["anlaggning", "venue", "plan"]):
            return ChangeCategory.VENUE_CHANGE
        elif any(
            team_field in field_path for team_field in ["lag", "team", "hemmalag", "bortalag"]
        ):
            return ChangeCategory.TEAM_CHANGE
        elif any(status_field in field_path for status_field in ["status", "installd", "avbruten"]):
            return ChangeCategory.STATUS_CHANGE
        else:
            return ChangeCategory.UNKNOWN

    def _map_urgency_to_priority(self, urgency: ChangeUrgency) -> ChangePriority:
        """
        Map semantic urgency to legacy priority.

        Args:
            urgency: Semantic urgency level

        Returns:
            Legacy ChangePriority enum value
        """
        return self.priority_mapping.get(urgency, ChangePriority.MEDIUM)

    def _map_stakeholders_to_legacy(self, stakeholders: List[str]) -> Set[StakeholderType]:
        """
        Map semantic stakeholder names to legacy stakeholder types.

        Args:
            stakeholders: List of semantic stakeholder names

        Returns:
            Set of legacy StakeholderType enum values
        """
        legacy_stakeholders = set()

        for stakeholder in stakeholders:
            stakeholder_lower = stakeholder.lower()

            if stakeholder_lower in ["referees", "referee", "domare"]:
                legacy_stakeholders.add(StakeholderType.REFEREES)
            elif stakeholder_lower in ["coordinators", "coordinator", "koordinator"]:
                legacy_stakeholders.add(StakeholderType.COORDINATORS)
            elif stakeholder_lower in ["teams", "team", "lag"]:
                legacy_stakeholders.add(StakeholderType.TEAMS)
            elif stakeholder_lower in ["all", "alla"]:
                legacy_stakeholders.add(StakeholderType.ALL)
            else:
                # Default to coordinators for unknown stakeholders
                legacy_stakeholders.add(StakeholderType.COORDINATORS)

        return legacy_stakeholders

    def _extract_change_categories(self, field_changes: List[ChangeContext]) -> Set[ChangeCategory]:
        """
        Extract change categories from semantic field changes.

        Args:
            field_changes: List of semantic change contexts

        Returns:
            Set of legacy ChangeCategory enum values
        """
        categories = set()

        for context in field_changes:
            category = self._map_semantic_to_legacy_category(context)
            categories.add(category)

        return categories

    def _preserve_semantic_metadata(
        self, categorized_changes: CategorizedChanges, semantic_analysis: SemanticChangeAnalysis
    ) -> None:
        """
        Preserve semantic analysis metadata in the legacy format.

        Args:
            categorized_changes: Legacy categorized changes object
            semantic_analysis: Original semantic analysis
        """
        # Add semantic metadata as attributes (if supported by the class)
        if hasattr(categorized_changes, "semantic_metadata"):
            categorized_changes.semantic_metadata = {
                "analysis_enabled": True,
                "overall_impact": semantic_analysis.overall_impact.value,
                "overall_urgency": semantic_analysis.overall_urgency.value,
                "change_summary": semantic_analysis.change_summary,
                "detailed_analysis": semantic_analysis.detailed_analysis,
                "stakeholder_impact_map": semantic_analysis.stakeholder_impact_map,
                "recommended_actions": semantic_analysis.recommended_actions,
                "correlation_id": semantic_analysis.correlation_id,
                "analysis_timestamp": semantic_analysis.analysis_timestamp.isoformat(),
            }

    def _serialize_value(self, value: Any) -> str:
        """
        Serialize complex values for legacy format compatibility.

        Args:
            value: Value to serialize

        Returns:
            String representation of the value
        """
        if value is None:
            return ""
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return str(value)

    def _build_category_mapping(self) -> Dict[str, ChangeCategory]:
        """Build mapping from semantic categories to legacy categories."""
        return {
            "referee_changes": ChangeCategory.REFEREE_CHANGE,
            "time_changes": ChangeCategory.TIME_CHANGE,
            "date_changes": ChangeCategory.DATE_CHANGE,
            "venue_changes": ChangeCategory.VENUE_CHANGE,
            "team_changes": ChangeCategory.TEAM_CHANGE,
            "status_changes": ChangeCategory.STATUS_CHANGE,
            "general_changes": ChangeCategory.UNKNOWN,
            "no_changes": ChangeCategory.UNKNOWN,
        }

    def _build_priority_mapping(self) -> Dict[ChangeUrgency, ChangePriority]:
        """Build mapping from semantic urgency to legacy priority."""
        return {
            ChangeUrgency.IMMEDIATE: ChangePriority.CRITICAL,
            ChangeUrgency.URGENT: ChangePriority.HIGH,
            ChangeUrgency.NORMAL: ChangePriority.MEDIUM,
            ChangeUrgency.FUTURE: ChangePriority.LOW,
        }

    def _build_stakeholder_mapping(self) -> Dict[str, StakeholderType]:
        """Build mapping from semantic stakeholder names to legacy types."""
        return {
            "referees": StakeholderType.REFEREES,
            "referee": StakeholderType.REFEREES,
            "domare": StakeholderType.REFEREES,
            "coordinators": StakeholderType.COORDINATORS,
            "coordinator": StakeholderType.COORDINATORS,
            "koordinator": StakeholderType.COORDINATORS,
            "teams": StakeholderType.TEAMS,
            "team": StakeholderType.TEAMS,
            "lag": StakeholderType.TEAMS,
            "all": StakeholderType.ALL,
            "alla": StakeholderType.ALL,
        }
