"""Storage service implementation."""

import logging
from typing import Optional

import requests

from ..interfaces import StorageServiceInterface
from ..types import UploadResult, FilePath
from ..config import settings


logger = logging.getLogger(__name__)


class GoogleDriveStorageService(StorageServiceInterface):
    """Service for uploading files to Google Drive."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the storage service.
        
        Args:
            base_url: Base URL for the storage service. If None, uses config default.
        """
        self.base_url = base_url or settings.google_drive_service_url
        self.upload_endpoint = f"{self.base_url}/upload_file"

    def upload_file(
        self, 
        file_path: FilePath, 
        file_name: str, 
        folder_path: str, 
        mime_type: str
    ) -> UploadResult:
        """Upload a file to Google Drive.
        
        Args:
            file_path: Local path to the file
            file_name: Name for the uploaded file
            folder_path: Destination folder path
            mime_type: MIME type of the file
            
        Returns:
            Upload result with status and URL
        """
        try:
            with open(file_path, 'rb') as file_obj:
                files = {'file': (file_name, file_obj, mime_type)}
                data = {'folder_path': folder_path}
                
                response = requests.post(self.upload_endpoint, files=files, data=data)
                response.raise_for_status()
                
                result = response.json()
                
                if result.get('status') == 'success':
                    file_url = result.get('file_url')
                    logger.info(f"File uploaded to Google Drive. URL: {file_url}")
                    return {
                        'status': 'success',
                        'message': None,
                        'file_url': file_url
                    }
                else:
                    error_msg = (
                        f"Google Drive upload FAILED. "
                        f"Status: {result.get('status')}, "
                        f"Message: {result.get('message')}"
                    )
                    logger.error(error_msg)
                    return {
                        'status': 'error',
                        'message': error_msg,
                        'file_url': None
                    }
                    
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error uploading to Google Drive: {e}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'file_url': None
            }
        except Exception as e:
            error_msg = f"Error uploading to Google Drive: {e}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message': error_msg,
                'file_url': None
            }
