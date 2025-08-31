"""Integration tests for the match list processor."""

import json
import os
from unittest.mock import Mock, patch

from src.app import MatchListProcessorApp
from src.core.data_manager import MatchDataManager
from src.core.match_comparator import MatchComparator
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.utils.description_generator import generate_whatsapp_description


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_complete_workflow_with_new_matches(self, temp_data_dir, sample_matches_list):
        """Test complete workflow with new matches."""
        # Setup data manager with empty previous data
        data_manager = MatchDataManager(temp_data_dir, "test_matches.json")

        # Mock services
        mock_api_client = Mock()
        mock_api_client.fetch_matches_list.return_value = sample_matches_list

        mock_avatar_service = Mock()
        mock_avatar_service.create_avatar.return_value = (b"fake_image", None)

        mock_storage_service = Mock()
        mock_storage_service.upload_file.return_value = {
            "status": "success",
            "file_url": "http://example.com/file",
            "message": None,
        }

        mock_phonebook_service = Mock()
        mock_phonebook_service.sync_contacts.return_value = True

        # Create match processor
        match_processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, generate_whatsapp_description
        )

        # Create app and replace services
        app = MatchListProcessorApp()
        app.data_manager = data_manager
        app.api_client = mock_api_client
        app.avatar_service = mock_avatar_service
        app.storage_service = mock_storage_service
        app.phonebook_service = mock_phonebook_service
        app.match_processor = match_processor

        # Mock file operations
        with (
            patch("src.utils.file_utils.save_description_to_file") as mock_save_desc,
            patch("src.utils.file_utils.save_group_info_to_file") as mock_save_group,
            patch("src.utils.file_utils.save_avatar_to_file") as mock_save_avatar,
        ):

            mock_save_desc.return_value = "/tmp/desc.txt"
            mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
            mock_save_avatar.return_value = ("/tmp/avatar.png", "avatar.png")

            # Run the application
            app.run()

        # Verify that matches were processed
        mock_avatar_service.create_avatar.assert_called()
        mock_storage_service.upload_file.assert_called()

        # Verify that data was saved
        assert os.path.exists(data_manager.file_path)
        with open(data_manager.file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert len(saved_data) == 2

    def test_workflow_with_modified_matches(self, temp_data_dir, sample_matches_list):
        """Test workflow with modified matches."""
        # Setup data manager with previous data
        data_manager = MatchDataManager(temp_data_dir, "test_matches.json")

        # Save initial data
        initial_data = json.dumps(sample_matches_list, ensure_ascii=False)
        data_manager.save_current_matches_raw_json(initial_data)

        # Create modified version of matches
        modified_matches = []
        for match in sample_matches_list:
            modified_match = match.copy()
            modified_match["tid"] = "2025-06-14T16:00:00"  # Change time
            modified_matches.append(modified_match)

        # Mock services
        mock_api_client = Mock()
        mock_api_client.fetch_matches_list.return_value = modified_matches

        mock_avatar_service = Mock()
        mock_avatar_service.create_avatar.return_value = (b"fake_image", None)

        mock_storage_service = Mock()
        mock_storage_service.upload_file.return_value = {
            "status": "success",
            "file_url": "http://example.com/file",
            "message": None,
        }

        mock_phonebook_service = Mock()
        mock_phonebook_service.sync_contacts.return_value = True

        # Create match processor
        match_processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, generate_whatsapp_description
        )

        # Create app and replace services
        app = MatchListProcessorApp()
        app.data_manager = data_manager
        app.api_client = mock_api_client
        app.avatar_service = mock_avatar_service
        app.storage_service = mock_storage_service
        app.phonebook_service = mock_phonebook_service
        app.match_processor = match_processor

        # Mock file operations
        with (
            patch("src.utils.file_utils.save_description_to_file") as mock_save_desc,
            patch("src.utils.file_utils.save_group_info_to_file") as mock_save_group,
            patch("src.utils.file_utils.save_avatar_to_file") as mock_save_avatar,
        ):

            mock_save_desc.return_value = "/tmp/desc.txt"
            mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
            mock_save_avatar.return_value = ("/tmp/avatar.png", "avatar.png")

            # Run the application
            app.run()

        # Verify that modified matches were processed
        mock_avatar_service.create_avatar.assert_called()
        mock_storage_service.upload_file.assert_called()

    def test_workflow_with_insufficient_referees(self, temp_data_dir, sample_match_data):
        """Test workflow with matches having insufficient referees."""
        # Create match with only one referee
        match_with_one_referee = sample_match_data.copy()
        match_with_one_referee["domaruppdraglista"] = [sample_match_data["domaruppdraglista"][0]]

        # Mock services
        mock_api_client = Mock()
        mock_api_client.fetch_matches_list.return_value = [match_with_one_referee]

        mock_avatar_service = Mock()
        mock_storage_service = Mock()
        mock_phonebook_service = Mock()
        mock_phonebook_service.sync_contacts.return_value = True

        # Create match processor
        match_processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, generate_whatsapp_description
        )

        # Create app and replace services
        app = MatchListProcessorApp()
        app.data_manager = MatchDataManager(temp_data_dir, "test_matches.json")
        app.api_client = mock_api_client
        app.avatar_service = mock_avatar_service
        app.storage_service = mock_storage_service
        app.phonebook_service = mock_phonebook_service
        app.match_processor = match_processor

        # Run the application
        app.run()

        # Verify that avatar service was not called (insufficient referees)
        mock_avatar_service.create_avatar.assert_not_called()
        mock_storage_service.upload_file.assert_not_called()


