"""Data models for notification monitoring and delivery tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DeliveryStatus(Enum):
    """Status of notification delivery."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    RATE_LIMITED = "rate_limited"
    DEAD_LETTER = "dead_letter"


class FailureReason(Enum):
    """Reason for delivery failure."""

    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT = "rate_limit"
    INVALID_RECIPIENT = "invalid_recipient"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class DeliveryAttempt:
    """Individual delivery attempt record."""

    attempt_number: int
    timestamp: datetime
    status: DeliveryStatus
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    failure_reason: Optional[FailureReason] = None
    retry_after: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "failure_reason": (self.failure_reason.value if self.failure_reason else None),
            "retry_after": self.retry_after.isoformat() if self.retry_after else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeliveryAttempt":
        """Create from dictionary."""
        return cls(
            attempt_number=data["attempt_number"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=DeliveryStatus(data["status"]),
            response_time_ms=data.get("response_time_ms"),
            error_message=data.get("error_message"),
            failure_reason=(
                FailureReason(data["failure_reason"]) if data.get("failure_reason") else None
            ),
            retry_after=(
                datetime.fromisoformat(data["retry_after"]) if data.get("retry_after") else None
            ),
        )


@dataclass
class NotificationDeliveryRecord:
    """Complete delivery record for a notification."""

    notification_id: str
    channel: str
    recipient: str
    created_at: datetime
    final_status: DeliveryStatus
    attempts: List[DeliveryAttempt] = field(default_factory=list)
    total_attempts: int = 0
    first_attempt: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    total_delivery_time_ms: Optional[int] = None

    def add_attempt(self, attempt: DeliveryAttempt) -> None:
        """Add delivery attempt to record."""
        self.attempts.append(attempt)
        self.total_attempts += 1
        self.last_attempt = attempt.timestamp

        if self.first_attempt is None:
            self.first_attempt = attempt.timestamp

        if attempt.status == DeliveryStatus.DELIVERED:
            self.delivered_at = attempt.timestamp
            self.final_status = DeliveryStatus.DELIVERED
            if self.first_attempt:
                self.total_delivery_time_ms = int(
                    (self.delivered_at - self.first_attempt).total_seconds() * 1000
                )
        elif attempt.status in [DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER]:
            self.final_status = attempt.status

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "notification_id": self.notification_id,
            "channel": self.channel,
            "recipient": self.recipient,
            "created_at": self.created_at.isoformat(),
            "final_status": self.final_status.value,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "total_attempts": self.total_attempts,
            "first_attempt": (self.first_attempt.isoformat() if self.first_attempt else None),
            "last_attempt": (self.last_attempt.isoformat() if self.last_attempt else None),
            "delivered_at": (self.delivered_at.isoformat() if self.delivered_at else None),
            "total_delivery_time_ms": self.total_delivery_time_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationDeliveryRecord":
        """Create from dictionary."""
        record = cls(
            notification_id=data["notification_id"],
            channel=data["channel"],
            recipient=data["recipient"],
            created_at=datetime.fromisoformat(data["created_at"]),
            final_status=DeliveryStatus(data["final_status"]),
            total_attempts=data["total_attempts"],
            first_attempt=(
                datetime.fromisoformat(data["first_attempt"]) if data.get("first_attempt") else None
            ),
            last_attempt=(
                datetime.fromisoformat(data["last_attempt"]) if data.get("last_attempt") else None
            ),
            delivered_at=(
                datetime.fromisoformat(data["delivered_at"]) if data.get("delivered_at") else None
            ),
            total_delivery_time_ms=data.get("total_delivery_time_ms"),
        )

        # Restore attempts
        for attempt_data in data.get("attempts", []):
            record.attempts.append(DeliveryAttempt.from_dict(attempt_data))

        return record


@dataclass
class DeliveryResult:
    """Result of a delivery attempt."""

    status: DeliveryStatus
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    failure_reason: Optional[FailureReason] = None

    @property
    def success(self) -> bool:
        """Check if delivery was successful."""
        return self.status in [DeliveryStatus.SENT, DeliveryStatus.DELIVERED]


@dataclass
class NotificationHealthStatus:
    """Health status of notification system."""

    status: str  # "healthy", "degraded", "unhealthy"
    issues: List[str] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.utcnow)
    stats: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "issues": self.issues,
            "last_check": self.last_check.isoformat(),
            "stats": self.stats,
        }
