"""Unified match list processor application with integrated change detection."""

import logging
import os
import signal
import sys
import time
from types import FrameType
from typing import Any, Optional

from src.config import settings
from src.core.unified_processor import UnifiedMatchProcessor
from src.web.health_server import create_health_server

logger = logging.getLogger(__name__)


class UnifiedMatchListProcessorApp:
    """Unified application class with integrated change detection and processing."""

    def __init__(self) -> None:
        """Initialize the unified application."""
        # Detect test mode to prevent hanging (multiple detection methods)
        self.is_test_mode = bool(
            os.environ.get("PYTEST_CURRENT_TEST")
            or os.environ.get("CI")
            or "pytest" in sys.modules
            or "unittest" in sys.modules
        )

        # Initialize unified processor (replaces separate change detection + processing)
        self.unified_processor = UnifiedMatchProcessor()

        # Initialize health server (skip in test mode)
        self.health_server: Optional[Any] = None
        if not self.is_test_mode:
            self.health_server = create_health_server(settings, port=8000)

        # Set up signal handlers for graceful shutdown (skip in test mode)
        if not self.is_test_mode:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)

        # Service mode configuration
        self.run_mode = os.environ.get("RUN_MODE", "oneshot").lower()
        self.service_interval = int(os.environ.get("SERVICE_INTERVAL", "300"))  # 5 minutes default
        self.running = True

        logger.info(
            f"Unified match list processor initialized in {self.run_mode} mode (test_mode: {self.is_test_mode})"
        )

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:  # noqa: ARG002
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.shutdown()
        sys.exit(0)

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        logger.info("Shutting down unified processor...")
        self.running = False
        if hasattr(self, "health_server") and self.health_server:
            self.health_server.stop_server()

    def run(self) -> None:
        """Run the unified application logic."""
        logger.info(f"Starting unified match list processor in {self.run_mode} mode...")

        # Start health server (skip in test mode)
        if not self.is_test_mode and self.health_server:
            logger.info("Starting health server on port 8000...")
            self.health_server.start_server()

            # Give health server time to start
            time.sleep(2)

            if self.health_server and not self.health_server.is_running():
                logger.warning(
                    "Health server failed to start, but continuing with main processing..."
                )

        if self.run_mode == "service":
            self._run_as_service()
        else:
            self._run_once()

    def _run_as_service(self) -> None:
        """Run as a persistent service with periodic processing."""
        # In test mode, run only once to prevent hanging
        if self.is_test_mode:
            logger.info("Test mode detected - running service cycle once only")
            try:
                result = self.unified_processor.run_processing_cycle()
                self._log_processing_result(result)
                logger.info("Test mode service cycle completed")
            except Exception as e:
                logger.error(f"Test mode service cycle failed: {e}")
            return

        logger.info(f"Running as persistent service with {self.service_interval}s interval")

        cycle_count = 0
        max_cycles = int(os.environ.get("MAX_SERVICE_CYCLES", "0"))  # 0 = unlimited

        while self.running:
            try:
                logger.info("Starting unified processing cycle...")
                result = self.unified_processor.run_processing_cycle()

                # Log processing results
                self._log_processing_result(result)

                cycle_count += 1
                logger.info(
                    f"Processing cycle {cycle_count} completed in {result.processing_time:.2f}s. "
                    f"Sleeping for {self.service_interval}s..."
                )

                # Exit after max cycles if specified (for testing)
                if max_cycles > 0 and cycle_count >= max_cycles:
                    logger.info(f"Reached maximum cycles ({max_cycles}), stopping service")
                    break

                # Sleep with interruption check - allow early exit if stopped
                sleep_remaining = self.service_interval
                while sleep_remaining > 0 and self.running:
                    time.sleep(1)
                    sleep_remaining -= 1

            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                logger.exception("Stack trace:")
                # Continue running even if one cycle fails
                time.sleep(30)  # Wait 30 seconds before retrying

        logger.info("Unified service mode stopped")

    def _run_once(self) -> None:
        """Run once and exit (original behavior)."""
        try:
            logger.info("Running unified processing cycle once...")
            result = self.unified_processor.run_processing_cycle()

            # Log processing results
            self._log_processing_result(result)

            if result.errors:
                logger.error("Processing completed with errors")
                sys.exit(1)
            else:
                logger.info("Unified match list processor execution finished successfully.")

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.exception("Stack trace:")
            self.shutdown()
            sys.exit(1)
        finally:
            # Ensure graceful shutdown
            self.shutdown()

    def _log_processing_result(self, result: Any) -> None:
        """Log the results of a processing cycle.

        Args:
            result: ProcessingResult from unified processor
        """
        if result.processed:
            logger.info("✅ Processing cycle completed successfully")

            if result.changes:
                changes = result.changes
                logger.info("📊 Changes processed:")
                logger.info(
                    f"  - New matches: {len(changes.new_matches) if changes.new_matches else 0}"
                )
                logger.info(
                    f"  - Updated matches: {len(changes.updated_matches) if changes.updated_matches else 0}"
                )
                logger.info(
                    f"  - Removed matches: {len(changes.removed_matches) if changes.removed_matches else 0}"
                )
                logger.info(f"  - Total changes: {changes.total_changes}")
            else:
                logger.info("  - No changes detected")

        else:
            if result.changes and not result.changes.has_changes:
                logger.info("ℹ️  No changes detected - processing skipped")
            else:
                logger.warning("⚠️  Processing cycle completed but no processing occurred")

        if result.errors:
            logger.error(f"❌ Processing errors: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"  - {error}")

        logger.info("⏱️  Processing time: %.2f seconds", result.processing_time)

    def get_status(self) -> dict:
        """Get current application status.

        Returns:
            Dictionary with current status information
        """
        return {
            "service_name": "unified-match-list-processor",
            "mode": self.run_mode,
            "running": self.running,
            "service_interval": self.service_interval,
            "processor_stats": self.unified_processor.get_processing_stats(),
            "health_server_running": (
                self.health_server.is_running() if self.health_server else False
            ),
        }


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format=settings.log_format,
    )


def main() -> None:
    """Run the unified match list processor application."""
    setup_logging()
    app = UnifiedMatchListProcessorApp()
    app.run()


if __name__ == "__main__":
    main()
