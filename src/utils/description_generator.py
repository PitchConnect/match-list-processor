"""WhatsApp group description generation utilities."""

import logging

from ..custom_types import MatchDict

logger = logging.getLogger(__name__)


def generate_whatsapp_description(match_details: MatchDict) -> str:
    """Generate a minimalist WhatsApp group description string from match details.

    Args:
        match_details: Dictionary containing match information

    Returns:
        Formatted WhatsApp group description
    """
    team1_name = match_details.get("lag1namn", "Team 1")
    team2_name = match_details.get("lag2namn", "Team 2")
    competition_name = match_details.get("tavlingnamn", "Competition N/A")
    venue = match_details.get("anlaggningnamn", "Venue N/A")
    match_id = match_details.get("matchid", "N/A")

    description = (
        f"*{team1_name} - {team2_name}*\n"
        f"_{competition_name}_\n"
        f"{venue}\n"
        f"\n"
        f"Match Facts: https://www.svenskfotboll.se/matchfakta/match?matchId={match_id}\n"
        f"\n"
        f"---\n"
        f"This group is for communication among the referee team. "
        f"Please keep messages relevant to your referee duties for this match."
    )

    logger.debug(
        f"Generated (minimalist v2) WhatsApp group description for match ID {match_id}: "
        f"{description[:80]}..."
    )

    return description


def create_example_match_details() -> MatchDict:
    """Create example match details for testing purposes.

    Returns:
        Example match details dictionary
    """
    return {
        "matchid": 6169105,
        "lag1namn": "IK Kongahälla",
        "lag2namn": "Motala AIF FK",
        "tavlingnamn": "Div 2 Norra Götaland, herr 2025",
        "anlaggningnamn": "Kongevi 1 Konstgräs",
    }
