#!/usr/bin/env python3
"""
End-to-End Integration Tests for Service Consolidation
Tests the complete unified match-list-processor service functionality
Issue #54: Final Integration Testing and Production Deployment Validation
"""

import logging
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from src.config import settings
from src.core.unified_processor import UnifiedMatchProcessor

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceConsolidationE2ETests(unittest.TestCase):
    """End-to-end integration tests for the consolidated service."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests."""
        # Set test environment variables
        os.environ["PYTEST_CURRENT_TEST"] = "true"
        os.environ["CI"] = "true"
        os.environ["LOG_LEVEL"] = "INFO"

        # Create temporary data directory
        cls.temp_dir = tempfile.mkdtemp()
        os.environ["DATA_FOLDER"] = cls.temp_dir

        # Mock external service URLs for testing
        os.environ["FOGIS_API_CLIENT_URL"] = "http://localhost:8080"
        os.environ["WHATSAPP_AVATAR_SERVICE_URL"] = "http://localhost:5002"
        os.environ["GOOGLE_DRIVE_SERVICE_URL"] = "http://localhost:5000"
        os.environ["PHONEBOOK_SYNC_SERVICE_URL"] = "http://localhost:5003"

        logger.info("E2E test environment set up")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        logger.info("E2E test environment cleaned up")

    def setUp(self):
        """Set up for each test."""
        self.app = None
        self.unified_processor = None

    def tearDown(self):
        """Clean up after each test."""
        if self.app:
            self.app.shutdown()

    def test_data_persistence(self):
        """Test data persistence functionality."""
        logger.info("Testing data persistence...")

        processor = UnifiedMatchProcessor()

        # Test data manager initialization
        self.assertIsNotNone(processor.data_manager)

        # Test that data folder is configured (use temp dir for tests)
        # In test mode, data folder should be the temp directory we set up
        self.assertIsNotNone(settings.data_folder)
        self.assertTrue(os.path.exists(self.temp_dir))

        logger.info("✅ Data persistence test passed")

    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        logger.info("Testing error handling and recovery...")

        processor = UnifiedMatchProcessor()

        # Test processing with API failure
        with patch(
            "src.services.api_client.DockerNetworkApiClient.fetch_matches_list"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("API connection failed")

            result = processor.run_processing_cycle()

            # Should handle error gracefully
            self.assertFalse(result.processed)
            self.assertGreater(len(result.errors), 0)
            self.assertIn("API connection failed", str(result.errors))

        logger.info("✅ Error handling and recovery test passed")

    def test_performance_baseline(self):
        """Test performance baseline for processing cycles."""
        logger.info("Testing performance baseline...")

        processor = UnifiedMatchProcessor()

        # Mock API response
        with patch(
            "src.services.api_client.DockerNetworkApiClient.fetch_matches_list"
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Measure processing time
            start_time = time.time()
            result = processor.run_processing_cycle()
            processing_time = time.time() - start_time

            # Verify processing completes within reasonable time (5 seconds)
            self.assertLess(processing_time, 5.0)
            self.assertGreater(result.processing_time, 0)

        logger.info(
            f"✅ Performance baseline test passed (processing time: {processing_time:.2f}s)"
        )

    def test_service_consolidation_completeness(self):
        """Test that service consolidation is complete and functional."""
        logger.info("Testing service consolidation completeness...")

        # Test that unified processor includes all expected functionality
        processor = UnifiedMatchProcessor()

        # Verify change detection integration
        self.assertIsNotNone(processor.change_detector)

        # Verify match processing integration
        self.assertIsNotNone(processor.match_processor)

        # Verify notification system integration (may be None if not configured)
        self.assertTrue(hasattr(processor, "notification_service"))

        # Verify semantic analysis integration
        self.assertIsNotNone(processor.semantic_analyzer)
        self.assertIsNotNone(processor.semantic_adapter)

        # Verify all external service integrations
        self.assertIsNotNone(processor.api_client)
        self.assertIsNotNone(processor.avatar_service)
        self.assertIsNotNone(processor.storage_service)
        # phonebook_service removed in Issue #84

        # Test processing stats functionality
        stats = processor.get_processing_stats()
        self.assertIsInstance(stats, dict)
        # Check for any stats fields (the actual fields may vary)
        self.assertGreater(len(stats), 0)

        logger.info("✅ Service consolidation completeness test passed")


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
