"""Base class for field-specific analyzers."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models.analysis_models import ChangeContext, ChangeUrgency


class FieldAnalyzer(ABC):
    """Base class for field-specific analyzers."""

    @abstractmethod
    def can_analyze(self, field_path: str) -> bool:
        """Check if this analyzer can handle the given field.

        Args:
            field_path: The path to the field being analyzed

        Returns:
            True if this analyzer can handle the field
        """
        pass

    @abstractmethod
    def analyze_change(
        self,
        field_path: str,
        prev_value: Any,
        curr_value: Any,
        match_context: Dict[str, Any],
    ) -> List[ChangeContext]:
        """Analyze a specific field change.

        Args:
            field_path: The path to the field that changed
            prev_value: Previous value of the field
            curr_value: Current value of the field
            match_context: Context information about the match

        Returns:
            List of ChangeContext objects describing the changes
        """
        pass

    def assess_urgency(self, match_date: str, current_date: Optional[str] = None) -> ChangeUrgency:
        """Assess urgency based on match timing.

        Args:
            match_date: Date of the match (YYYY-MM-DD format)
            current_date: Current date (defaults to today)

        Returns:
            ChangeUrgency level based on timing
        """
        if current_date is None:
            current_date = datetime.now().strftime("%Y-%m-%d")

        try:
            match_dt = datetime.strptime(match_date, "%Y-%m-%d")
            current_dt = datetime.strptime(current_date, "%Y-%m-%d")
            days_until_match = (match_dt - current_dt).days

            if days_until_match <= 0:
                return ChangeUrgency.IMMEDIATE
            elif days_until_match <= 1:
                return ChangeUrgency.URGENT
            elif days_until_match <= 7:
                return ChangeUrgency.NORMAL
            else:
                return ChangeUrgency.FUTURE
        except (ValueError, TypeError):
            return ChangeUrgency.NORMAL

    def generate_user_friendly_description(self, change_context: ChangeContext) -> str:
        """Generate human-readable change description.

        Args:
            change_context: The change context to describe

        Returns:
            User-friendly description string
        """
        # Base implementation - can be overridden
        return change_context.change_description

    def extract_match_date(self, match_context: Dict[str, Any]) -> str:
        """Extract match date from match context.

        Args:
            match_context: Match context dictionary

        Returns:
            Match date string in YYYY-MM-DD format
        """
        # Try common field names for match date
        date_fields = ["speldatum", "match_date", "datum", "date"]

        for field in date_fields:
            if field in match_context and match_context[field]:
                return str(match_context[field])

        # Default to today if no date found
        return datetime.now().strftime("%Y-%m-%d")

    def extract_team_names(self, match_context: Dict[str, Any]) -> tuple[str, str]:
        """Extract home and away team names from match context.

        Args:
            match_context: Match context dictionary

        Returns:
            Tuple of (home_team, away_team) names
        """
        home_team = match_context.get("hemmalag", match_context.get("home_team", "Home Team"))
        away_team = match_context.get("bortalag", match_context.get("away_team", "Away Team"))

        return str(home_team), str(away_team)

    def format_date_friendly(self, date_str: str) -> str:
        """Format date in user-friendly way.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            User-friendly formatted date
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%A, %B %d, %Y")
        except (ValueError, TypeError):
            return date_str
