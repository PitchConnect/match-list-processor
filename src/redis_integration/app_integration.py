#!/usr/bin/env python3
"""
Application Integration for Redis Publishing

Provides integration helpers for adding Redis publishing to the match processor.
"""

import logging
from typing import Any, Dict, List, Optional

from .services import MatchProcessorRedisService

logger = logging.getLogger(__name__)


def add_redis_integration_to_processor(processor: Any) -> None:
    """
    Add Redis integration to a match processor instance.

    Supports both UnifiedMatchProcessor (with run_processing_cycle) and
    legacy processors (with _process_matches_sync).

    Args:
        processor: Match processor instance to enhance with Redis integration
    """
    # Add Redis service to processor
    processor.redis_integration = MatchProcessorRedisService()

    # Hook into UnifiedMatchProcessor's run_processing_cycle method
    if hasattr(processor, "run_processing_cycle"):
        processor._original_run_processing_cycle = processor.run_processing_cycle

        def enhanced_run_processing_cycle() -> Any:
            """Enhanced processing cycle with Redis integration."""
            try:
                # Publish processing start
                processor.redis_integration.handle_processing_start(
                    {"processor_type": type(processor).__name__}
                )

                # Call original processing method
                result = processor._original_run_processing_cycle()

                # Extract data from ProcessingResult
                # ProcessingResult has: processed, changes (ChangesSummary), processing_time, errors
                if result and result.processed:
                    # Get matches from the change detector's current state
                    matches = []
                    if hasattr(processor, "change_detector"):
                        try:
                            # Load the current matches that were just saved
                            matches = processor.change_detector.load_current_matches()
                        except Exception as e:
                            logger.warning(f"Could not load matches for Redis publishing: {e}")

                    # Get changes summary
                    changes = result.changes if hasattr(result, "changes") else None

                    # Publish completion
                    processor.redis_integration.handle_match_processing_complete(
                        matches, changes, {"processor_type": type(processor).__name__}
                    )
                else:
                    logger.info("No changes processed, skipping Redis publishing")

                return result

            except Exception as e:
                # Publish error
                processor.redis_integration.handle_processing_error(
                    e, {"processor_type": type(processor).__name__}
                )
                raise

        # Replace processing method
        processor.run_processing_cycle = enhanced_run_processing_cycle

        logger.info("✅ Redis integration added to UnifiedMatchProcessor")

    # Fallback for legacy processors with _process_matches_sync
    elif hasattr(processor, "_process_matches_sync"):
        processor._original_process_matches_sync = processor._process_matches_sync

        def enhanced_process_matches_sync() -> Any:
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

        logger.info("✅ Redis integration added to legacy match processor")

    else:
        logger.warning(
            "⚠️ Could not find compatible method to enhance "
            "(expected run_processing_cycle or _process_matches_sync)"
        )


def create_redis_service() -> MatchProcessorRedisService:
    """
    Create a standalone Redis service instance.

    Returns:
        MatchProcessorRedisService: Redis service instance
    """
    return MatchProcessorRedisService()


