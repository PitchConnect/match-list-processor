"""Data management for match list processing."""

import json
import logging
import os
from typing import Optional, cast

from ..config import settings
from ..custom_types import MatchList

logger = logging.getLogger(__name__)


class MatchDataManager:
    """Manages loading and saving of match data."""

    def __init__(self, data_folder: Optional[str] = None, filename: Optional[str] = None):
        """Initialize the data manager.

        Args:
            data_folder: Directory for data storage. If None, uses config default.
            filename: Filename for match data. If None, uses config default.
        """
        self.data_folder = data_folder or settings.data_folder
        self.filename = filename or settings.previous_matches_file
        self.file_path = os.path.join(self.data_folder, self.filename)

    def load_previous_matches_raw_json(self) -> Optional[str]:
        """Load the previous match list from JSON file as RAW JSON STRING.

        Returns:
            Raw JSON string if successful, None if file not found or error.
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                raw_json_string = f.read()
                logger.debug(f"Loaded previous matches JSON from {self.file_path} (raw string).")
                return raw_json_string
        except FileNotFoundError:
            logger.info(
                f"Previous matches JSON file not found at {self.file_path}. Starting fresh."
            )
            return None
        except Exception as e:
            logger.error(
                f"Error loading previous matches JSON from {self.file_path}: {e}. Starting fresh."
            )
            return None

    def parse_raw_json_to_list(self, raw_json_string: Optional[str]) -> MatchList:
        """Parse the raw JSON string into a Python list of matches.

        Args:
            raw_json_string: Raw JSON string to parse

        Returns:
            List of match dictionaries, empty list if parsing fails.
        """
        if not raw_json_string:
            return []

        try:
            previous_matches_list = json.loads(raw_json_string)
            first_three_ids = (
                [match["matchid"] for match in previous_matches_list[:3]]
                if previous_matches_list
                else []
            )
            logger.debug(
                f"Parsed raw JSON to list of matches (count: {len(previous_matches_list)}) - "
                f"first 3 match IDs: {first_three_ids}"
            )
            return cast(MatchList, previous_matches_list)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON string: {e}. Starting fresh with empty data.")
            return []

    def save_current_matches_raw_json(self, raw_json_string: str) -> None:
        """Save the current match list as RAW JSON STRING to file.

        Args:
            raw_json_string: Raw JSON string to save
        """
        os.makedirs(self.data_folder, exist_ok=True)

        try:
            logger.debug(
                f"Saving current matches as raw JSON string (first 50 chars): "
                f"{raw_json_string[:50]}..."
            )

            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(raw_json_string)

            logger.info(f"Current matches saved to {self.file_path} as raw JSON.")
        except Exception as e:
            logger.error(f"Error saving current matches as raw JSON to {self.file_path}: {e}")
