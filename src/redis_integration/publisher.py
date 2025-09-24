#!/usr/bin/env python3
"""
Redis Publisher for Match List Processor

Provides Redis publishing functionality for match updates and status messages.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .connection_manager import RedisConnectionManager
from .message_formatter import MatchUpdateMessageFormatter, ProcessingStatusMessageFormatter

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a Redis publish operation."""

    success: bool
    subscribers_notified: int = 0
    error: Optional[str] = None


class MatchProcessorRedisPublisher:
    """Redis publisher for match processor events."""

    def __init__(self):
        """Initialize Redis publisher."""
        self.connection_manager = RedisConnectionManager()
        self.config = self.connection_manager.config
        self.stats = {
            "total_published": 0,
            "successful_publishes": 0,
            "failed_publishes": 0,
            "last_publish_time": None,
        }

    def publish_match_updates(
        self, matches: List[Dict], changes: Dict, metadata: Dict = None
    ) -> PublishResult:
        """
        Publish match updates to Redis channel.

        Args:
            matches: List of match dictionaries
            changes: Change detection results
            metadata: Additional processing metadata

        Returns:
            PublishResult: Publishing result
        """
        if not self.config.enabled:
            return PublishResult(success=True, subscribers_notified=0)

        client = self.connection_manager.get_client()
        if client is None:
            error = "Redis client not available"
            logger.warning(f"⚠️ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

        try:
            message = MatchUpdateMessageFormatter.format_match_updates(matches, changes, metadata)
            subscribers = client.publish(self.config.match_updates_channel, message)

            self.stats["total_published"] += 1
            self.stats["successful_publishes"] += 1
            self.stats["last_publish_time"] = message

            logger.info(f"✅ Published match updates to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish match updates: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

    def publish_processing_status(self, status: str, details: Dict = None) -> PublishResult:
        """
        Publish processing status to Redis channel.

        Args:
            status: Processing status (started, completed, failed)
            details: Additional processing details

        Returns:
            PublishResult: Publishing result
        """
        if not self.config.enabled:
            return PublishResult(success=True, subscribers_notified=0)

        client = self.connection_manager.get_client()
        if client is None:
            error = "Redis client not available"
            logger.warning(f"⚠️ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

        try:
            message = ProcessingStatusMessageFormatter.format_processing_status(status, details)
            subscribers = client.publish(self.config.processor_status_channel, message)

            self.stats["total_published"] += 1
            self.stats["successful_publishes"] += 1

            logger.info(f"✅ Published processing status '{status}' to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish processing status: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

    def publish_system_alert(
        self, alert_type: str, message: str, severity: str = "info", details: Dict = None
    ) -> PublishResult:
        """
        Publish system alert to Redis channel.

        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, error)
            details: Additional alert details

        Returns:
            PublishResult: Publishing result
        """
        if not self.config.enabled:
            return PublishResult(success=True, subscribers_notified=0)

        client = self.connection_manager.get_client()
        if client is None:
            error = "Redis client not available"
            logger.warning(f"⚠️ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

        try:
            alert_message = ProcessingStatusMessageFormatter.format_system_alert(
                alert_type, message, severity, details
            )
            subscribers = client.publish(self.config.system_alerts_channel, alert_message)

            self.stats["total_published"] += 1
            self.stats["successful_publishes"] += 1

            logger.info(f"✅ Published system alert '{alert_type}' to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish system alert: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] += 1
            return PublishResult(success=False, error=error)

    def get_publishing_stats(self) -> Dict:
        """Get publishing statistics."""
        return {
            "redis_enabled": self.config.enabled,
            "redis_connected": self.connection_manager.is_connected(),
            "publishing_stats": self.stats.copy(),
        }