class EnhancedMatchProcessingIntegration:
    """
    Enhanced Redis integration for match processing with Schema v2.0 support.

    Provides Organization ID mapping for logo service integration and complete
    contact data structure for calendar sync.
    """

    def __init__(self, redis_client: Optional[Any] = None, enabled: bool = True) -> None:
        """
        Initialize enhanced Redis integration.

        Args:
            redis_client: Redis client instance (optional)
            enabled: Whether Redis publishing is enabled
        """
        self.enabled = enabled
        self.redis_service = MatchProcessorRedisService()

        # Import here to avoid circular imports
        from .publisher import MatchProcessorRedisPublisher

        self.publisher = MatchProcessorRedisPublisher()

    def handle_match_processing_complete_v2(
        self,
        matches: List[Dict],
        changes_summary: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Handle match processing completion with Enhanced Schema v2.0 publishing.

        Args:
            matches: List of FOGIS match objects
            changes_summary: Change detection results with detailed_changes
            metadata: Additional processing metadata
        """
        if not self.enabled:
            logger.info("📡 Redis publishing disabled - skipping Enhanced Schema v2.0 publishing")
            return

        try:
            # Validate Organization IDs for Enhanced Schema v2.0
            self._validate_organization_ids(matches)

            # Log Enhanced Schema v2.0 message details
            self._log_enhanced_message_details(matches, changes_summary)

            # Publish multi-version messages for backward compatibility
            results = self.publisher.publish_multi_version_updates(
                matches, changes_summary, metadata
            )

            # Log publishing results
            self._log_publishing_results(results)

            logger.info("✅ Enhanced Schema v2.0 publishing completed successfully")

        except Exception as e:
            logger.error(f"❌ Enhanced Schema v2.0 publishing failed: {e}")
            # Fallback to standard publishing if available
            try:
                self.redis_service.handle_match_processing_complete(
                    matches, changes_summary or {}, metadata
                )
                logger.info("✅ Fallback to standard Redis publishing successful")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback publishing also failed: {fallback_error}")

    def _validate_organization_ids(self, matches: List[Dict]) -> None:
        """Validate that Organization IDs are present for logo service integration."""
        missing_org_ids = []

        for match in matches:
            match_id = match.get("matchid", "unknown")
            if not match.get("lag1foreningid"):
                missing_org_ids.append(f"Match {match_id}: missing lag1foreningid")
            if not match.get("lag2foreningid"):
                missing_org_ids.append(f"Match {match_id}: missing lag2foreningid")

        if missing_org_ids:
            logger.warning(
                "⚠️ Missing Organization IDs for logo service:\n"
                + "\n".join(f"   - {msg}" for msg in missing_org_ids[:5])
                + (
                    f"\n   ... and {len(missing_org_ids) - 5} more"
                    if len(missing_org_ids) > 5
                    else ""
                )
            )
        else:
            logger.info("✅ All matches have Organization IDs for logo service integration")

    def _log_enhanced_message_details(
        self, matches: List[Dict], changes_summary: Optional[Dict]
    ) -> None:
        """Log Enhanced Schema v2.0 message details for operational visibility."""
        logger.info("📡 Enhanced Schema v2.0 Message Details:")
        logger.info(f"   - Total matches: {len(matches)}")
        logger.info(f"   - Has changes: {bool(changes_summary)}")

        if matches:
            sample_match = matches[0]
            logger.info(
                f"   - Sample Organization IDs: Home={sample_match.get('lag1foreningid')}, Away={sample_match.get('lag2foreningid')}"
            )

        if changes_summary and hasattr(changes_summary, "get"):
            detailed_changes = changes_summary.get("detailed_changes", [])
            logger.info(f"   - Detailed changes: {len(detailed_changes)} field-level changes")

    def _log_publishing_results(self, results: Dict[str, Any]) -> None:
        """Log multi-version publishing results."""
        for version, result in results.items():
            if result.success:
                logger.info(f"   ✅ {version}: {result.subscribers_notified} subscribers")
            else:
                logger.error(f"   ❌ {version}: {result.error}")


def add_enhanced_redis_integration_to_processor(processor: Any) -> None:
    """
    Add Enhanced Schema v2.0 Redis integration to a match processor instance.

    Supports both UnifiedMatchProcessor (with run_processing_cycle) and
    legacy processors (with _process_matches_sync).

    Args:
        processor: Match processor instance to enhance with Enhanced Schema v2.0 integration
    """
    # Add Enhanced Redis integration to processor
    processor.enhanced_redis_integration = EnhancedMatchProcessingIntegration()

    # Hook into UnifiedMatchProcessor's run_processing_cycle method
    if hasattr(processor, "run_processing_cycle"):
        processor._original_run_processing_cycle = processor.run_processing_cycle

        def enhanced_run_processing_cycle_v2() -> Any:
            """Enhanced processing cycle with Schema v2.0 Redis integration."""
            try:
                # Publish processing start
                processor.enhanced_redis_integration.redis_service.handle_processing_start(
                    {"processor_type": type(processor).__name__, "schema_version": "2.0"}
                )

                # Call original processing method
                result = processor._original_run_processing_cycle()

                # Extract data from ProcessingResult
                if result and result.processed:
                    # Get matches from the change detector's current state
                    matches = []
                    if hasattr(processor, "change_detector"):
                        try:
                            matches = processor.change_detector.load_current_matches()
                        except Exception as e:
                            logger.warning(f"Could not load matches for Redis publishing: {e}")

                    # Get changes summary
                    changes = result.changes if hasattr(result, "changes") else None

                    # Publish completion with Enhanced Schema v2.0
                    processor.enhanced_redis_integration.handle_match_processing_complete_v2(
                        matches,
                        changes,
                        {
                            "processor_type": type(processor).__name__,
                            "schema_version": "2.0",
                            "logo_service_compatible": True,
                        },
                    )
                else:
                    logger.info("No changes processed, skipping Enhanced Schema v2.0 publishing")

                return result

            except Exception as e:
                # Publish error
                processor.enhanced_redis_integration.redis_service.handle_processing_error(
                    e, {"processor_type": type(processor).__name__, "schema_version": "2.0"}
                )
                raise

        # Replace processing method
        processor.run_processing_cycle = enhanced_run_processing_cycle_v2

        logger.info("✅ Enhanced Schema v2.0 Redis integration added to UnifiedMatchProcessor")

    # Fallback for legacy processors with _process_matches_sync
    elif hasattr(processor, "_process_matches_sync"):
        processor._original_process_matches_sync = processor._process_matches_sync

        def enhanced_process_matches_sync_v2() -> Any:
            """Enhanced processing method with Schema v2.0 Redis integration."""
            try:
                # Publish processing start
                processor.enhanced_redis_integration.redis_service.handle_processing_start(
                    {"processor_type": type(processor).__name__, "schema_version": "2.0"}
                )

                # Call original processing method
                result = processor._original_process_matches_sync()

                # Extract matches and changes from result if available
                matches = getattr(result, "matches", []) if result else []
                changes = getattr(result, "changes", {}) if result else {}

                # Publish completion with Enhanced Schema v2.0
                processor.enhanced_redis_integration.handle_match_processing_complete_v2(
                    matches,
                    changes,
                    {
                        "processor_type": type(processor).__name__,
                        "schema_version": "2.0",
                        "logo_service_compatible": True,
                    },
                )

                return result

            except Exception as e:
                # Publish error
                processor.enhanced_redis_integration.redis_service.handle_processing_error(
                    e, {"processor_type": type(processor).__name__, "schema_version": "2.0"}
                )
                raise

        # Replace processing method
        processor._process_matches_sync = enhanced_process_matches_sync_v2

        logger.info("✅ Enhanced Schema v2.0 Redis integration added to legacy match processor")

    else:
        logger.warning(
            "⚠️ Could not find compatible method to enhance "
            "(expected run_processing_cycle or _process_matches_sync)"
        )
