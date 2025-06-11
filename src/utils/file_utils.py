"""File handling utilities."""

import logging
import os
from typing import List, Optional, Tuple

from ..types import MatchDict, FilePath
from ..config import settings


logger = logging.getLogger(__name__)


def extract_referee_names(match: MatchDict) -> List[str]:
    """Extract referee names from a match object.
    
    Args:
        match: Match data dictionary
        
    Returns:
        List of referee names
    """
    referee_names = []
    for referee in match.get('domaruppdraglista', []):
        referee_name = referee.get('personnamn', '') or referee.get('namn', '')
        if referee_name:
            referee_names.append(referee_name)
    return referee_names


def save_description_to_file(description_text: str, match_id: int) -> Optional[FilePath]:
    """Save description text to a temporary file.
    
    Args:
        description_text: WhatsApp group description text
        match_id: Match ID for filename
        
    Returns:
        File path if successful, None if failed
    """
    description_filename = f"whatsapp_group_description_match_{match_id}.txt"
    temp_description_filepath = os.path.join(settings.temp_file_directory, description_filename)
    
    try:
        with open(temp_description_filepath, 'w', encoding='utf-8') as description_file:
            description_file.write(description_text)
        logger.info(f"Description text saved to temporary file: {temp_description_filepath}")
        return temp_description_filepath
    except Exception as save_error:
        logger.error(f"Error saving description text to {temp_description_filepath}: {save_error}")
        logger.debug(f"File saving FAILED with error for: {temp_description_filepath}")
        return None


def save_avatar_to_file(avatar_data: bytes, match_id: int) -> Tuple[Optional[FilePath], Optional[str]]:
    """Save avatar image data to a temporary file.
    
    Args:
        avatar_data: Binary avatar image data
        match_id: Match ID for filename
        
    Returns:
        Tuple of (file_path, filename) if successful, (None, None) if failed
    """
    avatar_filename = f"whatsapp_group_avatar_match_{match_id}.png"
    temp_avatar_filepath = os.path.join(settings.temp_file_directory, avatar_filename)

    try:
        with open(temp_avatar_filepath, 'wb') as avatar_file:
            avatar_file.write(avatar_data)
        logger.info(f"Avatar image downloaded and saved to: {temp_avatar_filepath}")
        logger.debug(f"File saving completed WITHOUT errors for: {temp_avatar_filepath}")
        return temp_avatar_filepath, avatar_filename
    except Exception as save_error:
        logger.error(f"Error saving avatar image to {temp_avatar_filepath}: {save_error}")
        logger.debug(f"File saving FAILED with error for: {temp_avatar_filepath}")
        return None, None


def save_group_info_to_file(match_data: MatchDict, match_id: int) -> Tuple[Optional[FilePath], Optional[str]]:
    """Save group name and referee names to a file.
    
    Args:
        match_data: Match data dictionary
        match_id: Match ID for filename
        
    Returns:
        Tuple of (file_path, filename) if successful, (None, None) if failed
    """
    team1_name = match_data.get('lag1namn', 'Team 1')
    team2_name = match_data.get('lag2namn', 'Team 2')
    group_name = f"{team1_name} - {team2_name}"

    # Get match details
    match_date = match_data.get('speldatum', '')
    match_time = match_data.get('avsparkstid', '')
    match_number = match_data.get('matchnr', '')
    competition = match_data.get('tavlingnamn', '')
    venue = match_data.get('anlaggningnamn', '')

    # Create content
    group_info_content = f"Group Name: {group_name}\n"
    group_info_content += f"Match: {match_number}\n"
    group_info_content += f"Competition: {competition}\n"
    group_info_content += f"Date & Time: {match_date} {match_time}\n"
    group_info_content += f"Venue: {venue}\n\n"

    # Add referee information with roles
    group_info_content += "Referees:\n"
    for referee in match_data.get('domaruppdraglista', []):
        name = referee.get('personnamn', '') or referee.get('namn', '')
        role = referee.get('domarrollnamn', '')
        if name:
            group_info_content += f"- {name} ({role})\n"

    group_info_filename = f"whatsapp_group_info_match_{match_id}.txt"
    temp_group_info_filepath = os.path.join(settings.temp_file_directory, group_info_filename)

    try:
        with open(temp_group_info_filepath, 'w', encoding='utf-8') as group_info_file:
            group_info_file.write(group_info_content)
        logger.info(f"Group info saved to temporary file: {temp_group_info_filepath}")
        return temp_group_info_filepath, group_info_filename
    except Exception as save_error:
        logger.error(f"Error saving group info to {temp_group_info_filepath}: {save_error}")
        logger.debug(f"File saving FAILED with error for: {temp_group_info_filepath}")
        return None, None


def create_gdrive_folder_path(match_data: MatchDict, match_id: int) -> str:
    """Create Google Drive folder path for match assets.
    
    Args:
        match_data: Match data dictionary
        match_id: Match ID
        
    Returns:
        Formatted folder path for Google Drive
    """
    match_date_formatted = match_data.get('speldatum', '')
    safe_label = f"{match_id}_{match_data['lag1namn'].replace(' ', '_')}_{match_data['lag2namn'].replace(' ', '_')}"
    
    return f"{settings.gdrive_folder_base}/{match_date_formatted}/Match_{safe_label}"
