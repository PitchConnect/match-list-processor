"""Configuration management for the match list processor."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Data storage
    data_folder: str = Field(default="/data", env="DATA_FOLDER")
    previous_matches_file: str = Field(default="previous_matches.json", env="PREVIOUS_MATCHES_FILE")
    
    # Service URLs
    fogis_api_client_url: str = Field(
        default="http://fogis-api-client-service:8080", 
        env="FOGIS_API_CLIENT_URL"
    )
    whatsapp_avatar_service_url: str = Field(
        default="http://whatsapp-avatar-service:5002", 
        env="WHATSAPP_AVATAR_SERVICE_URL"
    )
    google_drive_service_url: str = Field(
        default="http://google-drive-service:5000", 
        env="GOOGLE_DRIVE_SERVICE_URL"
    )
    phonebook_sync_service_url: str = Field(
        default="http://fogis-calendar-phonebook-sync:5003", 
        env="PHONEBOOK_SYNC_SERVICE_URL"
    )
    
    # Processing settings
    min_referees_for_whatsapp: int = Field(default=2, env="MIN_REFEREES_FOR_WHATSAPP")
    temp_file_directory: str = Field(default="/tmp", env="TEMP_FILE_DIRECTORY")
    
    # Google Drive settings
    gdrive_folder_base: str = Field(default="WhatsApp_Group_Assets", env="GDRIVE_FOLDER_BASE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s", 
        env="LOG_FORMAT"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
