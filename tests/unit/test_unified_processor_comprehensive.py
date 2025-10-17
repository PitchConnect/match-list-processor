"""Comprehensive unit tests for unified processor functionality."""

import time
from unittest.mock import Mock, patch

import pytest

from src.core.unified_processor import ProcessingResult, UnifiedMatchProcessor


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
