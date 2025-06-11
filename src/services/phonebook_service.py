"""Phonebook synchronization service implementation."""

import logging
from typing import Optional

import requests

from ..interfaces import PhonebookSyncInterface
from ..config import settings


logger = logging.getLogger(__name__)


class FogisPhonebookSyncService(PhonebookSyncInterface):
    """Service for synchronizing contacts with the phonebook."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the phonebook sync service.
        
        Args:
            base_url: Base URL for the sync service. If None, uses config default.
        """
        self.base_url = base_url or settings.phonebook_sync_service_url
        self.sync_endpoint = f"{self.base_url}/sync"

    def sync_contacts(self) -> bool:
        """Trigger contact synchronization.
        
        Returns:
            True if sync was successful, False otherwise
        """
        logger.info("Triggering contact sync with phonebook...")
        
        try:
            response = requests.post(self.sync_endpoint)
            
            if response.status_code == 200:
                logger.info("Contact sync process completed successfully.")
                return True
            else:
                logger.error(
                    f"Contact sync process failed. "
                    f"Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error triggering contact sync: {e}")
            return False
