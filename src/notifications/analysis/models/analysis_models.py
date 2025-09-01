"""Data models for semantic change analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ChangeImpact(Enum):
    """Impact level of a change."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Significant impact
    MEDIUM = "medium"  # Moderate impact
    LOW = "low"  # Minor impact
    INFORMATIONAL = "info"  # FYI only


class ChangeUrgency(Enum):
    """Urgency level of a change based on timing."""

    IMMEDIATE = "immediate"  # Same day or past due
    URGENT = "urgent"  # Within 24-48 hours
    NORMAL = "normal"  # More than 48 hours
    FUTURE = "future"  # Far future changes


@dataclass
class ChangeContext:
    """Rich context information for a field change."""

    field_path: str  # e.g., "domaruppdraglista[0].namn"
    field_display_name: str  # e.g., "Referee Name"
    change_type: str  # "added", "removed", "modified"
    previous_value: Any
    current_value: Any
    business_impact: ChangeImpact
    urgency: ChangeUrgency
    affected_stakeholders: List[str]
    change_description: str
    technical_description: str
    user_friendly_description: str
    related_changes: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SemanticChangeAnalysis:
    """Complete semantic analysis of a match change."""

    match_id: str
    change_category: str
    field_changes: List[ChangeContext]
    overall_impact: ChangeImpact
    overall_urgency: ChangeUrgency
    change_summary: str
    detailed_analysis: str
    stakeholder_impact_map: Dict[str, List[str]]
    recommended_actions: List[str]
    correlation_id: Optional[str] = None
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_critical_changes(self) -> bool:
        """Check if analysis contains critical changes."""
        return any(change.business_impact == ChangeImpact.CRITICAL for change in self.field_changes)

    @property
    def requires_immediate_action(self) -> bool:
        """Check if analysis requires immediate action."""
        return (
            self.overall_urgency == ChangeUrgency.IMMEDIATE
            or self.overall_impact == ChangeImpact.CRITICAL
        )

    def get_changes_by_impact(self, impact: ChangeImpact) -> List[ChangeContext]:
        """Get all changes with specified impact level."""
        return [change for change in self.field_changes if change.business_impact == impact]

    def get_changes_by_urgency(self, urgency: ChangeUrgency) -> List[ChangeContext]:
        """Get all changes with specified urgency level."""
        return [change for change in self.field_changes if change.urgency == urgency]
