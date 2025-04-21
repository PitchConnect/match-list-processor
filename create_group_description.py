import logging

def generate_whatsapp_description(match_details):
    """
    Generates a minimalist WhatsApp group description string from match details (Version 2 - Minimalist).
    """
    team1_name = match_details.get('lag1namn', 'Team 1')
    team2_name = match_details.get('lag2namn', 'Team 2')
    competition_name = match_details.get('tavlingnamn', 'Competition N/A')
    venue = match_details.get('anlaggningnamn', 'Venue N/A')
    match_id = match_details.get('matchid', 'N/A')

    description = f"*{team1_name} - {team2_name}*\n" \
                  f"_{competition_name}_\n" \
                  f"{venue}\n" \
                  f"\n" \
                  f"Match Facts: https://www.svenskfotboll.se/matchfakta/match?matchId={match_id}\n" \
                  f"\n" \
                  f"---\n" \
                  f"This group is for communication among the referee team. " \
                  f"Please keep messages relevant to your referee duties for this match."

    logging.debug(f"Generated (minimalist v2) WhatsApp group description for match ID {match_id}: {description[:80]}...") # Log first 80 chars
    return description

if __name__ == '__main__':
    # Example usage (for testing)
    example_match_details = {
        "matchid": 6169105, # Example match ID
        "lag1namn": "IK Kongahälla",
        "lag2namn": "Motala AIF FK",
        "tavlingnamn": "Div 2 Norra Götaland, herr 2025",
        "anlaggningnamn": "Kongevi 1 Konstgräs"
    }
    # Note: The URL format for matchfakta is now: https://www.svenskfotboll.se/matchfakta/match?matchId=MATCH_ID
    description = generate_whatsapp_description(example_match_details)
    print(description)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Example (minimalist v2) WhatsApp group description generated (when run directly):")
    logging.info(description)