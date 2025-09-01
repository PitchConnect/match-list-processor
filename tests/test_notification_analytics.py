"""Tests for notification analytics system."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from src.notifications.analytics.analytics_service import NotificationAnalyticsService
from src.notifications.analytics.metrics_models import (
    AnalyticsMetrics,
    ChannelMetrics,
    DeliveryMetrics,
)
from src.notifications.models.notification_models import (
    DeliveryResult,
    DeliveryStatus,
    NotificationChannel,
)


class TestMetricsModels(unittest.TestCase):
    """Test metrics models."""

    def test_delivery_metrics_creation(self):
        """Test delivery metrics creation and calculation."""
        metrics = DeliveryMetrics()
        metrics.total_sent = 100
        metrics.total_delivered = 85
        metrics.total_failed = 10
        metrics.total_pending = 5

        metrics.calculate_rates()

        self.assertEqual(metrics.delivery_rate, 0.85)
        self.assertEqual(metrics.failure_rate, 0.10)

        # Test dictionary conversion
        metrics_dict = metrics.to_dict()
        self.assertEqual(metrics_dict["total_sent"], 100)
        self.assertEqual(metrics_dict["delivery_rate"], 0.85)

    def test_channel_metrics_creation(self):
        """Test channel metrics creation."""
        delivery_metrics = DeliveryMetrics()
        delivery_metrics.total_sent = 50
        delivery_metrics.total_delivered = 45

        channel_metrics = ChannelMetrics(
            channel=NotificationChannel.EMAIL, delivery_metrics=delivery_metrics
        )

        self.assertEqual(channel_metrics.channel, NotificationChannel.EMAIL)
        self.assertEqual(channel_metrics.delivery_metrics.total_sent, 50)

        # Test dictionary conversion
        metrics_dict = channel_metrics.to_dict()
        self.assertEqual(metrics_dict["channel"], "email")
        self.assertEqual(metrics_dict["delivery_metrics"]["total_sent"], 50)

    def test_analytics_metrics_creation(self):
        """Test analytics metrics creation."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        metrics = AnalyticsMetrics(start_time=start_time, end_time=end_time)

        self.assertEqual(metrics.start_time, start_time)
        self.assertEqual(metrics.end_time, end_time)
        self.assertEqual(metrics.period_duration, timedelta(hours=1))

        # Test dictionary conversion
        metrics_dict = metrics.to_dict()
        self.assertIn("period", metrics_dict)
        self.assertEqual(metrics_dict["period"]["duration_hours"], 1.0)


