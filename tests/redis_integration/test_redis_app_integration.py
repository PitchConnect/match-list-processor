#!/usr/bin/env python3
"""
Tests for Redis App Integration

This module tests the Redis application integration functionality.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis app integration testing for CI/CD coverage
"""

import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.redis_integration.app_integration import (
    MatchProcessorRedisIntegration,
    add_redis_integration_to_processor,
    create_redis_integration,
)


class TestMatchProcessorRedisIntegration(unittest.TestCase):
    """Test Match Processor Redis Integration functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.integration = MatchProcessorRedisIntegration()

    def test_initialization_success(self):
        """Test successful initialization."""
        integration = MatchProcessorRedisIntegration()

        self.assertIsInstance(integration, MatchProcessorRedisIntegration)
        # Redis service may or may not be initialized depending on environment

    def test_initialization_with_environment(self):
        """Test initialization with environment configuration."""
        with patch.dict(os.environ, {"REDIS_ENABLED": "true"}):
            integration = MatchProcessorRedisIntegration()

            self.assertIsInstance(integration, MatchProcessorRedisIntegration)

    def test_initialization_with_disabled_redis(self):
        """Test initialization with disabled Redis."""
        with patch.dict(os.environ, {"REDIS_ENABLED": "false"}):
            integration = MatchProcessorRedisIntegration()

            self.assertIsInstance(integration, MatchProcessorRedisIntegration)

    def test_publish_processing_start_success(self):
        """Test successful processing start publishing."""
        result = self.integration.publish_processing_start(processing_cycle=1)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_publish_processing_start_with_details(self):
        """Test processing start publishing with details."""
        result = self.integration.publish_processing_start(
            processing_cycle=2,
            additional_data={"test": "value"}
        )

        self.assertTrue(result)

    def test_publish_processing_start_no_args(self):
        """Test processing start publishing with no arguments."""
        result = self.integration.publish_processing_start()

        self.assertTrue(result)

    def test_publish_match_updates_success(self):
        """Test successful match updates publishing."""
        matches = [{"matchid": 123}]
        changes = {"new_matches": {123: matches[0]}}
        start_time = datetime.now()

        result = self.integration.publish_match_updates(
            matches, changes, start_time, processing_cycle=1
        )

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_publish_match_updates_minimal(self):
        """Test match updates publishing with minimal data."""
        result = self.integration.publish_match_updates([], {})

        self.assertTrue(result)

    def test_publish_match_updates_with_duration(self):
        """Test match updates publishing with processing duration."""
        start_time = datetime.now()

        result = self.integration.publish_match_updates(
            [], {}, start_time, processing_cycle=2
        )

        self.assertTrue(result)

    def test_publish_processing_error_success(self):
        """Test successful processing error publishing."""
        error = Exception("Test error")
        start_time = datetime.now()

        result = self.integration.publish_processing_error(
            error, processing_cycle=1, processing_start_time=start_time
        )

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_publish_processing_error_minimal(self):
        """Test processing error publishing with minimal data."""
        result = self.integration.publish_processing_error(Exception("test"))

        self.assertTrue(result)

    def test_get_redis_status(self):
        """Test getting Redis status."""
        status = self.integration.get_redis_status()

        self.assertIsInstance(status, dict)
        self.assertIn("integration_enabled", status)
        self.assertIn("redis_service_status", status)

    def test_close_integration(self):
        """Test closing the integration."""
        # Should not raise exception
        self.integration.close()

    def test_close_integration_multiple_times(self):
        """Test closing integration multiple times."""
        # Should not raise exception
        self.integration.close()
        self.integration.close()


class TestIntegrationHelpers(unittest.TestCase):
    """Test integration helper functions."""

    def test_create_redis_integration(self):
        """Test creating Redis integration."""
        integration = create_redis_integration()

        self.assertIsInstance(integration, MatchProcessorRedisIntegration)

    def test_add_redis_integration_to_processor(self):
        """Test adding Redis integration to processor."""
        # Create mock processor
        mock_processor = Mock()
        mock_processor._process_matches_sync = Mock(return_value="original_result")

        add_redis_integration_to_processor(mock_processor)

        # Verify integration was added
        self.assertIsInstance(mock_processor.redis_integration, MatchProcessorRedisIntegration)
        self.assertEqual(mock_processor._processing_cycle, 0)

    def test_add_redis_integration_with_existing_integration(self):
        """Test adding existing Redis integration to processor."""
        mock_integration = Mock()
        mock_processor = Mock()
        mock_processor._process_matches_sync = Mock(return_value="original_result")

        add_redis_integration_to_processor(mock_processor, mock_integration)

        self.assertEqual(mock_processor.redis_integration, mock_integration)

    def test_enhanced_process_matches_sync_success(self):
        """Test enhanced _process_matches_sync method."""
        mock_processor = Mock()
        mock_processor._process_matches_sync = Mock(return_value="original_result")
        mock_processor._all_matches = [{"matchid": 123}]
        mock_processor._changes = {"new_matches": {}}

        add_redis_integration_to_processor(mock_processor)

        # Call the enhanced method
        result = mock_processor._process_matches_sync()

        self.assertEqual(result, "original_result")

    def test_enhanced_process_matches_sync_exception(self):
        """Test enhanced _process_matches_sync method with exception."""
        mock_processor = Mock()
        mock_processor._process_matches_sync = Mock(side_effect=Exception("Processing error"))

        add_redis_integration_to_processor(mock_processor)

        # Call the enhanced method should raise exception
        with self.assertRaises(Exception):
            mock_processor._process_matches_sync()

    def test_processing_cycle_increment(self):
        """Test processing cycle increments correctly."""
        mock_processor = Mock()
        mock_processor._process_matches_sync = Mock(return_value="result")

        add_redis_integration_to_processor(mock_processor)

        # Call multiple times
        mock_processor._process_matches_sync()
        mock_processor._process_matches_sync()
        mock_processor._process_matches_sync()

        self.assertEqual(mock_processor._processing_cycle, 3)

    def test_integration_example_constant(self):
        """Test that integration example constant exists."""
        from src.redis_integration.app_integration import INTEGRATION_EXAMPLE

        self.assertIsInstance(INTEGRATION_EXAMPLE, str)
        self.assertIn("EventDrivenMatchListProcessor", INTEGRATION_EXAMPLE)


if __name__ == "__main__":
    unittest.main()
