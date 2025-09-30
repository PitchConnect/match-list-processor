#!/usr/bin/env python3
"""
Redis Publisher for Match List Processor

Provides Redis publishing functionality for match updates and status messages.
"""

import json
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

    def _log_message_details(
        self, channel: str, message: str, subscribers: int, message_type: str = "match_updates"
    ) -> None:
        """
        Log detailed information about a Redis message.

        Args:
            channel: Redis channel name
            message: JSON message string
            subscribers: Number of subscribers notified
            message_type: Type of message being published
        """
        try:
            # Parse message for logging
            message_data = json.loads(message)

            # Log message details at INFO level
            logger.info("📨 PUBLISHING MESSAGE:")
            logger.info(f"   Channel: {channel}")
            logger.info(f"   Message ID: {message_data.get('message_id', 'N/A')}")

            # Log payload details
            payload = message_data.get("payload", {})
            if "matches" in payload:
                match_count = len(payload["matches"])
                logger.info(f"   Matches: {match_count} match(es)")

            if "detailed_changes" in payload:
                changes_count = len(payload["detailed_changes"])
                logger.info(f"   Detailed Changes: {changes_count} change(s)")

            logger.info(f"   Subscribers: {subscribers}")

            # Log full message at debug level
            logger.debug(f"   Full Message: {json.dumps(message_data, indent=2)}")

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Could not parse message for detailed logging: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Error logging message details: {e}")

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

            # Log detailed message information (Issue #68)
            self._log_message_details(self.config.match_updates_channel, message, subscribers)

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

            # Log detailed message information (Issue #68)
            self._log_message_details("match_updates_v2", message, subscribers, "enhanced_v2")

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
            v2_subs_count = int(v2_subscribers) if not hasattr(v2_subscribers, "__await__") else 0
            results["v2.0"] = PublishResult(success=True, subscribers_notified=v2_subs_count)

            # Log detailed message information for v2.0 (Issue #68)
            self._log_message_details("match_updates_v2", v2_message, v2_subs_count, "enhanced_v2")

            # Publish to default channel (Enhanced Schema v2.0)
            default_subscribers = client.publish(self.config.match_updates_channel, v2_message)
            default_subs_count = (
                int(default_subscribers) if not hasattr(default_subscribers, "__await__") else 0
            )
            results["default"] = PublishResult(
                success=True, subscribers_notified=default_subs_count
            )

            # Log detailed message information for default channel (Issue #68)
            self._log_message_details(
                self.config.match_updates_channel, v2_message, default_subs_count, "default"
            )

            # Publish Legacy Schema v1.0 for backward compatibility
            v1_message = EnhancedSchemaV2Formatter.format_match_updates_v1_legacy(
                matches, changes_summary, metadata
            )
            v1_subscribers = client.publish("match_updates_v1", v1_message)
            v1_subs_count = int(v1_subscribers) if not hasattr(v1_subscribers, "__await__") else 0
            results["v1.0_legacy"] = PublishResult(success=True, subscribers_notified=v1_subs_count)

            # Log detailed message information for v1.0 legacy (Issue #68)
            self._log_message_details("match_updates_v1", v1_message, v1_subs_count, "legacy_v1")

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

            # Log detailed message information (Issue #68)
            self._log_message_details(
                self.config.processor_status_channel, message, subscribers, "processing_status"
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
