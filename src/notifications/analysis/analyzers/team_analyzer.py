"""Specialized analyzer for team changes."""

from typing import Any, Dict, List

from ..base_analyzer import FieldAnalyzer
from ..models.analysis_models import ChangeContext, ChangeImpact, ChangeUrgency


class TeamChangeAnalyzer(FieldAnalyzer):
    """Specialized analyzer for team-related changes."""

    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle team-related fields."""
        team_fields = ["hemmalag", "bortalag", "home_team", "away_team", "team", "lag"]
        return any(field in field_path.lower() for field in team_fields)

    def analyze_change(
        self,
        field_path: str,
        prev_value: Any,
        curr_value: Any,
        match_context: Dict[str, Any],
    ) -> List[ChangeContext]:
        """Analyze team changes."""
        match_date = self.extract_match_date(match_context)

        # Determine urgency based on match timing
        urgency = self.assess_urgency(match_date)

        # Team changes are always high impact
        impact = ChangeImpact.HIGH
        if urgency == ChangeUrgency.IMMEDIATE:
            impact = ChangeImpact.CRITICAL

        team_type = self._determine_team_type(field_path)
        change_description = f"{team_type} team changed from '{prev_value}' to '{curr_value}'"

        return [
            ChangeContext(
                field_path=field_path,
                field_display_name=f"{team_type} Team",
                change_type="modified",
                previous_value=prev_value,
                current_value=curr_value,
                business_impact=impact,
                urgency=urgency,
                affected_stakeholders=[
                    "teams",
                    "referees",
                    "coordinators",
                    "spectators",
                ],
                change_description=change_description,
                technical_description=f"Team field '{field_path}' changed from '{prev_value}' to '{curr_value}'",
                user_friendly_description=f"⚽ Team update: {change_description} for match on {self.format_date_friendly(match_date)}",
            )
        ]

    def _determine_team_type(self, field_path: str) -> str:
        """Determine if this is home or away team."""
        if "hemma" in field_path.lower() or "home" in field_path.lower():
            return "Home"
        elif "borta" in field_path.lower() or "away" in field_path.lower():
            return "Away"
        else:
            return "Team"
