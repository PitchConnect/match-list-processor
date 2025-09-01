"""Targeted tests to boost coverage for comprehensive test suite."""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from src.core.data_manager import MatchDataManager
from src.core.match_comparator import MatchComparator
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.services.avatar_service import WhatsAppAvatarService
from src.services.phonebook_service import FogisPhonebookSyncService
from src.services.storage_service import GoogleDriveStorageService
from src.utils.description_generator import generate_whatsapp_description
from src.utils.file_utils import create_gdrive_folder_path, extract_referee_names


@pytest.mark.unit
class TestMatchDataManager:
    """Test match data manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_manager = MatchDataManager(self.temp_dir)

    def test_data_manager_initialization(self):
        """Test data manager initialization."""
        assert self.data_manager.data_folder == self.temp_dir
        assert hasattr(self.data_manager, "file_path")

    def test_save_and_load_matches_raw_json(self, sample_match_data):
        """Test saving and loading raw JSON matches."""
        matches_json = json.dumps([sample_match_data])

        # Save matches as raw JSON string
        self.data_manager.save_current_matches_raw_json(matches_json)

        # Verify file exists
        assert os.path.exists(self.data_manager.file_path)

        # Load matches
        loaded_matches = self.data_manager.load_previous_matches()
        assert len(loaded_matches) == 1
        assert loaded_matches[0]["matchid"] == sample_match_data["matchid"]

    def test_save_current_matches(self, sample_match_data):
        """Test saving current matches."""
        matches = [sample_match_data]

        # Save current matches
        self.data_manager.save_current_matches(matches)

        # Verify file exists
        assert os.path.exists(self.data_manager.file_path)

        # Load and verify
        loaded_matches = self.data_manager.load_previous_matches()
        assert len(loaded_matches) == 1

    def test_load_previous_matches_no_file(self):
        """Test loading when no previous file exists."""
        # Should return empty list when file doesn't exist
        loaded_matches = self.data_manager.load_previous_matches()
        assert loaded_matches == []


@pytest.mark.unit
class TestMatchComparator:
    """Test match comparator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.comparator = MatchComparator()

    def test_convert_to_dict(self, sample_match_data):
        """Test converting match list to dictionary."""
        matches = [sample_match_data]
        result = self.comparator.convert_to_dict(matches)
        assert isinstance(result, dict)
        assert int(sample_match_data["matchid"]) in result

    def test_find_changes(self, sample_match_data):
        """Test finding changes between match lists."""
        previous_matches = [sample_match_data]
        current_matches = []  # Empty current matches

        new_matches, modified_matches, removed_matches = self.comparator.find_changes(
            previous_matches, current_matches
        )

        assert len(new_matches) == 0
        assert len(modified_matches) == 0
        assert len(removed_matches) == 1

    def test_is_match_modified(self, sample_match_data):
        """Test checking if match is modified."""
        # Same match should not be modified
        is_modified = self.comparator.is_match_modified(sample_match_data, sample_match_data)
        assert not is_modified

        # Different time should be modified
        modified_match = sample_match_data.copy()
        modified_match["tid"] = "2025-09-01T16:00:00"
        is_modified = self.comparator.is_match_modified(sample_match_data, modified_match)
        assert is_modified


