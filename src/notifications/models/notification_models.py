"""Core notification data models."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationChannel(Enum):
    """Supported notification channels."""

    EMAIL = "email"
    DISCORD = "discord"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"


class NotificationPriority(Enum):
    """Notification priority levels."""

    CRITICAL = "critical"  # Same-day changes, cancellations
    HIGH = "high"  # Referee changes, time/date changes
    MEDIUM = "medium"  # Venue changes, team changes
    LOW = "low"  # Minor updates, competition details


class DeliveryStatus(Enum):
    """Delivery status for notifications."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    RATE_LIMITED = "rate_limited"
    DEAD_LETTER = "dead_letter"


@dataclass
class NotificationRecipient:
    """Represents a notification recipient."""

    stakeholder_id: str
    name: str
    channel: NotificationChannel
    address: str  # email, webhook URL, phone number, etc.
    preferences: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stakeholder_id": self.stakeholder_id,
            "name": self.name,
            "channel": self.channel.value,
            "address": self.address,
            "preferences": self.preferences,
        }


@dataclass
class ChangeNotification:
    """Represents a change notification to be sent."""

    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    change_category: str = ""
    priority: NotificationPriority = NotificationPriority.MEDIUM
    change_summary: str = ""
    field_changes: List[Dict[str, Any]] = field(default_factory=list)
    match_context: Dict[str, Any] = field(default_factory=dict)
    affected_stakeholders: List[str] = field(default_factory=list)
    recipients: List[NotificationRecipient] = field(default_factory=list)
    delivery_status: Dict[str, DeliveryStatus] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "notification_id": self.notification_id,
            "timestamp": self.timestamp.isoformat(),
            "change_category": self.change_category,
            "priority": self.priority.value,
            "change_summary": self.change_summary,
            "field_changes": self.field_changes,
            "match_context": self.match_context,
            "affected_stakeholders": self.affected_stakeholders,
            "recipients": [r.to_dict() for r in self.recipients],
            "delivery_status": {k: v.value for k, v in self.delivery_status.items()},
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChangeNotification":
        """Create from dictionary."""
        recipients = [
            NotificationRecipient(
                stakeholder_id=r["stakeholder_id"],
                name=r["name"],
                channel=NotificationChannel(r["channel"]),
                address=r["address"],
                preferences=r.get("preferences", {}),
            )
            for r in data.get("recipients", [])
        ]

        delivery_status = {k: DeliveryStatus(v) for k, v in data.get("delivery_status", {}).items()}

        return cls(
            notification_id=data.get("notification_id", str(uuid.uuid4())),
            timestamp=(
                datetime.fromisoformat(data["timestamp"])
                if "timestamp" in data
                else datetime.now(timezone.utc)
            ),
            change_category=data.get("change_category", ""),
            priority=NotificationPriority(data.get("priority", "medium")),
            change_summary=data.get("change_summary", ""),
            field_changes=data.get("field_changes", []),
            match_context=data.get("match_context", {}),
            affected_stakeholders=data.get("affected_stakeholders", []),
            recipients=recipients,
            delivery_status=delivery_status,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )


@dataclass
class DeliveryResult:
    """Result of a notification delivery attempt."""

    recipient_id: str
    channel: NotificationChannel
    status: DeliveryStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    error_details: Optional[str] = None
    retry_after: Optional[int] = None  # seconds to wait before retry

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "recipient_id": self.recipient_id,
            "channel": self.channel.value,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "error_details": self.error_details,
            "retry_after": self.retry_after,
        }


@dataclass
class NotificationBatch:
    """Represents a batch of notifications for processing."""

    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notifications: List[ChangeNotification] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    total_recipients: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "notifications": [n.to_dict() for n in self.notifications],
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "total_recipients": self.total_recipients,
            "successful_deliveries": self.successful_deliveries,
            "failed_deliveries": self.failed_deliveries,
        }
