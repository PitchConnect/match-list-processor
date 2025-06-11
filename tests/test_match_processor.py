"""Tests for match processing functionality."""

from unittest.mock import Mock, patch

import pytest

from src.core.match_processor import MatchProcessor


class TestMatchProcessor:
    """Test the MatchProcessor class."""

    def test_init(self, mock_avatar_service, mock_storage_service, mock_description_generator):
        """Test processor initialization."""
        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        assert processor.avatar_service == mock_avatar_service
        assert processor.storage_service == mock_storage_service
        assert processor.description_generator == mock_description_generator

    @patch("src.core.match_processor.save_description_to_file")
    @patch("src.core.match_processor.save_group_info_to_file")
    @patch("src.core.match_processor.save_avatar_to_file")
    @patch("src.core.match_processor.create_gdrive_folder_path")
    def test_process_match_success(
        self,
        mock_create_folder,
        mock_save_avatar,
        mock_save_group,
        mock_save_desc,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test successful match processing."""
        # Setup mocks
        mock_save_desc.return_value = "/tmp/desc.txt"
        mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
        mock_save_avatar.return_value = ("/tmp/avatar.png", "avatar.png")
        mock_create_folder.return_value = "test/folder"

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(sample_match_data, 12345, is_new=True)

        assert result is not None
        assert result["success"] is True
        assert result["error_message"] is None
        assert result["description_url"] == "http://example.com/file"
        assert result["group_info_url"] == "http://example.com/file"
        assert result["avatar_url"] == "http://example.com/file"

    def test_process_match_insufficient_referees(
        self,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing match with insufficient referees."""
        # Modify match data to have only one referee
        match_data = sample_match_data.copy()
        match_data["domaruppdraglista"] = [sample_match_data["domaruppdraglista"][0]]

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(match_data, 12345, is_new=True)

        assert result is None

    @patch("src.core.match_processor.save_description_to_file")
    def test_process_match_description_save_failure(
        self,
        mock_save_desc,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing match when description save fails."""
        mock_save_desc.return_value = None

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(sample_match_data, 12345, is_new=True)

        assert result is not None
        assert result["success"] is False
        assert "Failed to save description file" in result["error_message"]

    @patch("src.core.match_processor.save_description_to_file")
    @patch("src.core.match_processor.save_group_info_to_file")
    def test_process_match_group_info_save_failure(
        self,
        mock_save_group,
        mock_save_desc,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing match when group info save fails."""
        mock_save_desc.return_value = "/tmp/desc.txt"
        mock_save_group.return_value = (None, None)

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(sample_match_data, 12345, is_new=True)

        assert result is not None
        assert result["success"] is False
        assert "Failed to save group info file" in result["error_message"]

    @patch("src.core.match_processor.save_description_to_file")
    @patch("src.core.match_processor.save_group_info_to_file")
    def test_process_match_avatar_creation_failure(
        self,
        mock_save_group,
        mock_save_desc,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing match when avatar creation fails."""
        mock_save_desc.return_value = "/tmp/desc.txt"
        mock_save_group.return_value = ("/tmp/group.txt", "group.txt")

        # Mock avatar service to return error
        mock_avatar_service = Mock()
        mock_avatar_service.create_avatar.return_value = (None, "Avatar creation failed")

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(sample_match_data, 12345, is_new=True)

        assert result is not None
        assert result["success"] is False
        assert "Avatar creation failed" in result["error_message"]

    @patch("src.core.match_processor.save_description_to_file")
    @patch("src.core.match_processor.save_group_info_to_file")
    @patch("src.core.match_processor.save_avatar_to_file")
    def test_process_match_avatar_save_failure(
        self,
        mock_save_avatar,
        mock_save_group,
        mock_save_desc,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing match when avatar save fails."""
        mock_save_desc.return_value = "/tmp/desc.txt"
        mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
        mock_save_avatar.return_value = (None, None)

        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor.process_match(sample_match_data, 12345, is_new=True)

        assert result is not None
        assert result["success"] is False
        assert "Failed to save avatar file" in result["error_message"]

    def test_process_match_with_modifications(
        self,
        mock_avatar_service,
        mock_storage_service,
        mock_description_generator,
        sample_match_data,
    ):
        """Test processing modified match."""
        previous_match = sample_match_data.copy()
        previous_match["tid"] = "2025-06-14T14:00:00"

        with (
            patch("src.core.match_processor.save_description_to_file") as mock_save_desc,
            patch("src.core.match_processor.save_group_info_to_file") as mock_save_group,
            patch("src.core.match_processor.save_avatar_to_file") as mock_save_avatar,
            patch("src.core.match_processor.create_gdrive_folder_path") as mock_create_folder,
        ):

            mock_save_desc.return_value = "/tmp/desc.txt"
            mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
            mock_save_avatar.return_value = ("/tmp/avatar.png", "avatar.png")
            mock_create_folder.return_value = "test/folder"

            processor = MatchProcessor(
                mock_avatar_service, mock_storage_service, mock_description_generator
            )

            result = processor.process_match(
                sample_match_data, 12345, is_new=False, previous_match_data=previous_match
            )

            assert result is not None
            assert result["success"] is True

    def test_create_error_result(
        self, mock_avatar_service, mock_storage_service, mock_description_generator
    ):
        """Test creating error result."""
        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, mock_description_generator
        )

        result = processor._create_error_result("Test error message")

        assert result["success"] is False
        assert result["error_message"] == "Test error message"
        assert result["description_url"] is None
        assert result["group_info_url"] is None
        assert result["avatar_url"] is None
