"""Main application orchestrator for match list processing with persistent service mode support."""

import json
import logging
import signal
import sys
import time
import os
from types import FrameType
from typing import Optional

# Import the original app components
from src.config import settings
from src.core.data_manager import MatchDataManager
from src.core.match_comparator import MatchComparator
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.services.avatar_service import WhatsAppAvatarService
from src.services.phonebook_service import FogisPhonebookSyncService
from src.services.storage_service import GoogleDriveStorageService
from src.types import MatchDict_Dict
from src.utils.description_generator import generate_whatsapp_description
from src.web.health_server import create_health_server

logger = logging.getLogger(__name__)


class PersistentMatchListProcessorApp:
    """Main application class for match list processing with persistent service mode."""

    def __init__(self) -> None:
        """Initialize the application with all required services."""
        self.data_manager = MatchDataManager()
        self.api_client = DockerNetworkApiClient()
        self.avatar_service = WhatsAppAvatarService()
        self.storage_service = GoogleDriveStorageService()
        self.phonebook_service = FogisPhonebookSyncService()
        self.match_processor = MatchProcessor(
            self.avatar_service, self.storage_service, generate_whatsapp_description
        )

        # Initialize health server
        self.health_server = create_health_server(settings, port=8000)

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Persistent service mode configuration
        self.run_mode = os.environ.get("RUN_MODE", "oneshot").lower()
        self.service_interval = int(os.environ.get("SERVICE_INTERVAL", "300"))  # 5 minutes default
        self.running = True

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:  # noqa: ARG002
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.shutdown()
        sys.exit(0)

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down health server...")
        if hasattr(self, "health_server"):
            self.health_server.stop_server()

    def run(self) -> None:
        """Run the main application logic."""
        logger.info(f"Starting match list processor in {self.run_mode} mode...")

        # Start health server
        logger.info("Starting health server on port 8000...")
        self.health_server.start_server()

        # Give health server time to start
        time.sleep(2)

        if not self.health_server.is_running():
            logger.warning("Health server failed to start, but continuing with main processing...")

        if self.run_mode == "service":
            self._run_as_service()
        else:
            self._run_once()

    def _run_as_service(self) -> None:
        """Run as a persistent service with periodic processing."""
        logger.info(f"Running as persistent service with {self.service_interval}s interval")
        
        while self.running:
            try:
                logger.info("Starting periodic match processing cycle...")
                self._process_matches()
                logger.info(f"Match processing cycle completed. Sleeping for {self.service_interval}s...")
                
                # Sleep with interruption check
                for _ in range(self.service_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                logger.exception("Stack trace:")
                # Continue running even if one cycle fails
                time.sleep(30)  # Wait 30 seconds before retrying

        logger.info("Service mode stopped")

    def _run_once(self) -> None:
        """Run once and exit (original behavior)."""
        try:
            self._process_matches()
            logger.info("Match list processor execution finished.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.exception("Stack trace:")
            self.shutdown()
            sys.exit(1)
        finally:
            # Ensure graceful shutdown
            self.shutdown()

    def _process_matches(self) -> None:
        """Process matches (core logic extracted from original run method)."""
        # Sync contacts with phonebook
        sync_result = self.phonebook_service.sync_contacts()
        if not sync_result:
            logger.warning("Contact sync failed, but continuing with match processing.")

        # Load and parse previous matches
        previous_matches_dict = self._load_previous_matches()
        logger.info(f"Loaded previous matches data: {len(previous_matches_dict)} matches.")

        # Fetch current matches
        current_matches_dict = self._fetch_current_matches()
        if not current_matches_dict:
            logger.warning("Could not fetch current matches.")
            if self.run_mode == "oneshot":
                sys.exit(1)
            else:
                return  # Continue in service mode

        logger.info(f"Fetched current matches: {len(current_matches_dict)} matches.")

        # Detect and process changes
        self._process_match_changes(previous_matches_dict, current_matches_dict)

        # Save current matches for future comparison
        self._save_current_matches(current_matches_dict)

    def _load_previous_matches(self) -> MatchDict_Dict:
        """Load and parse previous matches from storage."""
        raw_json = self.data_manager.load_previous_matches_raw_json()
        match_list = self.data_manager.parse_raw_json_to_list(raw_json)
        return MatchComparator.convert_to_dict(match_list)

    def _fetch_current_matches(self) -> MatchDict_Dict:
        """Fetch current matches from API."""
        logger.info("\n--- Fetching Current Matches List ---")
        current_matches_list = self.api_client.fetch_matches_list()

        if not current_matches_list:
            return {}

        return MatchComparator.convert_to_dict(current_matches_list)

    def _process_match_changes(
        self, previous_matches: MatchDict_Dict, current_matches: MatchDict_Dict
    ) -> None:
        """Process changes between previous and current matches."""
        logger.info("\n--- Starting Match Comparison and Change Detection ---")

        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(
            previous_matches, current_matches
        )

        # Process new matches
        self._process_new_matches(new_ids, current_matches)

        # Process removed matches
        self._process_removed_matches(removed_ids, previous_matches)

        # Process modified matches
        self._process_modified_matches(common_ids, previous_matches, current_matches)

        logger.info("\n--- Match Comparison and Change Detection Finished ---")

    def _process_new_matches(self, new_ids: set, current_matches: MatchDict_Dict) -> None:
        """Process newly detected matches."""
        if new_ids:
            logger.info(f"Detected NEW matches: {len(new_ids)}")
            for match_id in new_ids:
                match_data = current_matches[match_id]
                self.match_processor.process_match(match_data, match_id, is_new=True)
        else:
            logger.info("No new matches detected.")

    def _process_removed_matches(self, removed_ids: set, previous_matches: MatchDict_Dict) -> None:
        """Process removed matches."""
        if removed_ids:
            logger.info(f"Detected REMOVED matches: {len(removed_ids)}")
            for match_id in removed_ids:
                removed_match = previous_matches[match_id]
                logger.info(
                    f"  - Removed Match ID: {match_id}, "
                    f"Teams: {removed_match['lag1namn']} vs {removed_match['lag2namn']}"
                )
        else:
            logger.info("No removed matches detected.")

    def _process_modified_matches(
        self, common_ids: set, previous_matches: MatchDict_Dict, current_matches: MatchDict_Dict
    ) -> None:
        """Process modified matches."""
        if common_ids:
            logger.info(f"Checking for MODIFIED matches among {len(common_ids)} common matches...")
            modified_count = 0

            for match_id in common_ids:
                prev_match = previous_matches[match_id]
                curr_match = current_matches[match_id]

                if MatchComparator.is_match_modified(prev_match, curr_match):
                    modified_count += 1
                    self.match_processor.process_match(
                        curr_match, match_id, is_new=False, previous_match_data=prev_match
                    )

            logger.info(
                f"Found {modified_count} modified matches out of {len(common_ids)} common matches."
            )
        else:
            logger.info("No common matches found between previous and current lists.")

    def _save_current_matches(self, current_matches: MatchDict_Dict) -> None:
        """Save current matches for future comparison."""
        # Convert back to list format for JSON serialization
        current_matches_list = list(current_matches.values())
        raw_json_string = json.dumps(current_matches_list, ensure_ascii=False)
        self.data_manager.save_current_matches_raw_json(raw_json_string)
        logger.info("Current matches saved as raw JSON for future comparison.")


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()), format=settings.log_format
    )


def main() -> None:
    """Main entry point."""
    setup_logging()
    app = PersistentMatchListProcessorApp()
    app.run()


if __name__ == "__main__":
    main()
