"""Change context model for field-level analysis."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .analysis_models import ChangeImpact, ChangeUrgency


@dataclass
class ChangeContext:
    """Detailed context for a specific field change."""

    # Core change information
    field_path: str
    field_display_name: str
    change_type: str  # "added", "removed", "modified"
    previous_value: Any
    current_value: Any

    # Business context
    business_impact: ChangeImpact
    urgency: ChangeUrgency
    affected_stakeholders: List[str]

    # Descriptions
    change_description: str
    technical_description: str
    user_friendly_description: str

    # Metadata
    related_changes: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    match_context: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Set default timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "field_path": self.field_path,
            "field_display_name": self.field_display_name,
            "change_type": self.change_type,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "business_impact": self.business_impact.value,
            "urgency": self.urgency.value,
            "affected_stakeholders": self.affected_stakeholders,
            "change_description": self.change_description,
            "technical_description": self.technical_description,
            "user_friendly_description": self.user_friendly_description,
            "related_changes": self.related_changes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "match_context": self.match_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeContext":
        """Create from dictionary representation."""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])

        return cls(
            field_path=data["field_path"],
            field_display_name=data["field_display_name"],
            change_type=data["change_type"],
            previous_value=data["previous_value"],
            current_value=data["current_value"],
            business_impact=ChangeImpact(data["business_impact"]),
            urgency=ChangeUrgency(data["urgency"]),
            affected_stakeholders=data["affected_stakeholders"],
            change_description=data["change_description"],
            technical_description=data["technical_description"],
            user_friendly_description=data["user_friendly_description"],
            related_changes=data.get("related_changes"),
            timestamp=timestamp,
            match_context=data.get("match_context"),
        )
