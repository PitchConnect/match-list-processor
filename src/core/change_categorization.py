"""Enhanced change categorization system for granular change detection."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ChangeCategory(Enum):
    """Categories of changes that can occur in match data."""

    NEW_ASSIGNMENT = "new_assignment"
    REFEREE_CHANGE = "referee_change"
    TIME_CHANGE = "time_change"
    DATE_CHANGE = "date_change"
    VENUE_CHANGE = "venue_change"
    TEAM_CHANGE = "team_change"
    STATUS_CHANGE = "status_change"
    CANCELLATION = "cancellation"
    POSTPONEMENT = "postponement"
    INTERRUPTION = "interruption"
    COMPETITION_CHANGE = "competition_change"
    UNKNOWN = "unknown"


class ChangePriority(Enum):
    """Priority levels for changes based on urgency and impact."""

    CRITICAL = "critical"  # Same-day changes, cancellations
    HIGH = "high"  # Referee changes, time changes
    MEDIUM = "medium"  # Venue changes, team changes
    LOW = "low"  # Competition changes, minor updates


class StakeholderType(Enum):
    """Types of stakeholders affected by changes."""

    REFEREES = "referees"
    COORDINATORS = "coordinators"
    TEAMS = "teams"
    ALL = "all"


@dataclass
class MatchChangeDetail:
    """Detailed information about a specific change."""

    match_id: str
    match_nr: Optional[str]
    category: ChangeCategory
    priority: ChangePriority
    affected_stakeholders: List[StakeholderType]
    field_name: str
    previous_value: Any
    current_value: Any
    change_description: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "match_id": self.match_id,
            "match_nr": self.match_nr,
            "category": self.category.value,
            "priority": self.priority.value,
            "affected_stakeholders": [s.value for s in self.affected_stakeholders],
            "field_name": self.field_name,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "change_description": self.change_description,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CategorizedChanges:
    """Collection of categorized changes with metadata."""

    changes: List[MatchChangeDetail]
    total_changes: int
    critical_changes: int
    high_priority_changes: int
    affected_stakeholder_types: Set[StakeholderType]
    change_categories: Set[ChangeCategory]

    @property
    def has_changes(self) -> bool:
        """Check if any changes exist."""
        return self.total_changes > 0

    @property
    def has_critical_changes(self) -> bool:
        """Check if any critical changes exist."""
        return self.critical_changes > 0

    def get_changes_by_category(self, category: ChangeCategory) -> List[MatchChangeDetail]:
        """Get all changes of a specific category."""
        return [change for change in self.changes if change.category == category]

    def get_changes_by_priority(self, priority: ChangePriority) -> List[MatchChangeDetail]:
        """Get all changes of a specific priority."""
        return [change for change in self.changes if change.priority == priority]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "changes": [change.to_dict() for change in self.changes],
            "total_changes": self.total_changes,
            "critical_changes": self.critical_changes,
            "high_priority_changes": self.high_priority_changes,
            "affected_stakeholder_types": [s.value for s in self.affected_stakeholder_types],
            "change_categories": [c.value for c in self.change_categories],
            "has_changes": self.has_changes,
            "has_critical_changes": self.has_critical_changes,
        }


class GranularChangeDetector:
    """Enhanced change detector with granular categorization capabilities."""

    def __init__(self) -> None:
        """Initialize the granular change detector."""
        self.field_analyzers = {
            "speldatum": self._analyze_date_change,
            "avsparkstid": self._analyze_time_change,
            "anlaggningnamn": self._analyze_venue_change,
            "lag1lagid": self._analyze_team_change,
            "lag1namn": self._analyze_team_change,
            "lag2lagid": self._analyze_team_change,
            "lag2namn": self._analyze_team_change,
            "installd": self._analyze_status_change,
            "avbruten": self._analyze_status_change,
            "uppskjuten": self._analyze_status_change,
        }

    def categorize_changes(
        self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]
    ) -> List[MatchChangeDetail]:
        """Categorize all changes between previous and current match data.

        Args:
            prev_match: Previous match data
            curr_match: Current match data

        Returns:
            List of categorized change details
        """
        changes: List[MatchChangeDetail] = []
        match_id = curr_match.get("matchid", "unknown")
        match_nr = curr_match.get("matchnr")

        # Special handling for referee changes first
        referee_changes = self._detect_referee_changes(prev_match, curr_match)
        changes.extend(referee_changes)

        # Analyze each field for changes
        for field_name, analyzer in self.field_analyzers.items():
            # Standard field comparison
            prev_value = prev_match.get(field_name)
            curr_value = curr_match.get(field_name)

            if prev_value != curr_value:
                change_detail = analyzer(
                    match_id, match_nr, field_name, prev_value, curr_value, curr_match
                )
                if change_detail:
                    changes.append(change_detail)

        return changes

    def _detect_referee_changes(
        self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]
    ) -> List[MatchChangeDetail]:
        """Detect and categorize referee changes."""
        changes: List[MatchChangeDetail] = []
        match_id = curr_match.get("matchid", "unknown")
        match_nr = curr_match.get("matchnr")

        prev_referees = self._extract_referee_info(prev_match)
        curr_referees = self._extract_referee_info(curr_match)

        # Check for new assignments
        if not prev_referees and curr_referees:
            changes.append(
                MatchChangeDetail(
                    match_id=match_id,
                    match_nr=match_nr,
                    category=ChangeCategory.NEW_ASSIGNMENT,
                    priority=self._assess_priority(ChangeCategory.NEW_ASSIGNMENT, curr_match),
                    affected_stakeholders=[StakeholderType.REFEREES, StakeholderType.COORDINATORS],
                    field_name="domaruppdraglista",
                    previous_value=None,
                    current_value=curr_referees,
                    change_description=f"New referee assignment: {len(curr_referees)} referees assigned",
                    timestamp=datetime.now(timezone.utc),
                )
            )

        # Check for referee changes
        elif prev_referees != curr_referees:
            changes.append(
                MatchChangeDetail(
                    match_id=match_id,
                    match_nr=match_nr,
                    category=ChangeCategory.REFEREE_CHANGE,
                    priority=self._assess_priority(ChangeCategory.REFEREE_CHANGE, curr_match),
                    affected_stakeholders=[StakeholderType.REFEREES, StakeholderType.COORDINATORS],
                    field_name="domaruppdraglista",
                    previous_value=prev_referees,
                    current_value=curr_referees,
                    change_description=self._describe_referee_change(prev_referees, curr_referees),
                    timestamp=datetime.now(timezone.utc),
                )
            )

        return changes

    def _extract_referee_info(self, match: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract referee information from match data."""
        referees = []
        if "domaruppdraglista" in match:
            for referee in match["domaruppdraglista"]:
                referees.append(
                    {
                        "id": referee.get("domarid"),
                        "name": referee.get("personnamn"),
                        "role": referee.get("domarrollnamn"),
                    }
                )
        return referees

    def _describe_referee_change(
        self, prev_referees: List[Dict[str, Any]], curr_referees: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable description of referee changes."""
        prev_names = [ref.get("name", "Unknown") for ref in prev_referees]
        curr_names = [ref.get("name", "Unknown") for ref in curr_referees]

        if not prev_names:
            return f"Referees assigned: {', '.join(curr_names)}"
        elif not curr_names:
            return f"Referees removed: {', '.join(prev_names)}"
        else:
            return f"Referees changed from {', '.join(prev_names)} to {', '.join(curr_names)}"

    def _analyze_date_change(
        self,
        match_id: str,
        match_nr: Optional[str],
        field_name: str,
        prev_value: Any,
        curr_value: Any,
        curr_match: Dict[str, Any],
    ) -> Optional[MatchChangeDetail]:
        """Analyze date changes."""
        return MatchChangeDetail(
            match_id=match_id,
            match_nr=match_nr,
            category=ChangeCategory.DATE_CHANGE,
            priority=self._assess_priority(ChangeCategory.DATE_CHANGE, curr_match),
            affected_stakeholders=[StakeholderType.ALL],
            field_name=field_name,
            previous_value=prev_value,
            current_value=curr_value,
            change_description=f"Match date changed from {prev_value} to {curr_value}",
            timestamp=datetime.now(timezone.utc),
        )

    def _analyze_time_change(
        self,
        match_id: str,
        match_nr: Optional[str],
        field_name: str,
        prev_value: Any,
        curr_value: Any,
        curr_match: Dict[str, Any],
    ) -> Optional[MatchChangeDetail]:
        """Analyze time changes."""
        return MatchChangeDetail(
            match_id=match_id,
            match_nr=match_nr,
            category=ChangeCategory.TIME_CHANGE,
            priority=self._assess_priority(ChangeCategory.TIME_CHANGE, curr_match),
            affected_stakeholders=[StakeholderType.ALL],
            field_name=field_name,
            previous_value=prev_value,
            current_value=curr_value,
            change_description=f"Match time changed from {prev_value} to {curr_value}",
            timestamp=datetime.now(timezone.utc),
        )

    def _analyze_venue_change(
        self,
        match_id: str,
        match_nr: Optional[str],
        field_name: str,
        prev_value: Any,
        curr_value: Any,
        curr_match: Dict[str, Any],
    ) -> Optional[MatchChangeDetail]:
        """Analyze venue changes."""
        return MatchChangeDetail(
            match_id=match_id,
            match_nr=match_nr,
            category=ChangeCategory.VENUE_CHANGE,
            priority=self._assess_priority(ChangeCategory.VENUE_CHANGE, curr_match),
            affected_stakeholders=[StakeholderType.ALL],
            field_name=field_name,
            previous_value=prev_value,
            current_value=curr_value,
            change_description=f"Venue changed from {prev_value} to {curr_value}",
            timestamp=datetime.now(timezone.utc),
        )

    def _analyze_team_change(
        self,
        match_id: str,
        match_nr: Optional[str],
        field_name: str,
        prev_value: Any,
        curr_value: Any,
        curr_match: Dict[str, Any],
    ) -> Optional[MatchChangeDetail]:
        """Analyze team changes."""
        return MatchChangeDetail(
            match_id=match_id,
            match_nr=match_nr,
            category=ChangeCategory.TEAM_CHANGE,
            priority=self._assess_priority(ChangeCategory.TEAM_CHANGE, curr_match),
            affected_stakeholders=[StakeholderType.TEAMS, StakeholderType.COORDINATORS],
            field_name=field_name,
            previous_value=prev_value,
            current_value=curr_value,
            change_description=f"Team information changed: {field_name} from {prev_value} to {curr_value}",
            timestamp=datetime.now(timezone.utc),
        )

    def _analyze_status_change(
        self,
        match_id: str,
        match_nr: Optional[str],
        field_name: str,
        prev_value: Any,
        curr_value: Any,
        curr_match: Dict[str, Any],
    ) -> Optional[MatchChangeDetail]:
        """Analyze status changes (cancellation, postponement, interruption)."""
        category = ChangeCategory.STATUS_CHANGE
        description = f"Status changed: {field_name} from {prev_value} to {curr_value}"

        # Determine specific category based on field
        if field_name == "installd" and curr_value:
            category = ChangeCategory.CANCELLATION
            description = "Match cancelled"
        elif field_name == "uppskjuten" and curr_value:
            category = ChangeCategory.POSTPONEMENT
            description = "Match postponed"
        elif field_name == "avbruten" and curr_value:
            category = ChangeCategory.INTERRUPTION
            description = "Match interrupted"

        return MatchChangeDetail(
            match_id=match_id,
            match_nr=match_nr,
            category=category,
            priority=self._assess_priority(category, curr_match),
            affected_stakeholders=[StakeholderType.ALL],
            field_name=field_name,
            previous_value=prev_value,
            current_value=curr_value,
            change_description=description,
            timestamp=datetime.now(timezone.utc),
        )

    def _assess_priority(
        self, category: ChangeCategory, match_data: Dict[str, Any]
    ) -> ChangePriority:
        """Assess the priority of a change based on category and timing."""
        match_date_str = match_data.get("speldatum", "")

        # Check if this is a same-day change (critical priority)
        if self._is_same_day_change(match_date_str):
            return ChangePriority.CRITICAL

        # Category-based priority assessment
        priority_map = {
            ChangeCategory.CANCELLATION: ChangePriority.CRITICAL,
            ChangeCategory.NEW_ASSIGNMENT: ChangePriority.HIGH,
            ChangeCategory.REFEREE_CHANGE: ChangePriority.HIGH,
            ChangeCategory.TIME_CHANGE: ChangePriority.HIGH,
            ChangeCategory.DATE_CHANGE: ChangePriority.HIGH,
            ChangeCategory.VENUE_CHANGE: ChangePriority.MEDIUM,
            ChangeCategory.TEAM_CHANGE: ChangePriority.MEDIUM,
            ChangeCategory.POSTPONEMENT: ChangePriority.MEDIUM,
            ChangeCategory.INTERRUPTION: ChangePriority.MEDIUM,
            ChangeCategory.STATUS_CHANGE: ChangePriority.MEDIUM,
            ChangeCategory.COMPETITION_CHANGE: ChangePriority.LOW,
            ChangeCategory.UNKNOWN: ChangePriority.LOW,
        }

        return priority_map.get(category, ChangePriority.LOW)

    def _is_same_day_change(self, match_date_str: str) -> bool:
        """Check if the match is on the same day as the change."""
        try:
            if not match_date_str:
                return False

            # Parse match date (assuming format YYYY-MM-DD)
            match_date = datetime.strptime(match_date_str, "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()

            return match_date == today
        except (ValueError, TypeError):
            return False
