"""Tests for the unified processor."""

import tempfile
import unittest
from unittest.mock import patch

from src.core.unified_processor import UnifiedMatchProcessor


class TestUnifiedMatchProcessor(unittest.TestCase):
    """Test cases for the UnifiedMatchProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary file for testing
        self.temp_file = tempfile.mktemp(suffix=".json")

        # Mock all the services to avoid external dependencies
        with (
            patch("src.core.unified_processor.MatchDataManager"),
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.MatchProcessor"),
        ):

            self.processor = UnifiedMatchProcessor(self.temp_file)

        # Sample match data
        self.sample_matches = [
            {
                "matchid": "12345",
                "matchnr": "1",
                "speldatum": "2025-09-01",
                "avsparkstid": "14:00",
                "lag1lagid": "100",
                "lag1namn": "Team A",
                "lag2lagid": "200",
                "lag2namn": "Team B",
                "anlaggningnamn": "Stadium A",
                "domaruppdraglista": [],
            }
        ]
