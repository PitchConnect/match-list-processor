"""Tests for utility functions."""

from unittest.mock import mock_open, patch

from src.utils.description_generator import (
    create_example_match_details,
    generate_whatsapp_description,
)
from src.utils.file_utils import (
    create_gdrive_folder_path,
    extract_referee_names,
    save_avatar_to_file,
    save_description_to_file,
    save_group_info_to_file,
)


class TestFileUtils:
    """Test file utility functions."""

    def test_extract_referee_names(self, sample_match_data):
        """Test extracting referee names from match data."""
        names = extract_referee_names(sample_match_data)

        assert len(names) == 2
        assert "John Doe" in names
        assert "Jane Smith" in names

    def test_extract_referee_names_empty_list(self):
        """Test extracting referee names with empty referee list."""
        match_data = {"domaruppdraglista": []}
        names = extract_referee_names(match_data)

        assert names == []

    def test_extract_referee_names_missing_names(self):
        """Test extracting referee names with missing name fields."""
        match_data = {
            "domaruppdraglista": [
                {"domarid": 1, "domarrollnamn": "Huvuddomare"},
                {
                    "domarid": 2,
                    "personnamn": "",
                    "namn": "",
                    "domarrollnamn": "Assistent",
                },
            ]
        }
        names = extract_referee_names(match_data)

        assert names == []

    def test_extract_referee_names_fallback_to_namn(self):
        """Test extracting referee names with fallback to 'namn' field."""
        match_data = {
            "domaruppdraglista": [
                {"domarid": 1, "namn": "John Doe", "domarrollnamn": "Huvuddomare"}
            ]
        }
        names = extract_referee_names(match_data)

        assert names == ["John Doe"]

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.file_utils.settings")
    def test_save_description_to_file_success(self, mock_settings, mock_file):
        """Test successful description file saving."""
        mock_settings.temp_file_directory = "/tmp"

        result = save_description_to_file("Test description", 12345)

        assert result == "/tmp/whatsapp_group_description_match_12345.txt"
        mock_file.assert_called_once_with(
            "/tmp/whatsapp_group_description_match_12345.txt", "w", encoding="utf-8"
        )
        mock_file().write.assert_called_once_with("Test description")

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("src.utils.file_utils.settings")
    def test_save_description_to_file_error(self, mock_settings, mock_file):
        """Test description file saving with error."""
        mock_settings.temp_file_directory = "/tmp"

        result = save_description_to_file("Test description", 12345)

        assert result is None

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.file_utils.settings")
    def test_save_avatar_to_file_success(self, mock_settings, mock_file):
        """Test successful avatar file saving."""
        mock_settings.temp_file_directory = "/tmp"

        file_path, filename = save_avatar_to_file(b"image_data", 12345)

        assert file_path == "/tmp/whatsapp_group_avatar_match_12345.png"
        assert filename == "whatsapp_group_avatar_match_12345.png"
        mock_file.assert_called_once_with("/tmp/whatsapp_group_avatar_match_12345.png", "wb")
        mock_file().write.assert_called_once_with(b"image_data")

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("src.utils.file_utils.settings")
    def test_save_avatar_to_file_error(self, mock_settings, mock_file):
        """Test avatar file saving with error."""
        mock_settings.temp_file_directory = "/tmp"

        file_path, filename = save_avatar_to_file(b"image_data", 12345)

        assert file_path is None
        assert filename is None

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.utils.file_utils.settings")
    def test_save_group_info_to_file_success(self, mock_settings, mock_file, sample_match_data):
        """Test successful group info file saving."""
        mock_settings.temp_file_directory = "/tmp"

        file_path, filename = save_group_info_to_file(sample_match_data, 12345)

        assert file_path == "/tmp/whatsapp_group_info_match_12345.txt"
        assert filename == "whatsapp_group_info_match_12345.txt"

        # Check that the content includes expected information
        written_content = mock_file().write.call_args[0][0]
        assert "IK Kongahälla - Motala AIF FK" in written_content
        assert "John Doe" in written_content
        assert "Jane Smith" in written_content
        assert "2025-06-14" in written_content

    def test_create_gdrive_folder_path(self, sample_match_data):
        """Test creating Google Drive folder path."""
        with patch("src.utils.file_utils.settings") as mock_settings:
            mock_settings.gdrive_folder_base = "WhatsApp_Group_Assets"

            folder_path = create_gdrive_folder_path(sample_match_data, 12345)

            expected = "WhatsApp_Group_Assets/2025-06-14/Match_12345_IK_Kongahälla_Motala_AIF_FK"
            assert folder_path == expected


class TestDescriptionGenerator:
    """Test description generation utilities."""

    def test_generate_whatsapp_description(self, sample_match_data):
        """Test generating WhatsApp description."""
        description = generate_whatsapp_description(sample_match_data)

        assert "*IK Kongahälla - Motala AIF FK*" in description
        assert "_Div 2 Norra Götaland, herr 2025_" in description
        assert "Kongevi 1 Konstgräs" in description
        assert "https://www.svenskfotboll.se/matchfakta/match?matchId=6169105" in description
        assert "This group is for communication among the referee team" in description

    def test_generate_whatsapp_description_missing_fields(self):
        """Test generating description with missing fields."""
        match_data = {"matchid": 123, "lag1namn": "Team A", "lag2namn": "Team B"}

        description = generate_whatsapp_description(match_data)

        assert "*Team A - Team B*" in description
        assert "_Competition N/A_" in description
        assert "Venue N/A" in description
        assert "https://www.svenskfotboll.se/matchfakta/match?matchId=123" in description

    def test_create_example_match_details(self):
        """Test creating example match details."""
        example = create_example_match_details()

        assert example["matchid"] == 6169105
        assert example["lag1namn"] == "IK Kongahälla"
        assert example["lag2namn"] == "Motala AIF FK"
        assert example["tavlingnamn"] == "Div 2 Norra Götaland, herr 2025"
        assert example["anlaggningnamn"] == "Kongevi 1 Konstgräs"
