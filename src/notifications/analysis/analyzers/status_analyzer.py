"""Specialized analyzer for match status changes."""

from typing import Any, Dict, List

from ..base_analyzer import FieldAnalyzer
from ..models.analysis_models import ChangeContext, ChangeImpact


class StatusChangeAnalyzer(FieldAnalyzer):
    """Specialized analyzer for match status changes."""

    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle status-related fields."""
        status_fields = ["status", "state", "tillstand", "matchstatus"]
        return any(field in field_path.lower() for field in status_fields)

    def analyze_change(
        self,
        field_path: str,
        prev_value: Any,
        curr_value: Any,
        match_context: Dict[str, Any],
    ) -> List[ChangeContext]:
        """Analyze status changes."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        # Determine urgency based on match timing
        urgency = self.assess_urgency(match_date)

        # Determine impact based on status change type
        impact = self._assess_status_impact(str(prev_value), str(curr_value))

        status_description = self._describe_status_change(str(prev_value), str(curr_value))

        return [
            ChangeContext(
                field_path=field_path,
                field_display_name="Match Status",
                change_type="modified",
                previous_value=prev_value,
                current_value=curr_value,
                business_impact=impact,
                urgency=urgency,
                affected_stakeholders=self._get_affected_stakeholders(str(curr_value)),
                change_description=f"Match status changed: {status_description}",
                technical_description=f"Status field '{field_path}' changed from '{prev_value}' to '{curr_value}'",
                user_friendly_description=f"🚨 Status update for {home_team} vs {away_team} on {self.format_date_friendly(match_date)}: {status_description}",
            )
        ]

    def _assess_status_impact(self, prev_status: str, curr_status: str) -> ChangeImpact:
        """Assess the impact of status change."""
        # Critical status changes
        critical_statuses = ["cancelled", "postponed", "abandoned", "suspended"]
        if any(status in curr_status.lower() for status in critical_statuses):
            return ChangeImpact.CRITICAL

        # High impact status changes
        high_impact_statuses = ["delayed", "rescheduled", "moved"]
        if any(status in curr_status.lower() for status in high_impact_statuses):
            return ChangeImpact.HIGH

        # Medium impact for other status changes
        return ChangeImpact.MEDIUM

    def _describe_status_change(self, prev_status: str, curr_status: str) -> str:
        """Describe the status change in user-friendly terms."""
        curr_lower = curr_status.lower()

        if "cancelled" in curr_lower:
            return f"Match has been cancelled (was: {prev_status})"
        elif "postponed" in curr_lower:
            return f"Match has been postponed (was: {prev_status})"
        elif "delayed" in curr_lower:
            return f"Match has been delayed (was: {prev_status})"
        elif "rescheduled" in curr_lower:
            return f"Match has been rescheduled (was: {prev_status})"
        elif "confirmed" in curr_lower:
            return f"Match has been confirmed (was: {prev_status})"
        elif "scheduled" in curr_lower:
            return f"Match is now scheduled (was: {prev_status})"
        else:
            return f"Status updated from '{prev_status}' to '{curr_status}'"

    def _get_affected_stakeholders(self, curr_status: str) -> List[str]:
        """Get stakeholders affected by status change."""
        base_stakeholders = ["teams", "referees", "coordinators"]

        curr_lower = curr_status.lower()

        # Add spectators for major status changes
        if any(status in curr_lower for status in ["cancelled", "postponed", "rescheduled"]):
            base_stakeholders.append("spectators")

        # Add venue for venue-related status changes
        if any(status in curr_lower for status in ["moved", "rescheduled", "venue"]):
            base_stakeholders.append("venue")

        return base_stakeholders