@pytest.mark.unit
class TestMatchProcessor:
    """Test match processor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock services
        self.mock_avatar_service = Mock()
        self.mock_storage_service = Mock()
        self.mock_description_generator = Mock(return_value="Test description")

        self.processor = MatchProcessor(
            self.mock_avatar_service, self.mock_storage_service, self.mock_description_generator
        )

    def test_processor_initialization(self):
        """Test processor initialization."""
        assert self.processor.avatar_service == self.mock_avatar_service
        assert self.processor.storage_service == self.mock_storage_service
        assert hasattr(self.processor, "comparator")

    def test_process_match_new(self, sample_match_data):
        """Test processing a new match."""
        # Mock successful avatar and storage operations
        self.mock_avatar_service.create_avatar.return_value = (b"fake_image", None)
        self.mock_storage_service.upload_file.return_value = {
            "status": "success",
            "file_url": "https://example.com/file",
        }

        with patch("src.utils.file_utils.extract_referee_names", return_value=["Referee 1"]):
            result = self.processor.process_match(sample_match_data, 123, is_new=True)

            # Should return a processing result
            assert result is not None

    def test_process_match_modified(self, sample_match_data):
        """Test processing a modified match."""
        previous_match = sample_match_data.copy()
        modified_match = sample_match_data.copy()
        modified_match["avsparkstid"] = "16:00"

        # Mock services
        self.mock_avatar_service.create_avatar.return_value = (b"fake_image", None)
        self.mock_storage_service.upload_file.return_value = {
            "status": "success",
            "file_url": "https://example.com/file",
        }

        with patch("src.utils.file_utils.extract_referee_names", return_value=["Referee 1"]):
            result = self.processor.process_match(
                modified_match, 123, is_new=False, previous_match_data=previous_match
            )

            # Should return a processing result
            assert result is not None


@pytest.mark.unit
class TestApiClient:
    """Test API client functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = DockerNetworkApiClient()

    def test_client_initialization(self):
        """Test client initialization."""
        assert hasattr(self.client, "base_url")
        assert hasattr(self.client, "timeout")

    def test_fetch_matches_list_success(self, sample_match_data):
        """Test successful matches list fetch."""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = [sample_match_data]
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            matches = self.client.fetch_matches_list()
            assert len(matches) == 1
            assert matches[0]["matchid"] == sample_match_data["matchid"]

    def test_fetch_matches_list_error(self):
        """Test matches list fetch with error."""
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            with pytest.raises(Exception):
                self.client.fetch_matches_list()


@pytest.mark.unit
class TestAvatarService:
    """Test avatar service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = WhatsAppAvatarService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert hasattr(self.service, "api_key")
        assert hasattr(self.service, "base_url")

    def test_create_avatar_success(self):
        """Test successful avatar creation."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.content = b"fake_image_data"
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            image_data, error = self.service.create_avatar("Test description")
            assert image_data == b"fake_image_data"
            assert error is None

    def test_create_avatar_error(self):
        """Test avatar creation with error."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("API error")

            image_data, error = self.service.create_avatar("Test description")
            assert image_data is None
            assert error is not None


@pytest.mark.unit
class TestStorageService:
    """Test storage service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = GoogleDriveStorageService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert hasattr(self.service, "credentials_file")
        assert hasattr(self.service, "folder_id")

    def test_upload_file_success(self):
        """Test successful file upload."""
        with patch.object(self.service, "_get_drive_service") as mock_service:
            mock_drive = Mock()
            mock_file = Mock()
            mock_file.execute.return_value = {"id": "test-file-id"}
            mock_drive.files.return_value.create.return_value = mock_file
            mock_service.return_value = mock_drive

            result = self.service.upload_file("test.txt", b"test content")
            assert result["status"] == "success"
            assert "file_id" in result

    def test_upload_file_error(self):
        """Test file upload with error."""
        with patch.object(self.service, "_get_drive_service") as mock_service:
            mock_service.side_effect = Exception("Drive API error")

            result = self.service.upload_file("test.txt", b"test content")
            assert result["status"] == "error"
            assert "error" in result


@pytest.mark.unit
class TestPhonebookService:
    """Test phonebook service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = FogisPhonebookSyncService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert hasattr(self.service, "api_base_url")
        assert hasattr(self.service, "timeout")

    def test_sync_contacts_success(self, sample_match_data):
        """Test successful contact sync."""
        with patch("requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "success", "synced": 1}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = self.service.sync_contacts([sample_match_data])
            assert result is True

    def test_sync_contacts_error(self, sample_match_data):
        """Test contact sync with error."""
        with patch("requests.post") as mock_post:
            mock_post.side_effect = Exception("Sync error")

            result = self.service.sync_contacts([sample_match_data])
            assert result is False


@pytest.mark.unit
class TestUtilities:
    """Test utility functions."""

    def test_description_generator(self):
        """Test description generator function."""
        description = generate_whatsapp_description(
            "Team A", "Team B", "2025-09-01", "15:00", ["Referee 1"]
        )
        assert "Team A" in description
        assert "Team B" in description
        assert "2025-09-01" in description

    def test_file_utils_create_gdrive_folder_path(self):
        """Test creating Google Drive folder path."""
        path = create_gdrive_folder_path("Team A", "Team B", "2025-09-01")
        assert "Team A" in path
        assert "Team B" in path
        assert "2025-09-01" in path

    def test_file_utils_extract_referee_names(self, sample_match_data):
        """Test extracting referee names."""
        names = extract_referee_names(sample_match_data)
        assert isinstance(names, list)
        assert len(names) > 0
