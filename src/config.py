"""Configuration management for the match list processor."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Data storage
    data_folder: str = Field(default="/data", validation_alias="DATA_FOLDER")
    previous_matches_file: str = Field(
        default="previous_matches.json", validation_alias="PREVIOUS_MATCHES_FILE"
    )

    # Service URLs
    fogis_api_client_url: str = Field(
        default="http://fogis-api-client-service:8080", validation_alias="FOGIS_API_CLIENT_URL"
    )
    whatsapp_avatar_service_url: str = Field(
        default="http://whatsapp-avatar-service:5002",
        validation_alias="WHATSAPP_AVATAR_SERVICE_URL",
    )
    google_drive_service_url: str = Field(
        default="http://google-drive-service:5000", validation_alias="GOOGLE_DRIVE_SERVICE_URL"
    )
    phonebook_sync_service_url: str = Field(
        default="http://fogis-calendar-phonebook-sync:5003",
        validation_alias="PHONEBOOK_SYNC_SERVICE_URL",
    )

    # Processing settings
    min_referees_for_whatsapp: int = Field(default=2, validation_alias="MIN_REFEREES_FOR_WHATSAPP")
    temp_file_directory: str = Field(
        default="/tmp", validation_alias="TEMP_FILE_DIRECTORY"  # nosec B108
    )

    # Google Drive settings
    gdrive_folder_base: str = Field(
        default="WhatsApp_Group_Assets", validation_alias="GDRIVE_FOLDER_BASE"
    )

    # Logging
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s", validation_alias="LOG_FORMAT"
    )


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
