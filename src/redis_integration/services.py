#!/usr/bin/env python3
"""
Redis Service for Match List Processor

High-level Redis service for match processor integration.
"""

import logging
from typing import Dict, List, Optional

from .publisher import MatchProcessorRedisPublisher

logger = logging.getLogger(__name__)


class MatchProcessorRedisService:
    """High-level Redis service for match processor."""

    def __init__(self) -> None:
        """Initialize Redis service."""
        self.publisher = MatchProcessorRedisPublisher()

    def handle_processing_start(self, details: Optional[Dict] = None) -> bool:
        """
        Handle processing start event.

        Args:
            details: Processing start details

        Returns:
            bool: True if successful
        """
        result = self.publisher.publish_processing_status("started", details)
        return result.success

    def handle_match_processing_complete(
        self, matches: List[Dict], changes: Dict, details: Optional[Dict] = None
    ) -> bool:
        """
        Handle match processing completion.

        Args:
            matches: Processed matches
            changes: Change detection results
            details: Additional processing details

        Returns:
            bool: True if successful
        """
        # Publish match updates
        match_result = self.publisher.publish_match_updates(matches, changes, details)

        # Publish processing completion status
        status_details = {
            "matches_processed": len(matches),
            "changes_detected": bool(changes),
            "match_publishing_success": match_result.success,
            **(details or {}),
        }
        status_result = self.publisher.publish_processing_status("completed", status_details)

        return match_result.success and status_result.success

    def handle_processing_error(self, error: Exception, details: Optional[Dict] = None) -> bool:
        """
        Handle processing error.

        Args:
            error: Processing error
            details: Additional error details

        Returns:
            bool: True if successful
        """
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(details or {}),
        }

        # Publish processing error status
        status_result = self.publisher.publish_processing_status("failed", error_details)

        # Publish system alert
        alert_result = self.publisher.publish_system_alert(
            "processing_error", f"Match processing failed: {error}", "error", error_details
        )

        return status_result.success and alert_result.success

    def get_redis_status(self) -> Dict:
        """
        Get Redis service status.

        Returns:
            Dict: Redis service status
        """
        publisher_stats = self.publisher.get_publishing_stats()

        return {
            "redis_service": {
                "status": "connected" if publisher_stats["redis_connected"] else "disconnected",
                "enabled": publisher_stats["redis_enabled"],
                "publishing_stats": publisher_stats["publishing_stats"],
            }
        }
