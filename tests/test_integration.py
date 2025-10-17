"""Integration tests for the match list processor."""

import os
from unittest.mock import Mock, patch

from src.core.match_comparator import MatchComparator
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.utils.description_generator import generate_whatsapp_description


class TestEndToEndIntegration:
    """End-to-end integration tests."""

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
