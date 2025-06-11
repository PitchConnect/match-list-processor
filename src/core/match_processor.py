"""Core match processing logic."""

import logging
from typing import Callable, Optional

from ..config import settings
from ..interfaces import AvatarServiceInterface, StorageServiceInterface
from ..types import MatchDict, ProcessingResult, UploadResult
from ..utils.file_utils import (
    create_gdrive_folder_path,
    extract_referee_names,
    save_avatar_to_file,
    save_description_to_file,
    save_group_info_to_file,
)
from .match_comparator import MatchComparator

logger = logging.getLogger(__name__)


class MatchProcessor:
    """Handles processing of individual matches."""

    def __init__(
        self,
        avatar_service: AvatarServiceInterface,
        storage_service: StorageServiceInterface,
        description_generator: Callable[[MatchDict], str],
    ):
        """Initialize the match processor.

        Args:
            avatar_service: Service for creating avatars
            storage_service: Service for uploading files
            description_generator: Function/service for generating descriptions
        """
        self.avatar_service = avatar_service
        self.storage_service = storage_service
        self.description_generator = description_generator

    def process_match(
        self,
        match_data: MatchDict,
        match_id: int,
        is_new: bool = True,
        previous_match_data: Optional[MatchDict] = None,
    ) -> Optional[ProcessingResult]:
        """Process a match (new or modified).

        Args:
            match_data: Current match data
            match_id: Match ID
            is_new: Whether this is a new match
            previous_match_data: Previous match data for comparison (if modified)

        Returns:
            Processing result with URLs and status
        """
        action_type = "New" if is_new else "Modified"
        logger.info(
            f"  - {action_type} Match ID: {match_id}, "
            f"Teams: {match_data['lag1namn']} vs {match_data['lag2namn']}, "
            f"Date: {match_data['speldatum']}, Time: {match_data['avsparkstid']}"
        )

        # Log modifications if this is a modified match
        if not is_new and previous_match_data:
            modifications = MatchComparator.get_modification_details(
                previous_match_data, match_data
            )
            for modification in modifications:
                logger.info(f"    - {modification}")

        # Check number of referees
        referees = match_data.get("domaruppdraglista", [])
        if len(referees) < settings.min_referees_for_whatsapp:
            logger.info(
                f"  Match ID {match_id} has less than {settings.min_referees_for_whatsapp} "
                f"referees. Skipping WhatsApp group creation/update."
            )
            return None

        try:
            # Generate WhatsApp group description
            description_text = self.description_generator(match_data)
            logger.info(f"  Generated WhatsApp group description:\n{description_text}")

            # Save description to temporary file
            temp_description_filepath = save_description_to_file(description_text, match_id)
            if not temp_description_filepath:
                return self._create_error_result("Failed to save description file")

            # Save group info to temporary file
            temp_group_info_filepath, group_info_filename = save_group_info_to_file(
                match_data, match_id
            )
            if not temp_group_info_filepath:
                return self._create_error_result("Failed to save group info file")

            # Extract referee names
            referee_names_list = extract_referee_names(match_data)
            logger.info(f"  Extracted referee names: {referee_names_list}")

            # Create and save avatar
            team1_id = match_data.get("lag1foreningid")
            team2_id = match_data.get("lag2foreningid")

            if team1_id is None or team2_id is None:
                return self._create_error_result("Missing team IDs for avatar creation")

            avatar_data, avatar_error = self.avatar_service.create_avatar(team1_id, team2_id)

            if not avatar_data:
                return self._create_error_result(f"Avatar creation failed: {avatar_error}")

            temp_avatar_filepath, avatar_filename = save_avatar_to_file(avatar_data, match_id)
            if not temp_avatar_filepath or not avatar_filename:
                return self._create_error_result("Failed to save avatar file")

            # Create Google Drive folder path
            gdrive_folder_path = create_gdrive_folder_path(match_data, match_id)

            # Upload files to Google Drive
            description_result = self._upload_file(
                temp_description_filepath,
                f"whatsapp_group_description_match_{match_id}.txt",
                gdrive_folder_path,
                "text/plain",
            )

            if not group_info_filename:
                return self._create_error_result("Failed to get group info filename")

            group_info_result = self._upload_file(
                temp_group_info_filepath, group_info_filename, gdrive_folder_path, "text/plain"
            )

            avatar_result = self._upload_file(
                temp_avatar_filepath, avatar_filename, gdrive_folder_path, "image/png"
            )

            return {
                "description_url": description_result.get("file_url"),
                "group_info_url": group_info_result.get("file_url"),
                "avatar_url": avatar_result.get("file_url"),
                "success": True,
                "error_message": None,
            }

        except Exception as e:
            error_msg = f"Error processing match {match_id}: {e}"
            logger.error(error_msg)
            return self._create_error_result(error_msg)

    def _upload_file(
        self, file_path: str, file_name: str, folder_path: str, mime_type: str
    ) -> UploadResult:
        """Upload a file using the storage service."""
        return self.storage_service.upload_file(file_path, file_name, folder_path, mime_type)

    def _create_error_result(self, error_message: str) -> ProcessingResult:
        """Create an error result."""
        return {
            "description_url": None,
            "group_info_url": None,
            "avatar_url": None,
            "success": False,
            "error_message": error_message,
        }
