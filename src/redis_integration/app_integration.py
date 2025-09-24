#!/usr/bin/env python3
"""
Application Integration for Redis Publishing

Provides integration helpers for adding Redis publishing to the match processor.
"""

import logging
from typing import Any

from .services import MatchProcessorRedisService

logger = logging.getLogger(__name__)


def add_redis_integration_to_processor(processor: Any) -> None:
    """
    Add Redis integration to a match processor instance.

    Args:
        processor: Match processor instance to enhance with Redis integration
    """
    # Add Redis service to processor
    processor.redis_integration = MatchProcessorRedisService()

    # Store original processing method
    if hasattr(processor, "_process_matches_sync"):
        processor._original_process_matches_sync = processor._process_matches_sync

        def enhanced_process_matches_sync():
            """Enhanced processing method with Redis integration."""
            try:
                # Publish processing start
                processor.redis_integration.handle_processing_start(
                    {"processor_type": type(processor).__name__}
                )

                # Call original processing method
                result = processor._original_process_matches_sync()

                # Extract matches and changes from result if available
                matches = getattr(result, "matches", []) if result else []
                changes = getattr(result, "changes", {}) if result else {}

                # Publish completion
                processor.redis_integration.handle_match_processing_complete(
                    matches, changes, {"processor_type": type(processor).__name__}
                )

                return result

            except Exception as e:
                # Publish error
                processor.redis_integration.handle_processing_error(
                    e, {"processor_type": type(processor).__name__}
                )
                raise

        # Replace processing method
        processor._process_matches_sync = enhanced_process_matches_sync

        logger.info("✅ Redis integration added to match processor")
    else:
        logger.warning("⚠️ Could not find _process_matches_sync method to enhance")


def create_redis_service() -> MatchProcessorRedisService:
    """
    Create a standalone Redis service instance.

    Returns:
        MatchProcessorRedisService: Redis service instance
    """
    return MatchProcessorRedisService()