class TestNotificationAnalyticsService(unittest.TestCase):
    """Test notification analytics service."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.analytics = NotificationAnalyticsService(self.temp_dir)

    def test_service_initialization(self):
        """Test analytics service initialization."""
        self.assertIsInstance(self.analytics, NotificationAnalyticsService)
        self.assertEqual(len(self.analytics._delivery_history), 0)
        self.assertEqual(len(self.analytics._engagement_events), 0)

    def test_track_delivery_success(self):
        """Test tracking successful delivery."""
        delivery_result = DeliveryResult(
            recipient_id="test-123",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            message="Email sent successfully",
        )

        self.analytics.track_delivery(delivery_result, "new_assignment")

        # Check delivery history
        self.assertEqual(len(self.analytics._delivery_history), 1)
        event = self.analytics._delivery_history[0]
        self.assertEqual(event["recipient_id"], "test-123")
        self.assertEqual(event["channel"], "email")
        self.assertEqual(event["status"], "delivered")
        self.assertEqual(event["notification_type"], "new_assignment")

        # Check current metrics
        current_metrics = self.analytics.get_current_metrics()
        self.assertEqual(current_metrics.overall_delivery.total_sent, 1)
        self.assertEqual(current_metrics.overall_delivery.total_delivered, 1)
        self.assertEqual(current_metrics.overall_delivery.total_failed, 0)

    def test_track_delivery_failure(self):
        """Test tracking failed delivery."""
        delivery_result = DeliveryResult(
            recipient_id="test-456",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.FAILED,
            message="SMTP connection failed",
            error_details="Connection timeout",
        )

        self.analytics.track_delivery(delivery_result, "time_change")

        # Check current metrics
        current_metrics = self.analytics.get_current_metrics()
        self.assertEqual(current_metrics.overall_delivery.total_sent, 1)
        self.assertEqual(current_metrics.overall_delivery.total_delivered, 0)
        self.assertEqual(current_metrics.overall_delivery.total_failed, 1)

    def test_track_multiple_deliveries(self):
        """Test tracking multiple deliveries."""
        # Track successful email delivery
        email_result = DeliveryResult(
            recipient_id="email-123",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            message="Email sent",
        )
        self.analytics.track_delivery(email_result, "new_assignment")

        # Track successful Discord delivery
        discord_result = DeliveryResult(
            recipient_id="discord-456",
            channel=NotificationChannel.DISCORD,
            status=DeliveryStatus.DELIVERED,
            message="Discord sent",
        )
        self.analytics.track_delivery(discord_result, "time_change")

        # Track failed webhook delivery
        webhook_result = DeliveryResult(
            recipient_id="webhook-789",
            channel=NotificationChannel.WEBHOOK,
            status=DeliveryStatus.FAILED,
            message="Webhook failed",
        )
        self.analytics.track_delivery(webhook_result, "venue_change")

        # Check overall metrics
        current_metrics = self.analytics.get_current_metrics()
        self.assertEqual(current_metrics.overall_delivery.total_sent, 3)
        self.assertEqual(current_metrics.overall_delivery.total_delivered, 2)
        self.assertEqual(current_metrics.overall_delivery.total_failed, 1)

        # Check channel metrics
        self.assertIn(NotificationChannel.EMAIL, current_metrics.channel_metrics)
        self.assertIn(NotificationChannel.DISCORD, current_metrics.channel_metrics)
        self.assertIn(NotificationChannel.WEBHOOK, current_metrics.channel_metrics)

        email_metrics = current_metrics.channel_metrics[NotificationChannel.EMAIL]
        self.assertEqual(email_metrics.delivery_metrics.total_sent, 1)
        self.assertEqual(email_metrics.delivery_metrics.total_delivered, 1)

    def test_track_engagement(self):
        """Test tracking user engagement."""
        self.analytics.track_engagement("notif-123", "user-456", "open")
        self.analytics.track_engagement("notif-123", "user-456", "click", {"link": "calendar"})
        self.analytics.track_engagement("notif-456", "user-789", "unsubscribe")

        # Check engagement events
        self.assertEqual(len(self.analytics._engagement_events), 3)

        # Check engagement metrics
        current_metrics = self.analytics.get_current_metrics()
        self.assertEqual(current_metrics.overall_engagement.notification_opens, 1)
        self.assertEqual(current_metrics.overall_engagement.link_clicks, 1)
        self.assertEqual(current_metrics.overall_engagement.unsubscribe_requests, 1)

    def test_get_channel_performance(self):
        """Test getting channel performance metrics."""
        # Add some test deliveries
        for i in range(5):
            result = DeliveryResult(
                recipient_id=f"email-{i}",
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.DELIVERED if i < 4 else DeliveryStatus.FAILED,
                message="Test delivery",
            )
            self.analytics.track_delivery(result, "test")

        # Get email channel performance
        email_performance = self.analytics.get_channel_performance(NotificationChannel.EMAIL)

        self.assertEqual(email_performance.channel, NotificationChannel.EMAIL)
        self.assertEqual(email_performance.delivery_metrics.total_sent, 5)
        self.assertEqual(email_performance.delivery_metrics.total_delivered, 4)
        self.assertEqual(email_performance.delivery_metrics.total_failed, 1)
        self.assertEqual(email_performance.active_recipients, 5)

    def test_get_delivery_statistics(self):
        """Test getting delivery statistics."""
        # Initially empty
        stats = self.analytics.get_delivery_statistics()
        self.assertEqual(stats["total_deliveries"], 0)

        # Add some deliveries
        for i in range(10):
            result = DeliveryResult(
                recipient_id=f"test-{i}",
                channel=NotificationChannel.EMAIL if i < 7 else NotificationChannel.DISCORD,
                status=DeliveryStatus.DELIVERED if i < 8 else DeliveryStatus.FAILED,
                message="Test",
            )
            self.analytics.track_delivery(result, "test")

        stats = self.analytics.get_delivery_statistics()
        self.assertEqual(stats["total_deliveries"], 10)
        self.assertEqual(stats["successful_deliveries"], 8)
        self.assertEqual(stats["failed_deliveries"], 2)
        self.assertEqual(stats["delivery_rate"], 0.8)
        self.assertEqual(stats["failure_rate"], 0.2)

        # Check channel breakdown
        self.assertIn("channels", stats)
        self.assertIn("email", stats["channels"])
        self.assertIn("discord", stats["channels"])

    def test_generate_report(self):
        """Test generating analytics report."""
        # Add some test data
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)

        # Add deliveries
        for i in range(5):
            result = DeliveryResult(
                recipient_id=f"test-{i}",
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.DELIVERED,
                message="Test",
            )
            self.analytics.track_delivery(result, "test")

        # Add engagement
        self.analytics.track_engagement("test-1", "user-1", "open")
        self.analytics.track_engagement("test-2", "user-2", "click")

        # Generate report
        report = self.analytics.generate_report(start_time, end_time, "test_report")

        self.assertIsNotNone(report.report_id)
        self.assertEqual(report.report_type, "test_report")
        self.assertIsInstance(report.metrics, AnalyticsMetrics)

        # Check that insights and recommendations are added
        self.assertGreaterEqual(len(report.insights), 0)

        # Test report dictionary conversion
        report_dict = report.to_dict()
        self.assertIn("report_id", report_dict)
        self.assertIn("metrics", report_dict)
        self.assertIn("insights", report_dict)

    def test_reset_metrics(self):
        """Test resetting metrics."""
        # Add some data
        result = DeliveryResult(
            recipient_id="test",
            channel=NotificationChannel.EMAIL,
            status=DeliveryStatus.DELIVERED,
            message="Test",
        )
        self.analytics.track_delivery(result, "test")
        self.analytics.track_engagement("test", "user", "open")

        # Verify data exists
        self.assertEqual(len(self.analytics._delivery_history), 1)
        self.assertEqual(len(self.analytics._engagement_events), 1)

        # Reset
        self.analytics.reset_metrics()

        # Verify data is cleared
        self.assertEqual(len(self.analytics._delivery_history), 0)
        self.assertEqual(len(self.analytics._engagement_events), 0)

        current_metrics = self.analytics.get_current_metrics()
        self.assertEqual(current_metrics.overall_delivery.total_sent, 0)


if __name__ == "__main__":
    unittest.main()
