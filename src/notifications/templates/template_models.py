"""Template models for notification system."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List


class TemplateType(Enum):
    """Template types for different notification scenarios."""

    NEW_ASSIGNMENT = "new_assignment"
    REFEREE_CHANGE = "referee_change"
    TIME_CHANGE = "time_change"
    DATE_CHANGE = "date_change"
    VENUE_CHANGE = "venue_change"
    CANCELLATION = "cancellation"
    REMINDER = "reminder"
    DIGEST = "digest"


@dataclass
class TemplateContext:
    """Context data for template rendering."""

    # Match information
    match_id: str
    match_number: str
    team1_name: str
    team2_name: str
    match_date: str
    match_time: str
    venue_name: str
    series_name: str

    # Change information
    change_type: str
    change_summary: str
    change_details: List[Dict[str, Any]] = field(default_factory=list)
    priority: str = "medium"

    # Stakeholder information
    recipient_name: str = ""
    recipient_role: str = ""
    stakeholder_id: str = ""

    # System information
    notification_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    system_name: str = "FOGIS"
    support_email: str = "support@fogis.se"

    # Template customization
    brand_color: str = "#1e40af"  # Blue
    logo_url: str = ""
    footer_text: str = "FOGIS Notification System"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "match": {
                "id": self.match_id,
                "number": self.match_number,
                "team1": self.team1_name,
                "team2": self.team2_name,
                "date": self.match_date,
                "time": self.match_time,
                "venue": self.venue_name,
                "series": self.series_name,
            },
            "change": {
                "type": self.change_type,
                "summary": self.change_summary,
                "details": self.change_details,
                "priority": self.priority,
            },
            "recipient": {
                "name": self.recipient_name,
                "role": self.recipient_role,
                "id": self.stakeholder_id,
            },
            "system": {
                "name": self.system_name,
                "support_email": self.support_email,
                "notification_id": self.notification_id,
                "timestamp": self.timestamp.isoformat(),
            },
            "branding": {
                "color": self.brand_color,
                "logo_url": self.logo_url,
                "footer": self.footer_text,
            },
        }


@dataclass
class NotificationTemplate:
    """Template definition for notifications."""

    template_type: TemplateType
    name: str
    description: str
    subject_template: str
    html_template: str
    text_template: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_type": self.template_type.value,
            "name": self.name,
            "description": self.description,
            "subject_template": self.subject_template,
            "html_template": self.html_template,
            "text_template": self.text_template,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationTemplate":
        """Create from dictionary."""
        return cls(
            template_type=TemplateType(data["template_type"]),
            name=data["name"],
            description=data["description"],
            subject_template=data["subject_template"],
            html_template=data["html_template"],
            text_template=data["text_template"],
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.now(timezone.utc)
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.now(timezone.utc)
            ),
            version=data.get("version", "1.0"),
            is_active=data.get("is_active", True),
        )


@dataclass
class RenderedTemplate:
    """Rendered template ready for delivery."""

    template_type: TemplateType
    subject: str
    html_content: str
    text_content: str
    context: TemplateContext
    rendered_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_type": self.template_type.value,
            "subject": self.subject,
            "html_content": self.html_content,
            "text_content": self.text_content,
            "rendered_at": self.rendered_at.isoformat(),
            "context": self.context.to_dict(),
        }