class TestDataFlowIntegration:
    """Test data flow between components."""

    def test_data_manager_to_comparator_flow(self, temp_data_dir, sample_matches_list):
        """Test data flow from data manager to comparator."""
        # Setup data manager
        data_manager = MatchDataManager(temp_data_dir, "test_matches.json")

        # Save test data
        raw_json = json.dumps(sample_matches_list, ensure_ascii=False)
        data_manager.save_current_matches_raw_json(raw_json)

        # Load and parse data
        loaded_raw = data_manager.load_previous_matches_raw_json()
        parsed_list = data_manager.parse_raw_json_to_list(loaded_raw)

        # Convert to dictionary using comparator
        match_dict = MatchComparator.convert_to_dict(parsed_list)

        # Verify data integrity
        assert len(match_dict) == 2
        assert 6169105 in match_dict
        assert 6169106 in match_dict
        assert match_dict[6169105]["lag1namn"] == "IK Kongahälla"

    def test_api_client_to_comparator_flow(self, sample_matches_list):
        """Test data flow from API client to comparator."""
        # Set environment variable to allow API client unit testing
        with patch.dict(os.environ, {"PYTEST_API_CLIENT_UNIT_TEST": "1"}):
            # Mock API client
            with patch("src.services.api_client.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = sample_matches_list
                mock_get.return_value = mock_response

                # Fetch data using API client
                api_client = DockerNetworkApiClient()
                fetched_data = api_client.fetch_matches_list()

                # Convert using comparator
                match_dict = MatchComparator.convert_to_dict(fetched_data)

                # Verify data integrity
                assert len(match_dict) == 2
                assert isinstance(match_dict, dict)

    def test_comparator_to_processor_flow(self, sample_matches_list):
        """Test data flow from comparator to processor."""
        # Convert matches to dictionary
        current_matches = MatchComparator.convert_to_dict(sample_matches_list)
        previous_matches = {}

        # Detect changes
        new_ids, removed_ids, common_ids = MatchComparator.detect_changes(
            previous_matches, current_matches
        )

        # Mock services for processor
        mock_avatar_service = Mock()
        mock_avatar_service.create_avatar.return_value = (b"fake_image", None)

        mock_storage_service = Mock()
        mock_storage_service.upload_file.return_value = {
            "status": "success",
            "file_url": "http://example.com/file",
            "message": None,
        }

        # Create processor
        processor = MatchProcessor(
            mock_avatar_service, mock_storage_service, generate_whatsapp_description
        )

        # Process new matches
        with (
            patch("src.utils.file_utils.save_description_to_file") as mock_save_desc,
            patch("src.utils.file_utils.save_group_info_to_file") as mock_save_group,
            patch("src.utils.file_utils.save_avatar_to_file") as mock_save_avatar,
        ):

            mock_save_desc.return_value = "/tmp/desc.txt"
            mock_save_group.return_value = ("/tmp/group.txt", "group.txt")
            mock_save_avatar.return_value = ("/tmp/avatar.png", "avatar.png")

            for match_id in new_ids:
                match_data = current_matches[match_id]
                result = processor.process_match(match_data, match_id, is_new=True)
                assert result is not None
                assert result["success"] is True
