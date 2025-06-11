"""Match comparison and change detection logic."""

import logging
from typing import Set, Tuple

from ..types import MatchList, MatchDict_Dict, MatchId


logger = logging.getLogger(__name__)


class MatchComparator:
    """Handles comparison between previous and current match lists."""

    @staticmethod
    def convert_to_dict(match_list: MatchList) -> MatchDict_Dict:
        """Convert match list to dictionary keyed by match ID.
        
        Args:
            match_list: List of match dictionaries
            
        Returns:
            Dictionary with match IDs as keys and match data as values
        """
        return {int(match['matchid']): match for match in match_list}

    @staticmethod
    def detect_changes(
        previous_matches: MatchDict_Dict, 
        current_matches: MatchDict_Dict
    ) -> Tuple[Set[MatchId], Set[MatchId], Set[MatchId]]:
        """Detect changes between previous and current match lists.
        
        Args:
            previous_matches: Dictionary of previous matches
            current_matches: Dictionary of current matches
            
        Returns:
            Tuple of (new_match_ids, removed_match_ids, common_match_ids)
        """
        previous_match_ids = set(previous_matches.keys())
        current_match_ids = set(current_matches.keys())

        new_match_ids = current_match_ids - previous_match_ids
        removed_match_ids = previous_match_ids - current_match_ids
        common_match_ids = current_match_ids.intersection(previous_match_ids)

        logger.debug(f"Keys of current_matches dictionary: {list(current_matches.keys())}")
        logger.debug(f"Keys of previous_matches dictionary: {list(previous_matches.keys())}")

        return new_match_ids, removed_match_ids, common_match_ids

    @staticmethod
    def is_match_modified(previous_match: dict, current_match: dict) -> bool:
        """Check if a match has been modified.
        
        Args:
            previous_match: Previous match data
            current_match: Current match data
            
        Returns:
            True if match has been modified, False otherwise
        """
        # Check if match time has changed
        if previous_match.get('tid') != current_match.get('tid'):
            return True

        # Check if teams have changed
        if (previous_match.get('lag1lagid') != current_match.get('lag1lagid') or
            previous_match.get('lag2lagid') != current_match.get('lag2lagid')):
            return True

        # Check if venue has changed
        if previous_match.get('anlaggningid') != current_match.get('anlaggningid'):
            return True

        # Check if referee team has changed
        prev_referees = previous_match.get('domaruppdraglista', [])
        curr_referees = current_match.get('domaruppdraglista', [])
        
        if len(prev_referees) != len(curr_referees):
            return True
        
        prev_ref_ids = {ref.get('domarid') for ref in prev_referees}
        curr_ref_ids = {ref.get('domarid') for ref in curr_referees}
        
        if prev_ref_ids != curr_ref_ids:
            return True

        return False

    @staticmethod
    def get_modification_details(previous_match: dict, current_match: dict) -> list:
        """Get detailed list of modifications between two matches.
        
        Args:
            previous_match: Previous match data
            current_match: Current match data
            
        Returns:
            List of modification descriptions
        """
        modifications = []

        if previous_match.get('tid') != current_match.get('tid'):
            modifications.append(
                f"Date/Time changed from {previous_match.get('tidsangivelse')} "
                f"to {current_match.get('tidsangivelse')}"
            )

        if previous_match.get('lag1lagid') != current_match.get('lag1lagid'):
            modifications.append(
                f"Home Team changed from ID {previous_match.get('lag1lagid')} "
                f"to {current_match.get('lag1lagid')}"
            )

        if previous_match.get('lag2lagid') != current_match.get('lag2lagid'):
            modifications.append(
                f"Away Team changed from ID {previous_match.get('lag2lagid')} "
                f"to {current_match.get('lag2lagid')}"
            )

        if previous_match.get('anlaggningid') != current_match.get('anlaggningid'):
            modifications.append(
                f"Venue changed from ID {previous_match.get('anlaggningid')} "
                f"to {current_match.get('anlaggningid')}"
            )

        # Check referee changes
        prev_referees = previous_match.get('domaruppdraglista', [])
        curr_referees = current_match.get('domaruppdraglista', [])
        
        if len(prev_referees) != len(curr_referees):
            modifications.append("Referee team assignments changed (number of referees changed)")
        else:
            prev_ref_ids = {ref.get('domarid') for ref in prev_referees}
            curr_ref_ids = {ref.get('domarid') for ref in curr_referees}
            if prev_ref_ids != curr_ref_ids:
                modifications.append("Referee team assignments changed (different referees)")

        return modifications
