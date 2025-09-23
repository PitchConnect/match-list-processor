#!/usr/bin/env python3
"""
Tests for Redis Services

This module tests the Redis services functionality for the match list processor.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis services testing for CI/CD coverage
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from src.redis_integration.services import MatchProcessorRedisService, create_redis_service


class TestMatchProcessorRedisService(unittest.TestCase):
    """Test Match Processor Redis Service functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = MatchProcessorRedisService(redis_url="redis://test:6379", enabled=True)

    def test_service_initialization(self):
        """Test service initialization."""
        self.assertTrue(self.service.enabled)
        self.assertEqual(self.service.redis_url, "redis://test:6379")
        self.assertIsNotNone(self.service.connection_manager)
        self.assertIsNotNone(self.service.publisher)

    def test_service_initialization_disabled(self):
        """Test service initialization when disabled."""
        service = MatchProcessorRedisService(enabled=False)

        self.assertFalse(service.enabled)
        self.assertIsNone(service.connection_manager)
        self.assertIsNone(service.publisher)

    @patch("src.redis_integration.services.MatchProcessorRedisPublisher")
    def test_initialize_redis_publishing_success(self, mock_publisher_class):
        """Test successful Redis publishing initialization."""
        mock_publisher = Mock()
        mock_publisher.ensure_connection.return_value = True
        mock_publisher_class.return_value = mock_publisher

        # Reinitialize service to use mocked publisher
        service = MatchProcessorRedisService(redis_url="redis://test:6379", enabled=True)
        result = service.initialize_redis_publishing()

        self.assertTrue(result)

    def test_initialize_redis_publishing_disabled(self):
        """Test Redis publishing initialization when disabled."""
        service = MatchProcessorRedisService(enabled=False)

        result = service.initialize_redis_publishing()

        self.assertTrue(result)  # Should return True for disabled service

    def test_handle_processing_start_success(self):
        """Test successful processing start handling."""
        processing_details = {
            "processing_cycle": 1,
            "start_time": datetime.now().isoformat(),
        }

        result = self.service.handle_processing_start(processing_details)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_handle_processing_start_disabled(self):
        """Test processing start handling when disabled."""
        service = MatchProcessorRedisService(enabled=False)

        result = service.handle_processing_start({})

        self.assertTrue(result)

    def test_handle_match_processing_complete_success(self):
        """Test successful match processing completion handling."""
        matches = [{"matchid": 123, "team1": "A", "team2": "B"}]
        changes = {"new_matches": {123: matches[0]}}
        processing_details = {"processing_cycle": 1}

        result = self.service.handle_match_processing_complete(matches, changes, processing_details)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_handle_processing_error_success(self):
        """Test successful processing error handling."""
        error = Exception("Test error")
        processing_details = {"processing_cycle": 1}

        result = self.service.handle_processing_error(error, processing_details)

        # Should return True even if Redis is not connected (graceful degradation)
        self.assertTrue(result)

    def test_handle_processing_error_disabled(self):
        """Test processing error handling when disabled."""
        service = MatchProcessorRedisService(enabled=False)

        result = service.handle_processing_error(Exception("test"), {})

        self.assertTrue(result)

    def test_get_redis_status_enabled(self):
        """Test getting Redis status when enabled."""
        status = self.service.get_redis_status()

        self.assertIsInstance(status, dict)
        self.assertIn("enabled", status)
        self.assertIn("redis_available", status)
        self.assertIn("connection_status", status)
        self.assertIn("channels", status)

    def test_get_redis_status_disabled(self):
        """Test getting Redis status when disabled."""
        service = MatchProcessorRedisService(enabled=False)

        status = service.get_redis_status()

        self.assertFalse(status["enabled"])
        self.assertFalse(status["redis_available"])

    def test_close_service(self):
        """Test closing the service."""
        # Should not raise exception
        self.service.close()

    def test_close_service_disabled(self):
        """Test closing disabled service."""
        service = MatchProcessorRedisService(enabled=False)

        # Should not raise exception
        service.close()

    def test_create_redis_service_function(self):
        """Test create_redis_service helper function."""
        service = create_redis_service(redis_url="redis://test:6379", enabled=True)

        self.assertIsInstance(service, MatchProcessorRedisService)
        self.assertTrue(service.enabled)

    def test_create_redis_service_disabled(self):
        """Test create_redis_service with disabled service."""
        service = create_redis_service(enabled=False)

        self.assertIsInstance(service, MatchProcessorRedisService)
        self.assertFalse(service.enabled)

    def test_service_with_default_config(self):
        """Test service with default configuration."""
        service = MatchProcessorRedisService()

        # Should use environment configuration
        self.assertIsInstance(service, MatchProcessorRedisService)

    def test_service_initialization_error_handling(self):
        """Test service initialization with error handling."""
        # Test with invalid URL format
        service = MatchProcessorRedisService(redis_url="invalid_url", enabled=True)

        # Should handle initialization errors gracefully
        self.assertIsInstance(service, MatchProcessorRedisService)

    def test_service_string_representation(self):
        """Test service string representation."""
        service_str = str(self.service)

        self.assertIsInstance(service_str, str)
        self.assertIn("MatchProcessorRedisService", service_str)

    def test_service_repr_representation(self):
        """Test service repr representation."""
        service_repr = repr(self.service)

        self.assertIsInstance(service_repr, str)
        self.assertIn("MatchProcessorRedisService", service_repr)


if __name__ == "__main__":
    unittest.main()
