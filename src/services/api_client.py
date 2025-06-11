"""API client service implementations."""

import logging
from typing import Optional

import requests

from ..interfaces import ApiClientInterface
from ..types import MatchList
from ..config import settings


logger = logging.getLogger(__name__)


class DockerNetworkApiClient(ApiClientInterface):
    """API client implementation that communicates with the fogis-api-client-service
    container over the Docker network using HTTP.
    """

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the API client.
        
        Args:
            base_url: Base URL for the API service. If None, uses config default.
        """
        self.base_url = base_url or settings.fogis_api_client_url
        self.matches_endpoint = f"{self.base_url}/matches"

    def fetch_matches_list(self) -> MatchList:
        """Fetch the list of matches from the API client service.
        
        Returns:
            List of match dictionaries.
        """
        logger.info(f"Fetching matches list from: {self.matches_endpoint}...")
        
        try:
            response = requests.get(self.matches_endpoint)
            response.raise_for_status()
            
            logger.info(
                f"API Client Container Response (Matches List Test - Status Code: {response.status_code})"
            )
            
            response_data = response.json()
            logger.debug(f"API Response Type for matches list: {type(response_data)}")
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching matches list from {self.matches_endpoint}: {e}")
            return []
