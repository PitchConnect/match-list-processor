"""Main orchestrator for semantic change analysis."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .analyzers import (
    RefereeAssignmentAnalyzer,
    StatusChangeAnalyzer,
    TeamChangeAnalyzer,
    TimeChangeAnalyzer,
    VenueChangeAnalyzer,
)
from .base_analyzer import FieldAnalyzer
from .models.analysis_models import (
    ChangeContext,
    ChangeImpact,
    ChangeUrgency,
    SemanticChangeAnalysis,
)


class SemanticChangeAnalyzer:
    """Main orchestrator for semantic change analysis."""

    def __init__(self) -> None:
        """Initialize the semantic analyzer with field analyzers."""
        self.field_analyzers: List[FieldAnalyzer] = [
            RefereeAssignmentAnalyzer(),
            TimeChangeAnalyzer(),
            VenueChangeAnalyzer(),
            TeamChangeAnalyzer(),
            StatusChangeAnalyzer(),
        ]

    def analyze_match_changes(
        self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]
    ) -> SemanticChangeAnalysis:
        """Perform comprehensive semantic analysis of match changes.

        Args:
            prev_match: Previous match data
            curr_match: Current match data

        Returns:
            SemanticChangeAnalysis with detailed change information
        """
        all_changes = []

        # Detect all field changes
        field_changes = self._detect_field_changes(prev_match, curr_match)

        # Analyze each change with appropriate analyzer
        for field_path, prev_value, curr_value in field_changes:
            analyzer = self._find_analyzer(field_path)
            if analyzer:
                change_contexts = analyzer.analyze_change(
                    field_path, prev_value, curr_value, curr_match
                )
                all_changes.extend(change_contexts)
            else:
                # Create generic change context for unhandled fields
                generic_change = self._create_generic_change_context(
                    field_path, prev_value, curr_value, curr_match
                )
                all_changes.append(generic_change)

        # Perform correlation analysis
        correlated_changes = self._correlate_changes(all_changes)

        # Generate overall analysis
        match_id = curr_match.get("matchid", "unknown")
        return self._generate_semantic_analysis(match_id, all_changes, correlated_changes)

    def _detect_field_changes(
        self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]
    ) -> List[Tuple[str, Any, Any]]:
        """Detect all field-level changes between matches.

        Args:
            prev_match: Previous match data
            curr_match: Current match data

        Returns:
            List of tuples (field_path, prev_value, curr_value)
        """
        changes = []

        def compare_nested(prev_obj: Any, curr_obj: Any, path: str = "") -> None:
            """Recursively compare nested objects."""
            if isinstance(prev_obj, dict) and isinstance(curr_obj, dict):
                all_keys = set(prev_obj.keys()) | set(curr_obj.keys())
                for key in all_keys:
                    new_path = f"{path}.{key}" if path else key
                    prev_val = prev_obj.get(key)
                    curr_val = curr_obj.get(key)

                    if prev_val != curr_val:
                        if isinstance(prev_val, (dict, list)) and isinstance(
                            curr_val, (dict, list)
                        ):
                            compare_nested(prev_val, curr_val, new_path)
                        else:
                            changes.append((new_path, prev_val, curr_val))
            elif isinstance(prev_obj, list) and isinstance(curr_obj, list):
                max_len = max(len(prev_obj), len(curr_obj))
                for i in range(max_len):
                    new_path = f"{path}[{i}]"
                    prev_val = prev_obj[i] if i < len(prev_obj) else None
                    curr_val = curr_obj[i] if i < len(curr_obj) else None

                    if prev_val != curr_val:
                        if isinstance(prev_val, (dict, list)) and isinstance(
                            curr_val, (dict, list)
                        ):
                            compare_nested(prev_val, curr_val, new_path)
                        else:
                            changes.append((new_path, prev_val, curr_val))
            else:
                if prev_obj != curr_obj:
                    changes.append((path, prev_obj, curr_obj))

        compare_nested(prev_match, curr_match)
        return changes

    def _find_analyzer(self, field_path: str) -> Optional[FieldAnalyzer]:
        """Find appropriate analyzer for field.

        Args:
            field_path: Path to the field that changed

        Returns:
            FieldAnalyzer that can handle the field, or None
        """
        for analyzer in self.field_analyzers:
            if analyzer.can_analyze(field_path):
                return analyzer
        return None

    def _correlate_changes(self, changes: List[ChangeContext]) -> Dict[str, List[ChangeContext]]:
        """Detect correlated changes.

        Args:
            changes: List of change contexts

        Returns:
            Dictionary mapping correlation IDs to lists of related changes
        """
        correlations = {}

        # Group changes by type for correlation analysis
        referee_changes = [c for c in changes if "referee" in c.field_path.lower()]
        time_changes = [
            c
            for c in changes
            if any(t in c.field_path.lower() for t in ["datum", "tid", "time", "date"])
        ]
        venue_changes = [
            c for c in changes if any(v in c.field_path.lower() for v in ["venue", "arena", "plan"])
        ]

        # Create correlations for batched changes
        if len(referee_changes) > 1:
            correlation_id = f"referee_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            correlations[correlation_id] = referee_changes

        if len(time_changes) > 1:
            correlation_id = f"time_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            correlations[correlation_id] = time_changes

        if len(venue_changes) > 1:
            correlation_id = f"venue_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            correlations[correlation_id] = venue_changes

        return correlations

    def _generate_semantic_analysis(
        self,
        match_id: str,
        changes: List[ChangeContext],
        correlations: Dict[str, List[ChangeContext]],
    ) -> SemanticChangeAnalysis:
        """Generate comprehensive semantic analysis.

        Args:
            match_id: ID of the match being analyzed
            changes: List of all change contexts
            correlations: Dictionary of correlated changes

        Returns:
            Complete semantic analysis
        """
        if not changes:
            return SemanticChangeAnalysis(
                match_id=match_id,
                change_category="no_changes",
                field_changes=[],
                overall_impact=ChangeImpact.INFORMATIONAL,
                overall_urgency=ChangeUrgency.NORMAL,
                change_summary="No changes detected",
                detailed_analysis="No changes were detected in this match.",
                stakeholder_impact_map={},
                recommended_actions=[],
            )

        # Determine overall impact and urgency
        overall_impact = max(
            changes, key=lambda c: list(ChangeImpact).index(c.business_impact)
        ).business_impact
        overall_urgency = max(changes, key=lambda c: list(ChangeUrgency).index(c.urgency)).urgency

        # Generate stakeholder impact map
        stakeholder_map: Dict[str, List[str]] = {}
        for change in changes:
            for stakeholder in change.affected_stakeholders:
                if stakeholder not in stakeholder_map:
                    stakeholder_map[stakeholder] = []
                stakeholder_map[stakeholder].append(change.user_friendly_description)

        # Generate change summary
        change_types = list(set(c.field_display_name for c in changes))
        change_summary = f"{len(changes)} change(s) detected: {', '.join(change_types)}"

        # Generate detailed analysis
        detailed_analysis = self._generate_detailed_analysis(changes, correlations)

        # Generate recommended actions
        recommended_actions = self._generate_recommended_actions(changes, overall_urgency)

        return SemanticChangeAnalysis(
            match_id=match_id,
            change_category=self._determine_primary_category(changes),
            field_changes=changes,
            overall_impact=overall_impact,
            overall_urgency=overall_urgency,
            change_summary=change_summary,
            detailed_analysis=detailed_analysis,
            stakeholder_impact_map=stakeholder_map,
            recommended_actions=recommended_actions,
        )

    def _determine_primary_category(self, changes: List[ChangeContext]) -> str:
        """Determine primary change category.

        Args:
            changes: List of change contexts

        Returns:
            Primary category string
        """
        if any(
            "domaruppdrag" in c.field_path.lower() or "referee" in c.field_path.lower()
            for c in changes
        ):
            return "referee_changes"
        elif any(
            any(t in c.field_path.lower() for t in ["datum", "tid", "time", "date"])
            for c in changes
        ):
            return "time_changes"
        elif any(
            any(v in c.field_path.lower() for v in ["venue", "arena", "plan"]) for c in changes
        ):
            return "venue_changes"
        elif any("status" in c.field_path.lower() for c in changes):
            return "status_changes"
        elif any(
            any(t in c.field_path.lower() for t in ["hemmalag", "bortalag", "team", "lag"])
            for c in changes
        ):
            return "team_changes"
        else:
            return "general_changes"

    def _generate_detailed_analysis(
        self, changes: List[ChangeContext], correlations: Dict[str, List[ChangeContext]]
    ) -> str:
        """Generate detailed analysis text.

        Args:
            changes: List of change contexts
            correlations: Dictionary of correlated changes

        Returns:
            Detailed analysis string
        """
        analysis_parts = []

        # Group changes by impact level
        critical_changes = [c for c in changes if c.business_impact == ChangeImpact.CRITICAL]
        high_changes = [c for c in changes if c.business_impact == ChangeImpact.HIGH]

        if critical_changes:
            analysis_parts.append(
                f"CRITICAL: {len(critical_changes)} critical change(s) requiring immediate attention."
            )

        if high_changes:
            analysis_parts.append(
                f"HIGH IMPACT: {len(high_changes)} high-impact change(s) detected."
            )

        # Add correlation information
        if correlations:
            analysis_parts.append(
                f"CORRELATED: {len(correlations)} group(s) of related changes detected."
            )

        return (
            " ".join(analysis_parts)
            if analysis_parts
            else "Standard changes detected with normal impact."
        )

    def _generate_recommended_actions(
        self, changes: List[ChangeContext], urgency: ChangeUrgency
    ) -> List[str]:
        """Generate recommended actions based on changes.

        Args:
            changes: List of change contexts
            urgency: Overall urgency level

        Returns:
            List of recommended action strings
        """
        actions = []

        if urgency == ChangeUrgency.IMMEDIATE:
            actions.append("Send immediate notifications to all affected stakeholders")
            actions.append("Verify change accuracy with match coordinator")
        elif urgency == ChangeUrgency.URGENT:
            actions.append("Send priority notifications within 1 hour")
            actions.append("Confirm receipt with key stakeholders")

        # Add specific actions based on change types
        referee_changes = [c for c in changes if "referee" in c.field_path.lower()]
        if referee_changes:
            actions.append("Update referee assignment systems")
            actions.append("Send calendar updates to affected referees")

        time_changes = [
            c
            for c in changes
            if any(t in c.field_path.lower() for t in ["datum", "tid", "time", "date"])
        ]
        if time_changes:
            actions.append("Update all calendar systems")
            actions.append("Notify teams and venue coordinators")

        venue_changes = [
            c for c in changes if any(v in c.field_path.lower() for v in ["venue", "arena", "plan"])
        ]
        if venue_changes:
            actions.append("Update venue coordination systems")
            actions.append("Notify affected parties of location changes")

        return actions

    def _create_generic_change_context(
        self,
        field_path: str,
        prev_value: Any,
        curr_value: Any,
        match_context: Dict[str, Any],
    ) -> ChangeContext:
        """Create generic change context for unhandled fields.

        Args:
            field_path: Path to the field that changed
            prev_value: Previous value
            curr_value: Current value
            match_context: Match context information

        Returns:
            Generic ChangeContext
        """
        return ChangeContext(
            field_path=field_path,
            field_display_name=field_path.replace(".", " ").title(),
            change_type="modified",
            previous_value=prev_value,
            current_value=curr_value,
            business_impact=ChangeImpact.LOW,
            urgency=ChangeUrgency.NORMAL,
            affected_stakeholders=["coordinators"],
            change_description=f"Field '{field_path}' changed from '{prev_value}' to '{curr_value}'",
            technical_description=f"Generic field change: {field_path}",
            user_friendly_description=f"📝 Field update: {field_path} has been updated",
        )
