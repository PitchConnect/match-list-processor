"""Avatar service implementation."""

import logging
from typing import Optional, Tuple

import requests

from ..interfaces import AvatarServiceInterface
from ..config import settings


logger = logging.getLogger(__name__)


class WhatsAppAvatarService(AvatarServiceInterface):
    """Service for creating WhatsApp group avatars."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the avatar service.
        
        Args:
            base_url: Base URL for the avatar service. If None, uses config default.
        """
        self.base_url = base_url or settings.whatsapp_avatar_service_url
        self.create_endpoint = f"{self.base_url}/create_avatar"

    def create_avatar(self, team1_id: int, team2_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """Create an avatar for the given team IDs.
        
        Args:
            team1_id: ID of the first team
            team2_id: ID of the second team
            
        Returns:
            Tuple of (avatar_data, error_message)
        """
        payload = {
            "team1_id": str(team1_id),
            "team2_id": str(team2_id)
        }
        
        logger.info(f"Creating avatar for teams {team1_id} vs {team2_id}...")
        
        try:
            response = requests.post(self.create_endpoint, json=payload, stream=True)
            response.raise_for_status()

            if response.headers.get('Content-Type') == 'image/png':
                avatar_data = response.content
                logger.debug(f"Avatar image data length: {len(avatar_data)} bytes")
                return avatar_data, None
            else:
                error_msg = (
                    f"Unexpected Content-Type from avatar service: "
                    f"{response.headers.get('Content-Type')}"
                )
                logger.error(error_msg)
                logger.error(f"Response content: {response.text[:100]}...")
                return None, error_msg
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling avatar service: {e}"
            logger.error(error_msg)
            return None, error_msg
