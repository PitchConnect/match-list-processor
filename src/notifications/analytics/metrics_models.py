"""Analytics and metrics models for notification system."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..models.notification_models import NotificationChannel, NotificationPriority


@dataclass
class DeliveryMetrics:
    """Metrics for notification delivery performance."""

    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_pending: int = 0
    delivery_rate: float = 0.0
    failure_rate: float = 0.0
    average_delivery_time: float = 0.0  # seconds
    retry_count: int = 0

    def calculate_rates(self) -> None:
        """Calculate delivery and failure rates."""
        if self.total_sent > 0:
            self.delivery_rate = self.total_delivered / self.total_sent
            self.failure_rate = self.total_failed / self.total_sent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_sent": self.total_sent,
            "total_delivered": self.total_delivered,
            "total_failed": self.total_failed,
            "total_pending": self.total_pending,
            "delivery_rate": round(self.delivery_rate, 3),
            "failure_rate": round(self.failure_rate, 3),
            "average_delivery_time": round(self.average_delivery_time, 2),
            "retry_count": self.retry_count,
        }


@dataclass
class ChannelMetrics:
    """Metrics for specific notification channels."""

    channel: NotificationChannel
    delivery_metrics: DeliveryMetrics = field(default_factory=DeliveryMetrics)
    active_recipients: int = 0
    preferred_by_users: int = 0
    average_response_time: float = 0.0  # seconds
    error_types: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "channel": self.channel.value,
            "delivery_metrics": self.delivery_metrics.to_dict(),
            "active_recipients": self.active_recipients,
            "preferred_by_users": self.preferred_by_users,
            "average_response_time": round(self.average_response_time, 2),
            "error_types": self.error_types,
        }


@dataclass
class EngagementMetrics:
    """Metrics for notification engagement and user interaction."""

    notification_opens: int = 0
    link_clicks: int = 0
    unsubscribe_requests: int = 0
    preference_changes: int = 0
    feedback_responses: int = 0
    engagement_rate: float = 0.0

    def calculate_engagement_rate(self, total_delivered: int) -> None:
        """Calculate engagement rate based on opens and clicks."""
        if total_delivered > 0:
            self.engagement_rate = (self.notification_opens + self.link_clicks) / total_delivered

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notification_opens": self.notification_opens,
            "link_clicks": self.link_clicks,
            "unsubscribe_requests": self.unsubscribe_requests,
            "preference_changes": self.preference_changes,
            "feedback_responses": self.feedback_responses,
            "engagement_rate": round(self.engagement_rate, 3),
        }


@dataclass
class AnalyticsMetrics:
    """Comprehensive analytics metrics for notification system."""

    # Time period
    start_time: datetime
    end_time: datetime
    period_duration: timedelta = field(init=False)

    # Overall metrics
    overall_delivery: DeliveryMetrics = field(default_factory=DeliveryMetrics)
    overall_engagement: EngagementMetrics = field(default_factory=EngagementMetrics)

    # Channel-specific metrics
    channel_metrics: Dict[NotificationChannel, ChannelMetrics] = field(default_factory=dict)

    # Priority-based metrics
    priority_metrics: Dict[NotificationPriority, DeliveryMetrics] = field(default_factory=dict)

    # Notification type metrics
    type_metrics: Dict[str, DeliveryMetrics] = field(default_factory=dict)

    # Stakeholder metrics
    stakeholder_metrics: Dict[str, int] = field(default_factory=dict)

    # System performance
    system_uptime: float = 100.0  # percentage
    average_processing_time: float = 0.0  # seconds
    peak_throughput: int = 0  # notifications per minute

    def __post_init__(self) -> None:
        """Calculate period duration after initialization."""
        self.period_duration = self.end_time - self.start_time

    def add_channel_metrics(self, channel: NotificationChannel, metrics: ChannelMetrics) -> None:
        """Add metrics for a specific channel."""
        self.channel_metrics[channel] = metrics

    def add_priority_metrics(
        self, priority: NotificationPriority, metrics: DeliveryMetrics
    ) -> None:
        """Add metrics for a specific priority level."""
        self.priority_metrics[priority] = metrics

    def add_type_metrics(self, notification_type: str, metrics: DeliveryMetrics) -> None:
        """Add metrics for a specific notification type."""
        self.type_metrics[notification_type] = metrics

    def calculate_summary_metrics(self) -> None:
        """Calculate summary metrics from individual components."""
        # Calculate overall delivery metrics
        self.overall_delivery.calculate_rates()

        # Calculate overall engagement rate
        self.overall_engagement.calculate_engagement_rate(self.overall_delivery.total_delivered)

        # Calculate channel-specific rates
        for channel_metric in self.channel_metrics.values():
            channel_metric.delivery_metrics.calculate_rates()

        # Calculate priority-specific rates
        for priority_metric in self.priority_metrics.values():
            priority_metric.calculate_rates()

        # Calculate type-specific rates
        for type_metric in self.type_metrics.values():
            type_metric.calculate_rates()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "period": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "duration_hours": round(self.period_duration.total_seconds() / 3600, 2),
            },
            "overall_delivery": self.overall_delivery.to_dict(),
            "overall_engagement": self.overall_engagement.to_dict(),
            "channel_metrics": {
                channel.value: metrics.to_dict()
                for channel, metrics in self.channel_metrics.items()
            },
            "priority_metrics": {
                priority.value: metrics.to_dict()
                for priority, metrics in self.priority_metrics.items()
            },
            "type_metrics": self.type_metrics,
            "stakeholder_metrics": self.stakeholder_metrics,
            "system_performance": {
                "uptime_percentage": self.system_uptime,
                "average_processing_time": round(self.average_processing_time, 2),
                "peak_throughput": self.peak_throughput,
            },
        }


@dataclass
class NotificationReport:
    """Comprehensive notification system report."""

    report_id: str
    generated_at: datetime
    report_type: str  # daily, weekly, monthly, custom
    metrics: AnalyticsMetrics
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)

    def add_insight(self, insight: str) -> None:
        """Add an insight to the report."""
        self.insights.append(insight)

    def add_recommendation(self, recommendation: str) -> None:
        """Add a recommendation to the report."""
        self.recommendations.append(recommendation)

    def add_alert(self, alert: str) -> None:
        """Add an alert to the report."""
        self.alerts.append(alert)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "generated_at": self.generated_at.isoformat(),
            "report_type": self.report_type,
            "metrics": self.metrics.to_dict(),
            "insights": self.insights,
            "recommendations": self.recommendations,
            "alerts": self.alerts,
        }
