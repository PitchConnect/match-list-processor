"""Tests for service implementations."""

import os
from unittest.mock import Mock, mock_open, patch

import requests

from src.services.api_client import DockerNetworkApiClient
from src.services.avatar_service import WhatsAppAvatarService
from src.services.phonebook_service import FogisPhonebookSyncService
from src.services.storage_service import GoogleDriveStorageService


class TestDockerNetworkApiClient:
    """Test the DockerNetworkApiClient class."""

    def setup_method(self):
        """Set up test environment."""
        # Enable unit test mode for API client
        os.environ["PYTEST_API_CLIENT_UNIT_TEST"] = "1"

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up environment variable
        os.environ.pop("PYTEST_API_CLIENT_UNIT_TEST", None)

    def test_init_default_url(self):
        """Test initialization with default URL."""
        client = DockerNetworkApiClient()
        assert client.base_url == "http://fogis-api-client-service:8080"
        assert client.matches_endpoint == "http://fogis-api-client-service:8080/matches"

    def test_init_custom_url(self):
        """Test initialization with custom URL."""
        custom_url = "http://custom-api:9000"
        client = DockerNetworkApiClient(custom_url)
        assert client.base_url == custom_url
        assert client.matches_endpoint == f"{custom_url}/matches"

    @patch("src.services.api_client.requests.get")
    def test_fetch_matches_list_success(self, mock_get, sample_matches_list):
        """Test successful fetch of matches list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_matches_list
        mock_get.return_value = mock_response

        client = DockerNetworkApiClient()
        result = client.fetch_matches_list()

        assert result == sample_matches_list
        mock_get.assert_called_once_with("http://fogis-api-client-service:8080/matches", timeout=30)

    @patch("src.services.api_client.requests.get")
    def test_fetch_matches_list_http_error(self, mock_get):
        """Test fetch with HTTP error."""
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        client = DockerNetworkApiClient()
        result = client.fetch_matches_list()

        assert result == []

    @patch("src.services.api_client.requests.get")
    def test_fetch_matches_list_connection_error(self, mock_get):
        """Test fetch with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = DockerNetworkApiClient()
        result = client.fetch_matches_list()

        assert result == []


class TestWhatsAppAvatarService:
    """Test the WhatsAppAvatarService class."""

    def test_init_default_url(self):
        """Test initialization with default URL."""
        service = WhatsAppAvatarService()
        assert service.base_url == "http://whatsapp-avatar-service:5002"
        assert service.create_endpoint == "http://whatsapp-avatar-service:5002/create_avatar"

    def test_init_custom_url(self):
        """Test initialization with custom URL."""
        custom_url = "http://custom-avatar:6000"
        service = WhatsAppAvatarService(custom_url)
        assert service.base_url == custom_url
        assert service.create_endpoint == f"{custom_url}/create_avatar"

    @patch("src.services.avatar_service.requests.post")
    def test_create_avatar_success(self, mock_post):
        """Test successful avatar creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = b"fake_image_data"
        mock_post.return_value = mock_response

        service = WhatsAppAvatarService()
        avatar_data, error = service.create_avatar(123, 456)

        assert avatar_data == b"fake_image_data"
        assert error is None
        mock_post.assert_called_once()

    @patch("src.services.avatar_service.requests.post")
    def test_create_avatar_wrong_content_type(self, mock_post):
        """Test avatar creation with wrong content type."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "Error page"
        mock_post.return_value = mock_response

        service = WhatsAppAvatarService()
        avatar_data, error = service.create_avatar(123, 456)

        assert avatar_data is None
        assert "Unexpected Content-Type" in error

    @patch("src.services.avatar_service.requests.post")
    def test_create_avatar_request_error(self, mock_post):
        """Test avatar creation with request error."""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        service = WhatsAppAvatarService()
        avatar_data, error = service.create_avatar(123, 456)

        assert avatar_data is None
        assert "Error calling avatar service" in error


class TestGoogleDriveStorageService:
    """Test the GoogleDriveStorageService class."""

    def test_init_default_url(self):
        """Test initialization with default URL."""
        service = GoogleDriveStorageService()
        assert service.base_url == "http://google-drive-service:5000"
        assert service.upload_endpoint == "http://google-drive-service:5000/upload_file"

    @patch("src.services.storage_service.requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"file_content")
    def test_upload_file_success(self, mock_file, mock_post, temp_data_dir):
        """Test successful file upload."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "file_url": "http://drive.google.com/file/123",
        }
        mock_post.return_value = mock_response

        service = GoogleDriveStorageService()
        result = service.upload_file("/fake/path/file.txt", "file.txt", "test/folder", "text/plain")

        assert result["status"] == "success"
        assert result["file_url"] == "http://drive.google.com/file/123"
        assert result["message"] is None

    @patch("src.services.storage_service.requests.post")
    @patch("builtins.open", new_callable=mock_open, read_data=b"file_content")
    def test_upload_file_failure(self, mock_file, mock_post):
        """Test file upload failure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "error", "message": "Upload failed"}
        mock_post.return_value = mock_response

        service = GoogleDriveStorageService()
        result = service.upload_file("/fake/path/file.txt", "file.txt", "test/folder", "text/plain")

        assert result["status"] == "error"
        assert "Upload failed" in result["message"]
        assert result["file_url"] is None

    @patch("src.services.storage_service.requests.post")
    @patch("builtins.open", side_effect=FileNotFoundError("No such file or directory"))
    def test_upload_file_request_error(self, mock_file, mock_post):
        """Test file upload with request error."""
        service = GoogleDriveStorageService()
        result = service.upload_file("/fake/path/file.txt", "file.txt", "test/folder", "text/plain")

        assert result["status"] == "error"
        assert "Error uploading to Google Drive" in result["message"]
        assert result["file_url"] is None


class TestFogisPhonebookSyncService:
    """Test the FogisPhonebookSyncService class."""

    def test_init_default_url(self):
        """Test initialization with default URL."""
        service = FogisPhonebookSyncService()
        assert service.base_url == "http://fogis-calendar-phonebook-sync:5003"
        assert service.sync_endpoint == "http://fogis-calendar-phonebook-sync:5003/sync"

    @patch("src.services.phonebook_service.requests.post")
    def test_sync_contacts_success(self, mock_post):
        """Test successful contact sync."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        service = FogisPhonebookSyncService()
        result = service.sync_contacts()

        assert result is True
        mock_post.assert_called_once_with(
            "http://fogis-calendar-phonebook-sync:5003/sync", timeout=30
        )

    @patch("src.services.phonebook_service.requests.post")
    def test_sync_contacts_failure(self, mock_post):
        """Test contact sync failure."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_post.return_value = mock_response

        service = FogisPhonebookSyncService()
        result = service.sync_contacts()

        assert result is False

    @patch("src.services.phonebook_service.requests.post")
    def test_sync_contacts_request_error(self, mock_post):
        """Test contact sync with request error."""
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

        service = FogisPhonebookSyncService()
        result = service.sync_contacts()

        assert result is False
