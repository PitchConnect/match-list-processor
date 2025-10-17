"""Interface definitions for external services."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from .custom_types import FilePath, MatchList, UploadResult


class ApiClientInterface(ABC):
    """Abstract interface for API clients."""

    @abstractmethod
    def fetch_matches_list(self) -> MatchList:
        """Fetch a list of matches from the API.

        Returns:
            List of match dictionaries.
        """
        pass


class AvatarServiceInterface(ABC):
    """Abstract interface for avatar creation services."""

    @abstractmethod
    def create_avatar(self, team1_id: int, team2_id: int) -> Tuple[Optional[bytes], Optional[str]]:
        """Create an avatar for the given team IDs.

        Args:
            team1_id: ID of the first team
            team2_id: ID of the second team

        Returns:
            Tuple of (avatar_data, error_message)
        """
        pass


class StorageServiceInterface(ABC):
    """Abstract interface for file storage services."""

    @abstractmethod
    def upload_file(
        self,
        file_path: FilePath,
        file_name: str,
        folder_path: str,
        mime_type: str,
    ) -> UploadResult:
        """Upload a file to storage.

        Args:
            file_path: Local path to the file
            file_name: Name for the uploaded file
            folder_path: Destination folder path
            mime_type: MIME type of the file

        Returns:
            Upload result with status and URL
        """
        pass
