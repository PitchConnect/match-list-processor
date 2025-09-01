"""Stakeholder data models for notification system."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .notification_models import NotificationChannel


@dataclass
class ContactInfo:
    """Contact information for a stakeholder."""

    channel: NotificationChannel
    address: str  # email, phone, webhook URL, etc.
    verified: bool = False
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_verified: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "channel": self.channel.value,
            "address": self.address,
            "verified": self.verified,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_verified": self.last_verified.isoformat() if self.last_verified else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContactInfo":
        """Create from dictionary."""
        return cls(
            channel=NotificationChannel(data["channel"]),
            address=data["address"],
            verified=data.get("verified", False),
            active=data.get("active", True),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            last_verified=(
                datetime.fromisoformat(data["last_verified"]) if data.get("last_verified") else None
            ),
        )


@dataclass
class NotificationPreferences:
    """Notification preferences for a stakeholder."""

    enabled_channels: Set[NotificationChannel] = field(
        default_factory=lambda: {NotificationChannel.EMAIL}
    )
    enabled_change_types: Set[str] = field(
        default_factory=lambda: {
            "new_assignment",
            "referee_change",
            "time_change",
            "date_change",
            "venue_change",
            "cancellation",
        }
    )
    minimum_priority: str = "medium"  # low, medium, high, critical
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None  # HH:MM format
    timezone: str = "UTC"
    digest_mode: bool = False  # If true, batch notifications
    digest_frequency: str = "immediate"  # immediate, hourly, daily

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "enabled_channels": [c.value for c in self.enabled_channels],
            "enabled_change_types": list(self.enabled_change_types),
            "minimum_priority": self.minimum_priority,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "timezone": self.timezone,
            "digest_mode": self.digest_mode,
            "digest_frequency": self.digest_frequency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationPreferences":
        """Create from dictionary."""
        return cls(
            enabled_channels={
                NotificationChannel(c) for c in data.get("enabled_channels", ["email"])
            },
            enabled_change_types=set(
                data.get(
                    "enabled_change_types",
                    [
                        "new_assignment",
                        "referee_change",
                        "time_change",
                        "date_change",
                        "venue_change",
                        "cancellation",
                    ],
                )
            ),
            minimum_priority=data.get("minimum_priority", "medium"),
            quiet_hours_start=data.get("quiet_hours_start"),
            quiet_hours_end=data.get("quiet_hours_end"),
            timezone=data.get("timezone", "UTC"),
            digest_mode=data.get("digest_mode", False),
            digest_frequency=data.get("digest_frequency", "immediate"),
        )


@dataclass
class Stakeholder:
    """Represents a stakeholder in the notification system."""

    stakeholder_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: str = ""  # referee, coordinator, team_manager, etc.
    fogis_person_id: Optional[str] = None
    contact_info: List[ContactInfo] = field(default_factory=list)
    preferences: NotificationPreferences = field(default_factory=NotificationPreferences)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "stakeholder_id": self.stakeholder_id,
            "name": self.name,
            "role": self.role,
            "fogis_person_id": self.fogis_person_id,
            "contact_info": [c.to_dict() for c in self.contact_info],
            "preferences": self.preferences.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stakeholder":
        """Create from dictionary."""
        contact_info = [ContactInfo.from_dict(c) for c in data.get("contact_info", [])]
        preferences = NotificationPreferences.from_dict(data.get("preferences", {}))

        return cls(
            stakeholder_id=data.get("stakeholder_id", str(uuid.uuid4())),
            name=data.get("name", ""),
            role=data.get("role", ""),
            fogis_person_id=data.get("fogis_person_id"),
            contact_info=contact_info,
            preferences=preferences,
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if "created_at" in data
                else datetime.utcnow()
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if "updated_at" in data
                else datetime.utcnow()
            ),
            active=data.get("active", True),
            metadata=data.get("metadata", {}),
        )

    def get_contact_by_channel(self, channel: NotificationChannel) -> Optional[ContactInfo]:
        """Get contact info for a specific channel."""
        for contact in self.contact_info:
            if contact.channel == channel and contact.active:
                return contact
        return None

    def add_contact_info(
        self, channel: NotificationChannel, address: str, verified: bool = False
    ) -> None:
        """Add new contact information."""
        # Remove existing contact for this channel
        self.contact_info = [c for c in self.contact_info if c.channel != channel]

        # Add new contact
        self.contact_info.append(
            ContactInfo(
                channel=channel,
                address=address,
                verified=verified,
                active=True,
            )
        )
        self.updated_at = datetime.utcnow()

    def should_receive_notification(self, change_category: str, priority: str) -> bool:
        """Check if stakeholder should receive notification based on preferences."""
        if not self.active:
            return False

        # Check if change type is enabled
        if change_category not in self.preferences.enabled_change_types:
            return False

        # Check priority threshold
        priority_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_priority_level = priority_levels.get(self.preferences.minimum_priority, 1)
        current_priority_level = priority_levels.get(priority, 1)

        return current_priority_level >= min_priority_level

    def get_enabled_channels(self) -> List[NotificationChannel]:
        """Get list of enabled notification channels with valid contact info."""
        enabled_channels = []

        for channel in self.preferences.enabled_channels:
            contact = self.get_contact_by_channel(channel)
            if contact and contact.active:
                enabled_channels.append(channel)

        return enabled_channels
