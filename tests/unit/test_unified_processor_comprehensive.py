"""Comprehensive unit tests for unified processor functionality."""

from unittest.mock import patch

from src.core.unified_processor import UnifiedMatchProcessor


class TestUnifiedProcessorCore:
    """Test core unified processor functionality."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            self.processor = UnifiedMatchProcessor()
