"""Specialized analyzer for venue changes."""

from typing import Any, Dict, List

from ..base_analyzer import FieldAnalyzer
from ..models.analysis_models import ChangeContext, ChangeImpact, ChangeUrgency


class VenueChangeAnalyzer(FieldAnalyzer):
    """Specialized analyzer for venue changes."""

    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle venue-related fields."""
        venue_fields = ["venue", "arena", "plan", "plats", "location", "address"]
        return any(field in field_path.lower() for field in venue_fields)

    def analyze_change(
        self, field_path: str, prev_value: Any, curr_value: Any, match_context: Dict[str, Any]
    ) -> List[ChangeContext]:
        """Analyze venue changes."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        # Determine urgency based on match timing
        urgency = self.assess_urgency(match_date)

        # Venue changes are high impact, especially close to match date
        if urgency == ChangeUrgency.IMMEDIATE:
            impact = ChangeImpact.CRITICAL
        elif urgency == ChangeUrgency.URGENT:
            impact = ChangeImpact.HIGH
        else:
            impact = ChangeImpact.MEDIUM

        change_description = self._describe_venue_change(field_path, prev_value, curr_value)

        return [
            ChangeContext(
                field_path=field_path,
                field_display_name="Venue Information",
                change_type="modified",
                previous_value=prev_value,
                current_value=curr_value,
                business_impact=impact,
                urgency=urgency,
                affected_stakeholders=["teams", "referees", "coordinators", "venue", "spectators"],
                change_description=change_description,
                technical_description=f"Venue field '{field_path}' changed from '{prev_value}' to '{curr_value}'",
                user_friendly_description=f"📍 Venue update for {home_team} vs {away_team} on {self.format_date_friendly(match_date)}: {change_description}",
            )
        ]

    def _describe_venue_change(self, field_path: str, prev_value: Any, curr_value: Any) -> str:
        """Describe the venue change in user-friendly terms."""
        if "plan" in field_path.lower():
            return f"Playing field changed from '{prev_value}' to '{curr_value}'"
        elif "arena" in field_path.lower() or "venue" in field_path.lower():
            return f"Venue changed from '{prev_value}' to '{curr_value}'"
        elif "address" in field_path.lower() or "plats" in field_path.lower():
            return f"Venue address updated from '{prev_value}' to '{curr_value}'"
        else:
            return f"Venue information updated: {field_path} changed to '{curr_value}'"
