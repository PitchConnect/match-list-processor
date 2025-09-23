"""Specialized analyzer for time and date changes."""

from datetime import datetime
from typing import Any, Dict, List

from ..base_analyzer import FieldAnalyzer
from ..models.analysis_models import ChangeContext, ChangeImpact, ChangeUrgency


class TimeChangeAnalyzer(FieldAnalyzer):
    """Specialized analyzer for time and date changes."""

    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle time-related fields."""
        time_fields = ["datum", "tid", "time", "date", "speldatum", "spelstart"]
        return any(field in field_path.lower() for field in time_fields)

    def analyze_change(
        self,
        field_path: str,
        prev_value: Any,
        curr_value: Any,
        match_context: Dict[str, Any],
    ) -> List[ChangeContext]:
        """Analyze time/date changes."""
        changes = []

        if "datum" in field_path.lower() or "date" in field_path.lower():
            changes.append(
                self._analyze_date_change(field_path, prev_value, curr_value, match_context)
            )
        elif "tid" in field_path.lower() or "time" in field_path.lower():
            changes.append(
                self._analyze_time_change(field_path, prev_value, curr_value, match_context)
            )
        else:
            # Generic time-related change
            changes.append(
                self._analyze_generic_time_change(field_path, prev_value, curr_value, match_context)
            )

        return [change for change in changes if change is not None]

    def _analyze_date_change(
        self, field_path: str, prev_date: Any, curr_date: Any, match_context: Dict
    ) -> ChangeContext:
        """Analyze date changes."""
        home_team, away_team = self.extract_team_names(match_context)

        # Determine urgency based on new date
        urgency = self.assess_urgency(str(curr_date))

        # Determine impact based on how close the match is
        if urgency == ChangeUrgency.IMMEDIATE:
            impact = ChangeImpact.CRITICAL
        elif urgency == ChangeUrgency.URGENT:
            impact = ChangeImpact.HIGH
        else:
            impact = ChangeImpact.MEDIUM

        date_diff = self._calculate_date_difference(str(prev_date), str(curr_date))

        return ChangeContext(
            field_path=field_path,
            field_display_name="Match Date",
            change_type="modified",
            previous_value=prev_date,
            current_value=curr_date,
            business_impact=impact,
            urgency=urgency,
            affected_stakeholders=["teams", "referees", "coordinators", "venue"],
            change_description=f"Match date changed from {prev_date} to {curr_date} ({date_diff})",
            technical_description=f"Date field '{field_path}' changed from {prev_date} to {curr_date}",
            user_friendly_description=f"📅 Match date updated: {home_team} vs {away_team} has been {date_diff} to {self.format_date_friendly(str(curr_date))}",
        )

    def _analyze_time_change(
        self, field_path: str, prev_time: Any, curr_time: Any, match_context: Dict
    ) -> ChangeContext:
        """Analyze time changes."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        # Determine urgency based on match date
        urgency = self.assess_urgency(match_date)

        # Time changes are generally high impact if close to match date
        if urgency in [ChangeUrgency.IMMEDIATE, ChangeUrgency.URGENT]:
            impact = ChangeImpact.HIGH
        else:
            impact = ChangeImpact.MEDIUM

        time_diff = self._calculate_time_difference(str(prev_time), str(curr_time))

        return ChangeContext(
            field_path=field_path,
            field_display_name="Match Time",
            change_type="modified",
            previous_value=prev_time,
            current_value=curr_time,
            business_impact=impact,
            urgency=urgency,
            affected_stakeholders=["teams", "referees", "coordinators", "venue"],
            change_description=f"Match time changed from {prev_time} to {curr_time} ({time_diff})",
            technical_description=f"Time field '{field_path}' changed from {prev_time} to {curr_time}",
            user_friendly_description=f"🕐 Match time updated: {home_team} vs {away_team} on {self.format_date_friendly(match_date)} is now at {curr_time} (was {prev_time})",
        )

    def _analyze_generic_time_change(
        self, field_path: str, prev_value: Any, curr_value: Any, match_context: Dict
    ) -> ChangeContext:
        """Analyze generic time-related changes."""
        home_team, away_team = self.extract_team_names(match_context)
        match_date = self.extract_match_date(match_context)

        urgency = self.assess_urgency(match_date)
        impact = ChangeImpact.MEDIUM

        return ChangeContext(
            field_path=field_path,
            field_display_name="Schedule Information",
            change_type="modified",
            previous_value=prev_value,
            current_value=curr_value,
            business_impact=impact,
            urgency=urgency,
            affected_stakeholders=["teams", "referees", "coordinators"],
            change_description=f"Schedule information updated: {field_path} changed from {prev_value} to {curr_value}",
            technical_description=f"Time-related field '{field_path}' changed from {prev_value} to {curr_value}",
            user_friendly_description=f"📋 Schedule update for {home_team} vs {away_team}: {field_path} updated to {curr_value}",
        )

    def _calculate_date_difference(self, prev_date: str, curr_date: str) -> str:
        """Calculate and describe date difference."""
        try:
            prev_dt = datetime.strptime(prev_date, "%Y-%m-%d")
            curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
            diff_days = (curr_dt - prev_dt).days

            if diff_days > 0:
                return f"moved forward by {diff_days} day(s)"
            elif diff_days < 0:
                return f"moved back by {abs(diff_days)} day(s)"
            else:
                return "updated (same date)"
        except (ValueError, TypeError):
            return "updated"

    def _calculate_time_difference(self, prev_time: str, curr_time: str) -> str:
        """Calculate and describe time difference."""
        try:
            # Try to parse as HH:MM format
            prev_parts = prev_time.split(":")
            curr_parts = curr_time.split(":")

            if len(prev_parts) >= 2 and len(curr_parts) >= 2:
                prev_minutes = int(prev_parts[0]) * 60 + int(prev_parts[1])
                curr_minutes = int(curr_parts[0]) * 60 + int(curr_parts[1])
                diff_minutes = curr_minutes - prev_minutes

                if diff_minutes > 0:
                    hours, minutes = divmod(diff_minutes, 60)
                    if hours > 0:
                        return f"moved later by {hours}h {minutes}m"
                    else:
                        return f"moved later by {minutes} minutes"
                elif diff_minutes < 0:
                    hours, minutes = divmod(abs(diff_minutes), 60)
                    if hours > 0:
                        return f"moved earlier by {hours}h {minutes}m"
                    else:
                        return f"moved earlier by {minutes} minutes"
                else:
                    return "updated (same time)"
            else:
                return "updated"
        except (ValueError, TypeError):
            return "updated"
