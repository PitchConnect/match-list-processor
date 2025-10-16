"""Unified match processor with integrated change detection and notifications."""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

from ..notifications.adapters.semantic_to_legacy_adapter import SemanticToLegacyAdapter
from ..notifications.analysis.semantic_analyzer import SemanticChangeAnalyzer
from ..notifications.notification_service import NotificationService
from ..services.api_client import DockerNetworkApiClient
from ..services.avatar_service import WhatsAppAvatarService
from ..services.phonebook_service import FogisPhonebookSyncService
from ..services.storage_service import GoogleDriveStorageService
from ..utils.description_generator import generate_whatsapp_description
from .change_detector import ChangesSummary, GranularChangeDetector
from .data_manager import MatchDataManager
from .match_comparator import MatchComparator
from .match_processor import MatchProcessor

logger = logging.getLogger(__name__)


class ProcessingResult:
    """Result of a processing cycle."""

    def __init__(
        self,
        processed: bool,
        changes: Optional[ChangesSummary] = None,
        processing_time: float = 0.0,
        errors: Optional[list] = None,
        matches: Optional[list] = None,
    ):
        self.processed = processed
        self.changes = changes
        self.processing_time = processing_time
        self.errors = errors or []
        self.matches = matches or []  # Store processed matches for Redis publishing
        self.assets_generated = 0
        self.calendar_synced = False
        self.notifications_sent = 0
        self.notification_results: Optional[Dict[str, Any]] = None


