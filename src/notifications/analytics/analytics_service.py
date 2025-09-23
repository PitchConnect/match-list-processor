"""Notification analytics service for tracking and reporting."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.notification_models import DeliveryResult, DeliveryStatus, NotificationChannel
from .metrics_models import (
    AnalyticsMetrics,
    ChannelMetrics,
    DeliveryMetrics,
    EngagementMetrics,
    NotificationReport,
)

logger = logging.getLogger(__name__)


class NotificationAnalyticsService:
    """Service for tracking notification analytics and generating reports."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize analytics service.

        Args:
            storage_path: Path to store analytics data
        """
        self.storage_path = Path(storage_path) if storage_path else Path("data/analytics")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory metrics for current session
        self._current_metrics = AnalyticsMetrics(
            start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc)
        )

        # Delivery tracking
        self._delivery_history: List[Dict[str, Any]] = []
        self._engagement_events: List[Dict[str, Any]] = []

        logger.info(f"Analytics service initialized with storage: {self.storage_path}")

    def track_delivery(
        self, delivery_result: DeliveryResult, notification_type: str = "unknown"
    ) -> None:
        """Track a notification delivery result.

        Args:
            delivery_result: Result of notification delivery
            notification_type: Type of notification (e.g., 'new_assignment', 'time_change')
        """
        delivery_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recipient_id": delivery_result.recipient_id,
            "channel": delivery_result.channel.value,
            "status": delivery_result.status.value,
            "notification_type": notification_type,
            "delivery_timestamp": delivery_result.timestamp.isoformat(),
            "error_details": delivery_result.error_details,
        }

        self._delivery_history.append(delivery_event)

        # Update current metrics
        self._update_current_metrics(delivery_result, notification_type)

        logger.debug(
            f"Tracked delivery: {delivery_result.recipient_id} via {delivery_result.channel.value}"
        )

    def track_engagement(
        self,
        notification_id: str,
        recipient_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Track user engagement with notifications.

        Args:
            notification_id: ID of the notification
            recipient_id: ID of the recipient
            event_type: Type of engagement (open, click, unsubscribe, etc.)
            metadata: Additional event metadata
        """
        engagement_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notification_id": notification_id,
            "recipient_id": recipient_id,
            "event_type": event_type,
            "metadata": metadata or {},
        }

        self._engagement_events.append(engagement_event)

        # Update engagement metrics
        self._update_engagement_metrics(event_type)

        logger.debug(f"Tracked engagement: {event_type} for {notification_id}")

    def generate_report(
        self, start_time: datetime, end_time: datetime, report_type: str = "custom"
    ) -> NotificationReport:
        """Generate comprehensive analytics report.

        Args:
            start_time: Start of reporting period
            end_time: End of reporting period
            report_type: Type of report (daily, weekly, monthly, custom)

        Returns:
            Comprehensive notification report
        """
        logger.info(f"Generating {report_type} report for {start_time} to {end_time}")

        # Calculate metrics for the period
        metrics = self._calculate_period_metrics(start_time, end_time)

        # Generate report
        report = NotificationReport(
            report_id=str(uuid.uuid4()),
            generated_at=datetime.now(timezone.utc),
            report_type=report_type,
            metrics=metrics,
        )

        # Add insights and recommendations
        self._add_insights_and_recommendations(report)

        # Save report
        self._save_report(report)

        logger.info(f"Generated report {report.report_id}")
        return report

    def get_current_metrics(self) -> AnalyticsMetrics:
        """Get current session metrics.

        Returns:
            Current analytics metrics
        """
        self._current_metrics.end_time = datetime.now(timezone.utc)
        self._current_metrics.calculate_summary_metrics()
        return self._current_metrics

    def get_channel_performance(self, channel: NotificationChannel) -> ChannelMetrics:
        """Get performance metrics for a specific channel.

        Args:
            channel: Notification channel to analyze

        Returns:
            Channel-specific metrics
        """
        channel_deliveries = [
            event for event in self._delivery_history if event["channel"] == channel.value
        ]

        delivery_metrics = DeliveryMetrics()
        delivery_metrics.total_sent = len(channel_deliveries)
        delivery_metrics.total_delivered = len(
            [event for event in channel_deliveries if event["status"] == "delivered"]
        )
        delivery_metrics.total_failed = len(
            [event for event in channel_deliveries if event["status"] == "failed"]
        )
        delivery_metrics.calculate_rates()

        return ChannelMetrics(
            channel=channel,
            delivery_metrics=delivery_metrics,
            active_recipients=len(set(event["recipient_id"] for event in channel_deliveries)),
        )

    def get_delivery_statistics(self) -> Dict[str, Any]:
        """Get overall delivery statistics.

        Returns:
            Dictionary with delivery statistics
        """
        total_deliveries = len(self._delivery_history)
        if total_deliveries == 0:
            return {"total_deliveries": 0, "delivery_rate": 0.0, "failure_rate": 0.0}

        successful = len(
            [event for event in self._delivery_history if event["status"] == "delivered"]
        )
        failed = len([event for event in self._delivery_history if event["status"] == "failed"])

        return {
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful,
            "failed_deliveries": failed,
            "delivery_rate": (
                round(successful / total_deliveries, 3) if total_deliveries > 0 else 0.0
            ),
            "failure_rate": (round(failed / total_deliveries, 3) if total_deliveries > 0 else 0.0),
            "channels": self._get_channel_breakdown(),
        }

    def reset_metrics(self) -> None:
        """Reset current metrics and start fresh tracking."""
        self._current_metrics = AnalyticsMetrics(
            start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc)
        )
        self._delivery_history.clear()
        self._engagement_events.clear()
        logger.info("Analytics metrics reset")

    def _update_current_metrics(
        self, delivery_result: DeliveryResult, notification_type: str
    ) -> None:
        """Update current metrics with new delivery result."""
        # Update overall delivery metrics
        self._current_metrics.overall_delivery.total_sent += 1

        if delivery_result.status == DeliveryStatus.DELIVERED:
            self._current_metrics.overall_delivery.total_delivered += 1
        elif delivery_result.status == DeliveryStatus.FAILED:
            self._current_metrics.overall_delivery.total_failed += 1
        elif delivery_result.status == DeliveryStatus.PENDING:
            self._current_metrics.overall_delivery.total_pending += 1

        # Update channel metrics
        channel = delivery_result.channel
        if channel not in self._current_metrics.channel_metrics:
            self._current_metrics.channel_metrics[channel] = ChannelMetrics(channel=channel)

        channel_metrics = self._current_metrics.channel_metrics[channel]
        channel_metrics.delivery_metrics.total_sent += 1

        if delivery_result.status == DeliveryStatus.DELIVERED:
            channel_metrics.delivery_metrics.total_delivered += 1
        elif delivery_result.status == DeliveryStatus.FAILED:
            channel_metrics.delivery_metrics.total_failed += 1

        # Update type metrics
        if notification_type not in self._current_metrics.type_metrics:
            self._current_metrics.type_metrics[notification_type] = DeliveryMetrics()

        type_metrics = self._current_metrics.type_metrics[notification_type]
        type_metrics.total_sent += 1

        if delivery_result.status == DeliveryStatus.DELIVERED:
            type_metrics.total_delivered += 1
        elif delivery_result.status == DeliveryStatus.FAILED:
            type_metrics.total_failed += 1

    def _update_engagement_metrics(self, event_type: str) -> None:
        """Update engagement metrics with new event."""
        engagement = self._current_metrics.overall_engagement

        if event_type == "open":
            engagement.notification_opens += 1
        elif event_type == "click":
            engagement.link_clicks += 1
        elif event_type == "unsubscribe":
            engagement.unsubscribe_requests += 1
        elif event_type == "preference_change":
            engagement.preference_changes += 1
        elif event_type == "feedback":
            engagement.feedback_responses += 1

    def _calculate_period_metrics(
        self, start_time: datetime, end_time: datetime
    ) -> AnalyticsMetrics:
        """Calculate metrics for a specific time period."""
        period_deliveries = [
            event
            for event in self._delivery_history
            if start_time <= datetime.fromisoformat(event["timestamp"]) <= end_time
        ]

        period_engagement = [
            event
            for event in self._engagement_events
            if start_time <= datetime.fromisoformat(event["timestamp"]) <= end_time
        ]

        metrics = AnalyticsMetrics(start_time=start_time, end_time=end_time)

        # Calculate delivery metrics
        metrics.overall_delivery.total_sent = len(period_deliveries)
        metrics.overall_delivery.total_delivered = len(
            [event for event in period_deliveries if event["status"] == "delivered"]
        )
        metrics.overall_delivery.total_failed = len(
            [event for event in period_deliveries if event["status"] == "failed"]
        )

        # Calculate engagement metrics
        for event in period_engagement:
            self._update_engagement_metrics_for_period(
                metrics.overall_engagement, event["event_type"]
            )

        metrics.calculate_summary_metrics()
        return metrics

    def _update_engagement_metrics_for_period(
        self, engagement: EngagementMetrics, event_type: str
    ) -> None:
        """Update engagement metrics for a specific period."""
        if event_type == "open":
            engagement.notification_opens += 1
        elif event_type == "click":
            engagement.link_clicks += 1
        elif event_type == "unsubscribe":
            engagement.unsubscribe_requests += 1
        elif event_type == "preference_change":
            engagement.preference_changes += 1
        elif event_type == "feedback":
            engagement.feedback_responses += 1

    def _add_insights_and_recommendations(self, report: NotificationReport) -> None:
        """Add insights and recommendations to the report."""
        metrics = report.metrics

        # Delivery rate insights
        if metrics.overall_delivery.delivery_rate < 0.9:
            report.add_alert(f"Low delivery rate: {metrics.overall_delivery.delivery_rate:.1%}")
            report.add_recommendation("Review failed deliveries and improve channel reliability")

        if metrics.overall_delivery.delivery_rate > 0.95:
            report.add_insight("Excellent delivery rate achieved")

        # Channel performance insights
        best_channel = None
        best_rate = 0.0
        for channel, channel_metrics in metrics.channel_metrics.items():
            if channel_metrics.delivery_metrics.delivery_rate > best_rate:
                best_rate = channel_metrics.delivery_metrics.delivery_rate
                best_channel = channel

        if best_channel:
            report.add_insight(f"Best performing channel: {best_channel.value} ({best_rate:.1%})")

        # Engagement insights
        if metrics.overall_engagement.engagement_rate > 0.1:
            report.add_insight("Good user engagement with notifications")
        elif metrics.overall_engagement.engagement_rate < 0.05:
            report.add_recommendation(
                "Consider improving notification content to increase engagement"
            )

    def _get_channel_breakdown(self) -> Dict[str, Dict[str, int]]:
        """Get breakdown of deliveries by channel."""
        breakdown = {}
        for event in self._delivery_history:
            channel = event["channel"]
            if channel not in breakdown:
                breakdown[channel] = {"sent": 0, "delivered": 0, "failed": 0}

            breakdown[channel]["sent"] += 1
            if event["status"] == "delivered":
                breakdown[channel]["delivered"] += 1
            elif event["status"] == "failed":
                breakdown[channel]["failed"] += 1

        return breakdown

    def _save_report(self, report: NotificationReport) -> None:
        """Save report to storage."""
        try:
            report_file = self.storage_path / f"report_{report.report_id}.json"
            with open(report_file, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            logger.info(f"Report saved to {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
