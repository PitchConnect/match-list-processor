"""Enhanced change detection logic migrated from match-list-change-detector service."""

import json
import logging
import os
from typing import Any, Dict, List, Tuple

from ..types import MatchList

logger = logging.getLogger(__name__)


class ChangesSummary:
    """Summary of detected changes in match list."""

    def __init__(
        self,
        new_matches: List[Dict[str, Any]],
        updated_matches: List[Dict[str, Any]],
        removed_matches: List[Dict[str, Any]],
    ):
        self.new_matches = new_matches
        self.updated_matches = updated_matches
        self.removed_matches = removed_matches
        self.has_changes = bool(new_matches or updated_matches or removed_matches)
        self.total_changes = len(new_matches) + len(updated_matches) + len(removed_matches)


class GranularChangeDetector:
    """Enhanced change detector with granular analysis capabilities."""

    def __init__(self, previous_matches_file: str = "data/previous_matches.json"):
        """Initialize the change detector.

        Args:
            previous_matches_file: Path to file storing previous matches state
        """
        self.previous_matches_file = previous_matches_file
        self.data_dir = os.path.dirname(previous_matches_file)

        # Ensure data directory exists
        if self.data_dir:
            os.makedirs(self.data_dir, exist_ok=True)

    def detect_changes(self, current_matches: MatchList) -> ChangesSummary:
        """Detect changes between previous and current match lists.

        Args:
            current_matches: Current list of matches from API

        Returns:
            ChangesSummary object with detailed change information
        """
        logger.info("Starting change detection analysis...")

        # Load previous matches
        previous_matches = self.load_previous_matches()

        # Convert to dictionaries for comparison
        prev_matches_dict = self._convert_to_dict(previous_matches)
        curr_matches_dict = self._convert_to_dict([dict(match) for match in current_matches])

        # Detect changes
        has_changes, changes = self._compare_match_lists(prev_matches_dict, curr_matches_dict)

        # Create summary
        summary = ChangesSummary(
            new_matches=changes.get("new_match_details", {}),
            updated_matches=changes.get("changed_match_details", {}),
            removed_matches=changes.get("removed_match_details", {}),
        )

        if has_changes:
            logger.info(
                f"Changes detected: {changes['new_matches']} new, "
                f"{changes['removed_matches']} removed, {changes['changed_matches']} changed"
            )
        else:
            logger.info("No changes detected in match list")

        return summary

    def load_previous_matches(self) -> List[Dict[str, Any]]:
        """Load previous matches from storage file.

        Returns:
            List of previous match dictionaries
        """
        try:
            if os.path.exists(self.previous_matches_file):
                with open(self.previous_matches_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle both direct list and nested structure
                if isinstance(data, list):
                    matches = data
                elif isinstance(data, dict) and "matches" in data:
                    matches = data["matches"]
                elif isinstance(data, dict) and "matchlista" in data:
                    matches = data["matchlista"]
                else:
                    logger.warning(f"Unexpected data structure in {self.previous_matches_file}")
                    matches = []

                logger.info(
                    f"Loaded {len(matches)} previous matches from {self.previous_matches_file}"
                )
                return matches
            else:
                logger.info(f"No previous matches file found at {self.previous_matches_file}")
                return []

        except Exception as e:
            logger.error(f"Failed to load previous matches: {e}")
            return []

    def save_current_matches(self, matches: MatchList) -> None:
        """Save current matches to storage file.

        Args:
            matches: Current list of matches to save
        """
        try:
            # Ensure directory exists
            os.makedirs(self.data_dir, exist_ok=True)

            with open(self.previous_matches_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(matches)} matches to {self.previous_matches_file}")

        except Exception as e:
            logger.error(f"Failed to save current matches: {e}")

    def _convert_to_dict(self, match_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Convert match list to dictionary keyed by match ID.

        Args:
            match_list: List of match dictionaries

        Returns:
            Dictionary with match IDs as keys
        """
        return {
            str(match.get("matchid", "")): match for match in match_list if match.get("matchid")
        }

    def _compare_match_lists(
        self,
        prev_matches_dict: Dict[str, Dict[str, Any]],
        curr_matches_dict: Dict[str, Dict[str, Any]],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Compare previous and current match lists to detect changes.

        This method implements the sophisticated change detection logic from the
        original match-list-change-detector service.

        Args:
            prev_matches_dict: Previous matches as dictionary
            curr_matches_dict: Current matches as dictionary

        Returns:
            Tuple of (has_changes, changes_dict)
        """
        # Get match ID sets
        prev_match_ids = set(prev_matches_dict.keys())
        curr_match_ids = set(curr_matches_dict.keys())

        # Find new, removed, and common matches
        new_match_ids = curr_match_ids - prev_match_ids
        removed_match_ids = prev_match_ids - curr_match_ids
        common_match_ids = curr_match_ids.intersection(prev_match_ids)

        # Analyze changes in common matches
        changed_matches = []

        for match_id in common_match_ids:
            prev_match = prev_matches_dict[match_id]
            curr_match = curr_matches_dict[match_id]

            # Check for basic field changes
            basic_changes = self._detect_basic_changes(prev_match, curr_match)

            # Check for referee changes
            referee_changes = self._detect_referee_changes(prev_match, curr_match)

            if basic_changes or referee_changes:
                change_record = self._create_change_record(
                    prev_match, curr_match, basic_changes, referee_changes
                )
                changed_matches.append(change_record)

        # Prepare changes summary
        changes = {
            "new_matches": len(new_match_ids),
            "removed_matches": len(removed_match_ids),
            "changed_matches": len(changed_matches),
            "new_match_details": [curr_matches_dict[match_id] for match_id in new_match_ids],
            "removed_match_details": [
                prev_matches_dict[match_id] for match_id in removed_match_ids
            ],
            "changed_match_details": changed_matches,
        }

        # Determine if there are any changes
        has_changes = (
            len(new_match_ids) > 0 or len(removed_match_ids) > 0 or len(changed_matches) > 0
        )

        return has_changes, changes

    def _detect_basic_changes(self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]) -> bool:
        """Detect basic field changes in a match.

        Args:
            prev_match: Previous match data
            curr_match: Current match data

        Returns:
            True if basic changes detected
        """
        # Fields to check for changes
        basic_fields = [
            "speldatum",
            "avsparkstid",
            "lag1lagid",
            "lag1namn",
            "lag2lagid",
            "lag2namn",
            "anlaggningnamn",
            "installd",
            "avbruten",
            "uppskjuten",
        ]

        for field in basic_fields:
            if prev_match.get(field) != curr_match.get(field):
                return True

        return False

    def _detect_referee_changes(
        self, prev_match: Dict[str, Any], curr_match: Dict[str, Any]
    ) -> bool:
        """Detect referee assignment changes.

        Args:
            prev_match: Previous match data
            curr_match: Current match data

        Returns:
            True if referee changes detected
        """
        prev_referee_ids = set()
        curr_referee_ids = set()

        # Extract referee IDs from previous match
        if "domaruppdraglista" in prev_match:
            for referee in prev_match["domaruppdraglista"]:
                prev_referee_ids.add(referee.get("domareid"))

        # Extract referee IDs from current match
        if "domaruppdraglista" in curr_match:
            for referee in curr_match["domaruppdraglista"]:
                curr_referee_ids.add(referee.get("domareid"))

        return prev_referee_ids != curr_referee_ids

    def _create_change_record(
        self,
        prev_match: Dict[str, Any],
        curr_match: Dict[str, Any],
        basic_changes: bool,
        referee_changes: bool,
    ) -> Dict[str, Any]:
        """Create detailed change record for a modified match.

        Args:
            prev_match: Previous match data
            curr_match: Current match data
            basic_changes: Whether basic fields changed
            referee_changes: Whether referee assignments changed

        Returns:
            Detailed change record dictionary
        """
        match_id = curr_match.get("matchid")

        change_record = {
            "match_id": match_id,
            "match_nr": curr_match.get("matchnr"),
            "previous": self._extract_match_details(prev_match),
            "current": self._extract_match_details(curr_match),
            "changes": {"basic": basic_changes, "referees": referee_changes},
        }

        return change_record

    def _extract_match_details(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant match details for change tracking.

        Args:
            match: Match data dictionary

        Returns:
            Extracted match details
        """
        details: Dict[str, Any] = {
            "date": match.get("speldatum"),
            "time": match.get("avsparkstid"),
            "home_team": {
                "id": match.get("lag1lagid"),
                "name": match.get("lag1namn"),
            },
            "away_team": {
                "id": match.get("lag2lagid"),
                "name": match.get("lag2namn"),
            },
            "venue": match.get("anlaggningnamn"),
            "status": {
                "cancelled": match.get("installd", False),
                "interrupted": match.get("avbruten", False),
                "postponed": match.get("uppskjuten", False),
            },
            "referees": [],
        }

        # Add referee details
        if "domaruppdraglista" in match:
            for referee in match["domaruppdraglista"]:
                details["referees"].append(
                    {
                        "id": referee.get("domareid"),
                        "name": referee.get("personnamn"),
                        "role": referee.get("domarrollnamn"),
                        "email": referee.get("epostadress"),
                        "phone": referee.get("mobiltelefon"),
                    }
                )

        return details