class UnifiedMatchProcessor:
    """Unified processor that combines change detection with match processing and notifications."""

    def __init__(
        self,
        previous_matches_file: str = "data/previous_matches.json",
        notification_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the unified processor.

        Args:
            previous_matches_file: Path to file storing previous matches state
            notification_config: Configuration for notification system
        """
        # Initialize change detection
        self.change_detector = GranularChangeDetector(previous_matches_file)

        # Initialize semantic analysis system
        self.use_semantic_analysis = self._get_config_bool("ENABLE_SEMANTIC_ANALYSIS", True)
        self.fallback_to_legacy = self._get_config_bool("FALLBACK_TO_LEGACY", True)

        if self.use_semantic_analysis:
            try:
                self.semantic_analyzer = SemanticChangeAnalyzer()
                self.semantic_adapter = SemanticToLegacyAdapter()
                logger.info("Semantic analysis system initialized")
            except Exception as e:
                logger.error(f"Failed to initialize semantic analysis: {e}")
                if not self.fallback_to_legacy:
                    raise
                self.use_semantic_analysis = False
                logger.info("Disabled semantic analysis, using legacy detection")

        # Initialize notification service
        self.notification_service = None
        if notification_config:
            try:
                self.notification_service = NotificationService(notification_config)
                logger.info("Notification service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize notification service: {e}")

        # Initialize existing services
        self.data_manager = MatchDataManager()
        self.api_client = DockerNetworkApiClient()
        self.avatar_service = WhatsAppAvatarService()
        self.storage_service = GoogleDriveStorageService()
        self.phonebook_service = FogisPhonebookSyncService()

        # Connect notification service to monitored services
        if self.notification_service:
            self.api_client.set_notification_service(self.notification_service)
            logger.info("Connected notification service to API client monitoring")

        # Initialize match processor
        self.match_processor = MatchProcessor(
            self.avatar_service,
            self.storage_service,
            generate_whatsapp_description,
        )

        logger.info("Unified match processor initialized")

    def run_processing_cycle(self) -> ProcessingResult:
        """Run a complete processing cycle with integrated change detection.

        Returns:
            ProcessingResult with details of what was processed
        """
        start_time = time.time()
        errors: list[str] = []

        try:
            logger.info("Starting unified processing cycle...")

            # 1. Fetch current matches
            current_matches = self._fetch_current_matches()
            if not current_matches:
                logger.warning("No matches fetched from API")
                return ProcessingResult(
                    processed=False,
                    processing_time=time.time() - start_time,
                    errors=["No matches fetched from API"],
                    matches=[],
                )

            # 2. Detect changes using integrated change detector
            changes = self.change_detector.detect_changes(current_matches)

            # 3. Process only if changes detected
            if changes.has_changes:
                logger.info(f"Changes detected - processing {changes.total_changes} changes")

                # Process the changes
                self._process_changes(changes, current_matches)

                # Send notifications for changes
                notification_results = self._send_notifications(changes, current_matches)

                # Trigger downstream services
                self._trigger_downstream_services(changes)

                # Update state
                self.change_detector.save_current_matches(current_matches)

                result = ProcessingResult(
                    processed=True,
                    changes=changes,
                    processing_time=time.time() - start_time,
                    errors=errors,
                    matches=current_matches,
                )
                result.notification_results = notification_results
                result.notifications_sent = (
                    notification_results.get("notifications_sent", 0) if notification_results else 0
                )

                return result
            else:
                logger.info("No changes detected - skipping processing")
                return ProcessingResult(
                    processed=False,
                    changes=changes,
                    processing_time=time.time() - start_time,
                    errors=errors,
                    matches=current_matches,
                )

        except Exception as e:
            error_msg = f"Processing cycle failed: {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

            return ProcessingResult(
                processed=False, processing_time=time.time() - start_time, errors=errors, matches=[]
            )

    def _fetch_current_matches(self) -> list:
        """Fetch current matches from the API.

        Returns:
            List of current matches
        """
        try:
            logger.info("Fetching current matches from API...")
            matches = self.api_client.fetch_matches_list()
            logger.info(f"Fetched {len(matches)} matches from API")
            return matches
        except Exception as e:
            logger.error(f"Failed to fetch matches from API: {e}")
            raise

    def _process_changes(self, changes: ChangesSummary, current_matches: list) -> bool:
        """Process detected changes using existing match processor logic.

        Args:
            changes: Summary of detected changes
            current_matches: Current matches from API

        Returns:
            True if processing was successful
        """
        try:
            logger.info("Processing detected changes...")

            # Process using existing logic with current matches
            self._run_existing_processing_logic(current_matches)

            return True

        except Exception as e:
            logger.error(f"Failed to process changes: {e}")
            return False

    def _run_existing_processing_logic(self, matches: list) -> None:
        """Run the existing match processing logic.

        Args:
            matches: List of matches to process
        """
        try:
            # Convert matches to the format expected by existing processor
            current_matches_dict = MatchComparator.convert_to_dict(matches)

            # Load previous matches for comparison (using existing logic)
            raw_json = self.data_manager.load_previous_matches_raw_json()
            previous_matches_list = self.data_manager.parse_raw_json_to_list(raw_json)
            previous_matches_dict = MatchComparator.convert_to_dict(previous_matches_list)

            # Use existing change detection for processing workflow
            new_match_ids, removed_match_ids, common_match_ids = MatchComparator.detect_changes(
                previous_matches_dict, current_matches_dict
            )

            # Process new matches
            if new_match_ids:
                logger.info(f"Processing {len(new_match_ids)} new matches")
                for match_id in new_match_ids:
                    match = current_matches_dict[match_id]
                    result = self.match_processor.process_match(match, match_id, is_new=True)
                    if result and result.get("success"):
                        logger.info(f"Successfully processed new match {match_id}")
                    else:
                        logger.error(
                            f"Failed to process new match {match_id}: {result.get('error_message') if result else 'Unknown error'}"
                        )

            # Process updated matches
            for match_id in common_match_ids:
                previous_match = previous_matches_dict[match_id]
                current_match = current_matches_dict[match_id]

                if MatchComparator.is_match_modified(previous_match, current_match):
                    logger.info(f"Processing updated match {match_id}")
                    result = self.match_processor.process_match(
                        current_match, match_id, is_new=False, previous_match_data=previous_match
                    )
                    if result and result.get("success"):
                        logger.info(f"Successfully processed updated match {match_id}")
                    else:
                        logger.error(
                            f"Failed to process updated match {match_id}: {result.get('error_message') if result else 'Unknown error'}"
                        )

            # Save processed matches
            import json

            raw_json = json.dumps(matches, ensure_ascii=False, indent=2)
            self.data_manager.save_current_matches_raw_json(raw_json)

        except Exception as e:
            logger.error(f"Failed to run existing processing logic: {e}")
            raise

    def _send_notifications(
        self, changes: ChangesSummary, current_matches: list
    ) -> Optional[Dict[str, Any]]:
        """Send notifications for detected changes with semantic analysis integration.

        Args:
            changes: Summary of detected changes
            current_matches: Current matches from API

        Returns:
            Notification results dictionary or None if notifications disabled
        """
        if not self.notification_service:
            logger.debug("Notification service not configured, skipping notifications")
            return None

        try:
            logger.info("Sending notifications for detected changes...")

            # Enhanced notification flow with semantic analysis
            if self.use_semantic_analysis and hasattr(self, "semantic_analyzer"):
                try:
                    # Perform semantic analysis on changed matches
                    categorized_changes = self._perform_semantic_analysis(changes, current_matches)

                    if categorized_changes:
                        # Send notifications with semantic context
                        notification_results = asyncio.run(
                            self.notification_service.process_changes(
                                categorized_changes,
                                self._get_match_context(current_matches, changes),
                            )
                        )
                        notification_results["semantic_analysis"] = True
                        return notification_results

                except Exception as e:
                    logger.error(f"Semantic analysis failed: {e}")

                    if not self.fallback_to_legacy:
                        raise

                    logger.info("Falling back to legacy change detection")

            # Legacy notification processing
            if hasattr(changes, "categorized_changes") and changes.categorized_changes:
                # Use enhanced granular change categorization
                notification_results = asyncio.run(
                    self.notification_service.process_changes(
                        changes.categorized_changes,
                        self._get_match_context(current_matches, changes),
                    )
                )
                notification_results["semantic_analysis"] = False
            else:
                # Fallback for basic change detection
                logger.info("Using fallback notification processing for basic changes")
                notification_results = {"enabled": True, "notifications_sent": 0, "fallback": True}

            logger.info(
                f"Notification processing completed: {notification_results.get('notifications_sent', 0)} notifications sent"
            )
            return notification_results

        except Exception as e:
            logger.error(f"Failed to send notifications: {e}")
            return {"enabled": True, "notifications_sent": 0, "error": str(e)}

    def _perform_semantic_analysis(
        self, changes: ChangesSummary, current_matches: list
    ) -> Optional[Any]:
        """
        Perform semantic analysis on detected changes.

        Args:
            changes: Summary of detected changes
            current_matches: Current matches from API

        Returns:
            CategorizedChanges object with semantic analysis or None
        """
        if not hasattr(self, "semantic_analyzer") or not hasattr(self, "semantic_adapter"):
            logger.warning("Semantic analysis components not available")
            return None

        try:
            # Load previous matches for comparison
            previous_matches = self.change_detector.load_previous_matches()
            prev_matches_dict = self.change_detector._convert_to_dict(previous_matches)
            curr_matches_dict = self.change_detector._convert_to_dict(
                [dict(match) if hasattr(match, "__dict__") else match for match in current_matches]
            )

            # Perform semantic analysis on each changed match
            all_semantic_analyses = []

            # Get changed match IDs from the changes summary
            if hasattr(changes, "changed_matches") and changes.changed_matches:
                for match_id in changes.changed_matches:
                    prev_match = prev_matches_dict.get(match_id)
                    curr_match = curr_matches_dict.get(match_id)

                    if prev_match and curr_match:
                        # Perform semantic analysis
                        semantic_analysis = self.semantic_analyzer.analyze_match_changes(
                            prev_match, curr_match
                        )
                        all_semantic_analyses.append(semantic_analysis)

            # If we have semantic analyses, convert them to legacy format
            if all_semantic_analyses:
                # For now, use the first analysis (could be enhanced to merge multiple)
                primary_analysis = all_semantic_analyses[0]

                # Convert semantic analysis to legacy categorized changes
                categorized_changes = self.semantic_adapter.convert_semantic_to_categorized(
                    primary_analysis
                )

                logger.info(
                    f"Semantic analysis completed: {len(primary_analysis.field_changes)} "
                    f"changes analyzed with {primary_analysis.overall_impact.value} impact"
                )

                return categorized_changes

            logger.debug("No semantic analysis performed - no changed matches found")
            return None

        except Exception as e:
            logger.error(f"Error during semantic analysis: {e}")
            raise

    def _get_match_context(self, current_matches: list, changes: ChangesSummary) -> Dict[str, Any]:
        """Get match context for notifications.

        Args:
            current_matches: Current matches from API
            changes: Summary of detected changes

        Returns:
            Match context dictionary
        """
        # For now, return the first match as context
        # In a more sophisticated implementation, this would extract
        # the specific match that changed
        if current_matches:
            match_data = current_matches[0]
            return match_data if isinstance(match_data, dict) else {}
        else:
            return {}

    def _get_config_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean configuration value from environment.

        Args:
            key: Environment variable key
            default: Default value if not found

        Returns:
            Boolean configuration value
        """
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on", "enabled")

    def _trigger_downstream_services(self, changes: ChangesSummary) -> None:
        """Trigger downstream services like calendar sync.

        Args:
            changes: Summary of detected changes
        """
        try:
            logger.info("Triggering downstream services...")

            # Trigger calendar sync using existing service
            calendar_sync_success = self._trigger_calendar_sync(changes)

            if calendar_sync_success:
                logger.info("Calendar sync triggered successfully")
            else:
                logger.warning("Calendar sync failed")

        except Exception as e:
            logger.error(f"Failed to trigger downstream services: {e}")

    def _trigger_calendar_sync(self, changes: ChangesSummary) -> bool:
        """Trigger calendar sync service.

        Args:
            changes: Summary of detected changes

        Returns:
            True if calendar sync was triggered successfully
        """
        try:
            # Use existing phonebook service to trigger calendar sync
            logger.info("Triggering calendar sync via phonebook service...")

            # Use the existing sync_contacts method
            success = self.phonebook_service.sync_contacts()
            return success

        except Exception as e:
            logger.error(f"Failed to trigger calendar sync: {e}")
            return False

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        stats: Dict[str, Any] = {
            "service_type": "unified_processor",
            "change_detection": "integrated",
            "last_processing": "not_implemented",  # Will be implemented with state tracking
            "total_processed": "not_implemented",
        }

        # Add notification statistics if available
        if self.notification_service:
            stats["notifications"] = {
                "enabled": True,
                "stakeholder_stats": self.notification_service.get_stakeholder_statistics(),
                "delivery_stats": self.notification_service.get_delivery_statistics(),
                "health_status": self.notification_service.get_health_status(),
            }
        else:
            stats["notifications"] = {"enabled": False}

        return stats

    def get_notification_health(self) -> Dict[str, Any]:
        """Get notification system health status.

        Returns:
            Notification health status dictionary
        """
        if not self.notification_service:
            return {"enabled": False, "status": "not_configured"}

        try:
            return self.notification_service.get_health_status()
        except Exception as e:
            logger.error(f"Failed to get notification health: {e}")
            return {"enabled": True, "status": "error", "error": str(e)}

    def test_notification_channels(self) -> Dict[str, Any]:
        """Test notification channels.

        Returns:
            Test results for all notification channels
        """
        if not self.notification_service:
            return {"enabled": False, "channels": {}}

        try:
            return self.notification_service.test_notification_channels()
        except Exception as e:
            logger.error(f"Failed to test notification channels: {e}")
            return {"enabled": True, "error": str(e), "channels": {}}
