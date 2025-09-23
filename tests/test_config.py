"""Tests for configuration management."""

import os
import tempfile
from unittest.mock import patch

from src.config import Settings, get_settings


class TestSettings:
    """Test the Settings configuration class."""

    def test_default_settings(self):
        """Test default configuration values."""
        # Clear any environment variables that might interfere
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.data_folder == "/data"
        assert settings.previous_matches_file == "previous_matches.json"
        assert settings.fogis_api_client_url == "http://fogis-api-client-service:8080"
        assert settings.whatsapp_avatar_service_url == "http://whatsapp-avatar-service:5002"
        assert settings.google_drive_service_url == "http://google-drive-service:5000"
        assert settings.phonebook_sync_service_url == "http://fogis-calendar-phonebook-sync:5003"
        assert settings.min_referees_for_whatsapp == 2
        assert settings.temp_file_directory == "/tmp"
        assert settings.gdrive_folder_base == "WhatsApp_Group_Assets"
        assert settings.log_level == "INFO"

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "DATA_FOLDER": "/custom/data",
                "MIN_REFEREES_FOR_WHATSAPP": "3",
                "LOG_LEVEL": "DEBUG",
            },
        ):
            settings = Settings()

            assert settings.data_folder == "/custom/data"
            assert settings.min_referees_for_whatsapp == 3
            assert settings.log_level == "DEBUG"

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DATA_FOLDER=/env/data\n")
            f.write("TEMP_FILE_DIRECTORY=/env/tmp\n")
            env_file = f.name

        try:
            # Clear environment variables to ensure we're testing file loading
            with patch.dict(os.environ, {}, clear=True):
                settings = Settings(_env_file=env_file)
                assert settings.data_folder == "/env/data"
                assert settings.temp_file_directory == "/env/tmp"
        finally:
            os.unlink(env_file)

    def test_get_settings_function(self):
        """Test the get_settings function."""
        # Clear environment variables to test default behavior
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()
            assert isinstance(settings, Settings)
            assert settings.data_folder == "/data"
