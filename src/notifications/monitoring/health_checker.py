"""Health checker for notification system monitoring."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .models import NotificationHealthStatus

logger = logging.getLogger(__name__)


class NotificationHealthChecker:
    """Health checker for notification system components."""

    def __init__(self, delivery_monitor: Any = None) -> None:
        """Initialize health checker.

        Args:
            delivery_monitor: DeliveryMonitor instance for health checks
        """
        self.delivery_monitor = delivery_monitor
        self.health_thresholds = {
            "success_rate_threshold": 0.95,
            "max_retry_queue_size": 100,
            "max_dead_letter_size": 50,
            "max_avg_delivery_time_ms": 5000,
            "min_notifications_for_stats": 10,
        }

        logger.info("Notification health checker initialized")

    def check_overall_health(self) -> NotificationHealthStatus:
        """Check overall health of notification system.

        Returns:
            NotificationHealthStatus with comprehensive health information
        """
        issues = []
        stats = {}

        try:
            # Check delivery monitor health if available
            if self.delivery_monitor:
                delivery_health = self._check_delivery_health()
                issues.extend(delivery_health["issues"])
                stats.update(delivery_health["stats"])

            # Check system resources
            resource_health = self._check_system_resources()
            issues.extend(resource_health["issues"])
            stats.update(resource_health["stats"])

            # Determine overall status
            if not issues:
                status = "healthy"
            elif len(issues) <= 2:
                status = "degraded"
            else:
                status = "unhealthy"

            return NotificationHealthStatus(
                status=status, issues=issues, last_check=datetime.utcnow(), stats=stats
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return NotificationHealthStatus(
                status="unhealthy",
                issues=[f"Health check failed: {str(e)}"],
                last_check=datetime.utcnow(),
                stats={"error": str(e)},
            )

    def _check_delivery_health(self) -> Dict[str, Any]:
        """Check delivery system health.

        Returns:
            Dictionary with delivery health information
        """
        issues = []
        stats = {}

        try:
            # Get delivery statistics
            delivery_stats = self.delivery_monitor.get_delivery_stats(1)  # Last hour
            stats["delivery"] = delivery_stats

            # Check success rate
            success_rate = delivery_stats.get("success_rate", 0)
            if success_rate < self.health_thresholds["success_rate_threshold"]:
                if (
                    delivery_stats.get("total_notifications", 0)
                    >= self.health_thresholds["min_notifications_for_stats"]
                ):
                    issues.append(f"Low delivery success rate: {success_rate:.2%}")

            # Check retry queue size
            retry_queue_size = delivery_stats.get("retry_queue_size", 0)
            if retry_queue_size > self.health_thresholds["max_retry_queue_size"]:
                issues.append(f"High retry queue size: {retry_queue_size}")

            # Check dead letter queue size
            dead_letter_size = delivery_stats.get("dead_letter_queue_size", 0)
            if dead_letter_size > self.health_thresholds["max_dead_letter_size"]:
                issues.append(f"High dead letter queue size: {dead_letter_size}")

            # Check average delivery time
            avg_delivery_time = delivery_stats.get("average_delivery_time_ms", 0)
            if avg_delivery_time > self.health_thresholds["max_avg_delivery_time_ms"]:
                issues.append(f"High average delivery time: {avg_delivery_time:.0f}ms")

            # Check channel-specific health
            channel_issues = self._check_channel_health(delivery_stats.get("by_channel", {}))
            issues.extend(channel_issues)

        except Exception as e:
            logger.error(f"Delivery health check failed: {e}")
            issues.append(f"Delivery health check failed: {str(e)}")

        return {"issues": issues, "stats": stats}

    def _check_channel_health(self, channel_stats: Dict[str, Any]) -> List[str]:
        """Check health of individual channels.

        Args:
            channel_stats: Statistics by channel

        Returns:
            List of channel-specific health issues
        """
        issues = []

        for channel, stats in channel_stats.items():
            success_rate = stats.get("success_rate", 0)
            total_notifications = stats.get("total", 0)

            # Only check channels with sufficient activity
            if total_notifications >= self.health_thresholds["min_notifications_for_stats"]:
                if success_rate < self.health_thresholds["success_rate_threshold"]:
                    issues.append(f"Channel '{channel}' has low success rate: {success_rate:.2%}")

        return issues

    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource health.

        Returns:
            Dictionary with system resource health information
        """
        issues = []
        stats = {}

        try:
            import psutil

            # Check memory usage
            memory = psutil.virtual_memory()
            stats["memory_usage_percent"] = memory.percent

            if memory.percent > 90:
                issues.append(f"High memory usage: {memory.percent:.1f}%")
            elif memory.percent > 80:
                issues.append(f"Elevated memory usage: {memory.percent:.1f}%")

            # Check disk usage for data directory
            disk = psutil.disk_usage("/")
            stats["disk_usage_percent"] = (disk.used / disk.total) * 100

            if stats["disk_usage_percent"] > 95:
                issues.append(f"Critical disk usage: {stats['disk_usage_percent']:.1f}%")
            elif stats["disk_usage_percent"] > 85:
                issues.append(f"High disk usage: {stats['disk_usage_percent']:.1f}%")

        except ImportError:
            # psutil not available
            stats["system_monitoring"] = "unavailable"
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            issues.append(f"System resource check failed: {str(e)}")

        return {"issues": issues, "stats": stats}

    def check_channel_connectivity(self, channel_configs: Dict[str, Any]) -> Dict[str, Any]:
        """Check connectivity to notification channels.

        Args:
            channel_configs: Configuration for each channel

        Returns:
            Dictionary with connectivity test results
        """
        results = {}

        for channel, config in channel_configs.items():
            try:
                if channel.lower() == "email":
                    results[channel] = self._test_email_connectivity(config)
                elif channel.lower() == "discord":
                    results[channel] = self._test_discord_connectivity(config)
                elif channel.lower() == "webhook":
                    results[channel] = self._test_webhook_connectivity(config)
                else:
                    results[channel] = {
                        "status": "unknown",
                        "message": "Unknown channel type",
                    }
            except Exception as e:
                logger.error(f"Connectivity test failed for {channel}: {e}")
                results[channel] = {"status": "error", "message": str(e)}

        return results

    def _test_email_connectivity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test email server connectivity.

        Args:
            config: Email configuration

        Returns:
            Connectivity test result
        """
        try:
            # Basic configuration check
            required_fields = ["smtp_server", "smtp_port", "username"]
            missing_fields = [field for field in required_fields if not config.get(field)]

            if missing_fields:
                return {
                    "status": "error",
                    "message": f"Missing configuration: {', '.join(missing_fields)}",
                }

            # TODO: Implement actual SMTP connectivity test
            return {"status": "ok", "message": "Email configuration appears valid"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _test_discord_connectivity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Discord webhook connectivity.

        Args:
            config: Discord configuration

        Returns:
            Connectivity test result
        """
        try:
            webhook_url = config.get("webhook_url")
            if not webhook_url:
                return {"status": "error", "message": "Missing webhook_url"}

            # TODO: Implement actual Discord webhook test
            return {
                "status": "ok",
                "message": "Discord webhook configuration appears valid",
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _test_webhook_connectivity(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test generic webhook connectivity.

        Args:
            config: Webhook configuration

        Returns:
            Connectivity test result
        """
        try:
            url = config.get("url")
            if not url:
                return {"status": "error", "message": "Missing webhook URL"}

            # TODO: Implement actual webhook connectivity test
            return {"status": "ok", "message": "Webhook configuration appears valid"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_health_thresholds(self, new_thresholds: Dict[str, Any]) -> None:
        """Update health check thresholds.

        Args:
            new_thresholds: New threshold values
        """
        self.health_thresholds.update(new_thresholds)
        logger.info(f"Updated health thresholds: {new_thresholds}")

    def get_health_thresholds(self) -> Dict[str, Any]:
        """Get current health check thresholds.

        Returns:
            Current threshold configuration
        """
        return self.health_thresholds.copy()
