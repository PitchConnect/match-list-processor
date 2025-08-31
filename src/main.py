#!/usr/bin/env python3
"""
Smart entry point for match list processor.

This module automatically selects the appropriate application mode based on environment variables:
- PROCESSOR_MODE=unified: Uses new unified processor with integrated change detection (default)
- PROCESSOR_MODE=legacy: Uses legacy processor with separate change detection
- RUN_MODE=service: Uses persistent service mode
- RUN_MODE=oneshot: Uses traditional oneshot mode
- Default: unified processor in oneshot mode for backward compatibility

This resolves the restart loop issue and provides the new unified architecture.
"""

import logging
import os
import sys

# Set up basic logging for the entry point
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point that selects the appropriate application mode."""
    run_mode = os.environ.get("RUN_MODE", "oneshot").lower()
    processor_mode = os.environ.get("PROCESSOR_MODE", "unified").lower()

    logger.info(
        f"Match List Processor starting in {run_mode} mode with {processor_mode} processor..."
    )

    # Use unified processor by default (new architecture)
    if processor_mode == "unified":
        logger.info("Using unified processor with integrated change detection (src.app_unified)")
        try:
            from src.app_unified import main as unified_main

            unified_main()
            return
        except ImportError as e:
            logger.error(f"Failed to import unified processor module: {e}")
            logger.error("Falling back to legacy processor")
            processor_mode = "legacy"

    # Legacy processor modes
    if processor_mode == "legacy":
        if run_mode == "service":
            logger.info("Using legacy persistent service mode (src.app_persistent)")
            try:
                from src.app_persistent import main as persistent_main

                persistent_main()
                return
            except ImportError as e:
                logger.error(f"Failed to import persistent service module: {e}")
                logger.error("Falling back to oneshot mode")
                run_mode = "oneshot"

        if run_mode == "oneshot":
            logger.info("Using legacy oneshot mode (src.app)")
            try:
                from src.app import main as oneshot_main

                oneshot_main()
                return
            except ImportError as e:
                logger.error(f"Failed to import oneshot module: {e}")
                sys.exit(1)

    # Handle unknown modes
    if run_mode not in ["service", "oneshot"]:
        logger.warning(f"Unknown RUN_MODE '{run_mode}', defaulting to unified processor")
        try:
            from src.app_unified import main as unified_main

            unified_main()
        except ImportError:
            logger.error("Failed to import unified processor, trying legacy oneshot")
            from src.app import main as oneshot_main

            oneshot_main()


if __name__ == "__main__":
    main()
