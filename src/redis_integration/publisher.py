#!/usr/bin/env python3
"""
Redis Publisher for Match List Processor

Provides Redis publishing functionality for match updates and status messages.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .connection_manager import RedisConnectionManager
from .message_formatter import (
    EnhancedSchemaV2Formatter,
    MatchUpdateMessageFormatter,
    ProcessingStatusMessageFormatter,
)

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """Result of a Redis publish operation."""

    success: bool
    subscribers_notified: int = 0
    error: Optional[str] = None


class MatchProcessorRedisPublisher:
    """Redis publisher for match processor events."""

    def __init__(self) -> None:
        """Initialize Redis publisher."""
        self.connection_manager = RedisConnectionManager()
        self.config = self.connection_manager.config
        self.stats: Dict[str, Any] = {
            "total_published": 0,
            "successful_publishes": 0,
            "failed_publishes": 0,
            "last_publish_time": None,
        }

    def publish_match_updates(
        self, matches: List[Dict], changes: Dict, metadata: Optional[Dict] = None
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
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

        try:
            message = MatchUpdateMessageFormatter.format_match_updates(matches, changes, metadata)
            subscribers_result = client.publish(self.config.match_updates_channel, message)
            # Handle both sync and async redis client return types
            subscribers = (
                int(subscribers_result) if not hasattr(subscribers_result, "__await__") else 0
            )

            self.stats["total_published"] = self.stats.get("total_published", 0) + 1
            self.stats["successful_publishes"] = self.stats.get("successful_publishes", 0) + 1
            self.stats["last_publish_time"] = message

            logger.info(f"✅ Published match updates to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish match updates: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

    def publish_enhanced_schema_v2(
        self,
        matches: List[Dict],
        changes_summary: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> PublishResult:
        """
        Publish match updates using Enhanced Schema v2.0 with Organization ID mapping.

        Args:
            matches: List of FOGIS match objects
            changes_summary: Change detection results with detailed_changes
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
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

        try:
            # Format Enhanced Schema v2.0 message
            message = EnhancedSchemaV2Formatter.format_match_updates_v2(
                matches, changes_summary, metadata
            )

            # Publish to Enhanced Schema v2.0 channel
            subscribers_result = client.publish("match_updates_v2", message)
            subscribers = (
                int(subscribers_result) if not hasattr(subscribers_result, "__await__") else 0
            )

            self.stats["total_published"] = self.stats.get("total_published", 0) + 1
            self.stats["successful_publishes"] = self.stats.get("successful_publishes", 0) + 1
            self.stats["last_publish_time"] = message

            logger.info(f"✅ Published Enhanced Schema v2.0 to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish Enhanced Schema v2.0: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

    def publish_multi_version_updates(
        self,
        matches: List[Dict],
        changes_summary: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, PublishResult]:
        """
        Publish match updates in multiple schema versions for backward compatibility.

        Args:
            matches: List of FOGIS match objects
            changes_summary: Change detection results
            metadata: Additional processing metadata

        Returns:
            Dict[str, PublishResult]: Results for each schema version
        """
        results = {}

        if not self.config.enabled:
            return {
                "v2.0": PublishResult(success=True, subscribers_notified=0),
                "v1.0_legacy": PublishResult(success=True, subscribers_notified=0),
                "default": PublishResult(success=True, subscribers_notified=0),
            }

        client = self.connection_manager.get_client()
        if client is None:
            error = "Redis client not available"
            logger.warning(f"⚠️ {error}")
            failed_result = PublishResult(success=False, error=error)
            return {
                "v2.0": failed_result,
                "v1.0_legacy": failed_result,
                "default": failed_result,
            }

        try:
            # Publish Enhanced Schema v2.0
            v2_message = EnhancedSchemaV2Formatter.format_match_updates_v2(
                matches, changes_summary, metadata
            )
            v2_subscribers = client.publish("match_updates_v2", v2_message)
            results["v2.0"] = PublishResult(
                success=True,
                subscribers_notified=(
                    int(v2_subscribers) if not hasattr(v2_subscribers, "__await__") else 0
                ),
            )

            # Publish to default channel (Enhanced Schema v2.0)
            default_subscribers = client.publish(self.config.match_updates_channel, v2_message)
            results["default"] = PublishResult(
                success=True,
                subscribers_notified=(
                    int(default_subscribers) if not hasattr(default_subscribers, "__await__") else 0
                ),
            )

            # Publish Legacy Schema v1.0 for backward compatibility
            v1_message = EnhancedSchemaV2Formatter.format_match_updates_v1_legacy(
                matches, changes_summary, metadata
            )
            v1_subscribers = client.publish("match_updates_v1", v1_message)
            results["v1.0_legacy"] = PublishResult(
                success=True,
                subscribers_notified=(
                    int(v1_subscribers) if not hasattr(v1_subscribers, "__await__") else 0
                ),
            )

            # Update stats
            self.stats["total_published"] = self.stats.get("total_published", 0) + 3
            self.stats["successful_publishes"] = self.stats.get("successful_publishes", 0) + 3

            total_subscribers = sum(result.subscribers_notified for result in results.values())
            logger.info(
                f"✅ Published multi-version updates to {total_subscribers} total subscribers"
            )
            logger.info(
                f"   - Enhanced Schema v2.0: {results['v2.0'].subscribers_notified} subscribers"
            )
            logger.info(
                f"   - Legacy Schema v1.0: {results['v1.0_legacy'].subscribers_notified} subscribers"
            )

        except Exception as e:
            error = f"Failed to publish multi-version updates: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            failed_result = PublishResult(success=False, error=error)
            results = {
                "v2.0": failed_result,
                "v1.0_legacy": failed_result,
                "default": failed_result,
            }

        return results

    def publish_processing_status(
        self, status: str, details: Optional[Dict] = None
    ) -> PublishResult:
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
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

        try:
            message = ProcessingStatusMessageFormatter.format_processing_status(status, details)
            subscribers_result = client.publish(self.config.processor_status_channel, message)
            # Handle both sync and async redis client return types
            subscribers = (
                int(subscribers_result) if not hasattr(subscribers_result, "__await__") else 0
            )

            self.stats["total_published"] = self.stats.get("total_published", 0) + 1
            self.stats["successful_publishes"] = self.stats.get("successful_publishes", 0) + 1

            logger.info(f"✅ Published processing status '{status}' to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish processing status: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

    def publish_system_alert(
        self, alert_type: str, message: str, severity: str = "info", details: Optional[Dict] = None
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
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

        try:
            alert_message = ProcessingStatusMessageFormatter.format_system_alert(
                alert_type, message, severity, details
            )
            subscribers_result = client.publish(self.config.system_alerts_channel, alert_message)
            # Handle both sync and async redis client return types
            subscribers = (
                int(subscribers_result) if not hasattr(subscribers_result, "__await__") else 0
            )

            self.stats["total_published"] = self.stats.get("total_published", 0) + 1
            self.stats["successful_publishes"] = self.stats.get("successful_publishes", 0) + 1

            logger.info(f"✅ Published system alert '{alert_type}' to {subscribers} subscribers")
            return PublishResult(success=True, subscribers_notified=subscribers)

        except Exception as e:
            error = f"Failed to publish system alert: {e}"
            logger.error(f"❌ {error}")
            self.stats["failed_publishes"] = self.stats.get("failed_publishes", 0) + 1
            return PublishResult(success=False, error=error)

    def get_publishing_stats(self) -> Dict:
        """Get publishing statistics."""
        return {
            "redis_enabled": self.config.enabled,
            "redis_connected": self.connection_manager.is_connected(),
            "publishing_stats": self.stats.copy(),
        }
