#!/usr/bin/env python3
"""
Tests for Redis Integration

Comprehensive test suite for Redis pub/sub integration functionality.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path for imports (must be before local imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Local imports after path modification
from redis_integration import (  # noqa: E402
    MatchProcessorRedisPublisher,
    MatchProcessorRedisService,
    RedisConfig,
    add_redis_integration_to_processor,
)


class TestRedisConfig(unittest.TestCase):
    """Test Redis configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RedisConfig()
        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertTrue(config.enabled)
        self.assertEqual(config.match_updates_channel, "fogis:matches:updates")

    def test_from_environment(self):
        """Test configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "REDIS_URL": "redis://test:6379",
                "REDIS_PUBSUB_ENABLED": "false",
                "REDIS_MATCH_UPDATES_CHANNEL": "test:matches",
            },
        ):
            config = RedisConfig.from_environment()
            self.assertEqual(config.url, "redis://test:6379")
            self.assertFalse(config.enabled)
            self.assertEqual(config.match_updates_channel, "test:matches")

    def test_get_channels(self):
        """Test channel configuration retrieval."""
        config = RedisConfig()
        channels = config.get_channels()
        self.assertIn("match_updates", channels)
        self.assertIn("processor_status", channels)
        self.assertIn("system_alerts", channels)


class TestRedisPublisher(unittest.TestCase):
    """Test Redis publisher functionality."""

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_match_updates_success(self, mock_connection_manager):
        """Test successful match updates publishing."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.publish.return_value = 2

        mock_manager = Mock()
        mock_manager.get_client.return_value = mock_client
        mock_manager.config.enabled = True
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        matches = [{"id": 1, "team1": "A", "team2": "B"}]
        changes = {"summary": {"new_matches": 1}}

        result = publisher.publish_match_updates(matches, changes)

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 2)
        mock_client.publish.assert_called_once()

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_disabled(self, mock_connection_manager):
        """Test publishing when Redis is disabled."""
        mock_manager = Mock()
        mock_manager.config.enabled = False
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        result = publisher.publish_match_updates([], {})

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 0)

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_connection_failed(self, mock_connection_manager):
        """Test publishing when Redis connection fails."""
        mock_manager = Mock()
        mock_manager.get_client.return_value = None
        mock_manager.config.enabled = True
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        result = publisher.publish_match_updates([], {})

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


class TestRedisService(unittest.TestCase):
    """Test Redis service functionality."""

    @patch("redis_integration.services.MatchProcessorRedisPublisher")
    def test_handle_processing_complete(self, mock_publisher_class):
        """Test handling processing completion."""
        mock_publisher = Mock()
        mock_publisher.publish_match_updates.return_value = Mock(success=True)
        mock_publisher.publish_processing_status.return_value = Mock(success=True)
        mock_publisher_class.return_value = mock_publisher

        service = MatchProcessorRedisService()
        matches = [{"id": 1}]
        changes = {"summary": {}}

        result = service.handle_match_processing_complete(matches, changes)

        self.assertTrue(result)
        mock_publisher.publish_match_updates.assert_called_once()
        mock_publisher.publish_processing_status.assert_called_once()

    @patch("redis_integration.services.MatchProcessorRedisPublisher")
    def test_handle_processing_error(self, mock_publisher_class):
        """Test handling processing errors."""
        mock_publisher = Mock()
        mock_publisher.publish_processing_status.return_value = Mock(success=True)
        mock_publisher.publish_system_alert.return_value = Mock(success=True)
        mock_publisher_class.return_value = mock_publisher

        service = MatchProcessorRedisService()
        error = Exception("Test error")

        result = service.handle_processing_error(error)

        self.assertTrue(result)
        mock_publisher.publish_processing_status.assert_called_once()
        mock_publisher.publish_system_alert.assert_called_once()


class TestAppIntegration(unittest.TestCase):
    """Test application integration functionality."""

    def test_add_redis_integration(self):
        """Test adding Redis integration to processor."""
        # Create mock processor
        processor = Mock()
        processor._process_matches_sync = Mock(return_value=None)

        add_redis_integration_to_processor(processor)

        # Check that Redis integration was added
        self.assertTrue(hasattr(processor, "redis_integration"))
        self.assertTrue(hasattr(processor, "_original_process_matches_sync"))

    def test_integration_without_process_method(self):
        """Test integration with processor without _process_matches_sync method."""
        processor = Mock()
        del processor._process_matches_sync  # Remove the method

        add_redis_integration_to_processor(processor)

        # Should still add redis_integration but warn about missing method
        self.assertTrue(hasattr(processor, "redis_integration"))


if __name__ == "__main__":
    unittest.main()
