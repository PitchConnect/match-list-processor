#!/usr/bin/env python3
"""
Smart entry point for match list processor.

This module automatically selects the appropriate application mode based on the RUN_MODE environment variable:
- RUN_MODE=service: Uses persistent service mode (src.app_persistent)
- RUN_MODE=oneshot: Uses traditional oneshot mode (src.app)
- Default: oneshot mode for backward compatibility

This resolves the restart loop issue by ensuring the correct application mode is used
based on deployment configuration.
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

    logger.info(f"Match List Processor starting in {run_mode} mode...")

    if run_mode == "service":
        logger.info("Using persistent service mode (src.app_persistent)")
        try:
            from src.app_persistent import main as persistent_main

            persistent_main()
        except ImportError as e:
            logger.error(f"Failed to import persistent service module: {e}")
            logger.error("Falling back to oneshot mode")
            run_mode = "oneshot"

    if run_mode == "oneshot":
        logger.info("Using oneshot mode (src.app)")
        try:
            from src.app import main as oneshot_main

            oneshot_main()
        except ImportError as e:
            logger.error(f"Failed to import oneshot module: {e}")
            sys.exit(1)

    if run_mode not in ["service", "oneshot"]:
        logger.warning(f"Unknown RUN_MODE '{run_mode}', defaulting to oneshot mode")
        from src.app import main as oneshot_main

        oneshot_main()


if __name__ == "__main__":
    main()
