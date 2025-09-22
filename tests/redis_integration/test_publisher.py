#!/usr/bin/env python3
"""
Tests for Redis Publisher

This module tests the Redis publishing functionality for the match list processor.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis publisher testing
"""

import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for testing
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from redis_integration.publisher import (
    MatchProcessorRedisPublisher,
    PublishResult,
    create_redis_publisher
)
from redis_integration.connection_manager import RedisConnectionConfig

class TestPublishResult(unittest.TestCase):
    """Test PublishResult dataclass."""
    
    def test_publish_result_creation(self):
        """Test publish result creation."""
        result = PublishResult(
            success=True,
            channel="test_channel",
            subscribers_notified=5,
            message_id="test-id"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.channel, "test_channel")
        self.assertEqual(result.subscribers_notified, 5)
        self.assertEqual(result.message_id, "test-id")
        self.assertIsNotNone(result.timestamp)
    
    def test_publish_result_with_error(self):
        """Test publish result with error."""
        result = PublishResult(
            success=False,
            channel="test_channel",
            subscribers_notified=0,
            error="Connection failed"
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "Connection failed")

class TestMatchProcessorRedisPublisher(unittest.TestCase):
    """Test Redis publisher for match processor."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = RedisConnectionConfig(url="redis://test:6379")
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publisher_initialization(self, mock_connection_manager):
        """Test publisher initialization."""
        # Mock connection manager
        mock_manager = Mock()
        mock_manager.ensure_connection.return_value = True
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        self.assertIsNotNone(publisher.connection_manager)
        self.assertEqual(len(publisher.channels), 3)
        self.assertIn('match_updates', publisher.channels)
        self.assertIn('processor_status', publisher.channels)
        self.assertIn('system_alerts', publisher.channels)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publish_match_updates_success(self, mock_connection_manager):
        """Test successful match updates publishing."""
        # Mock connection manager
        mock_manager = Mock()
        mock_manager.publish.return_value = 2  # 2 subscribers
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test data
        matches = [
            {
                'matchid': 123456,
                'datum': '2025-09-23',
                'hemmalag': 'Team A',
                'bortalag': 'Team B'
            }
        ]
        
        changes = {
            'new_matches': {123456: matches[0]},
            'updated_matches': {},
            'cancelled_matches': {}
        }
        
        # Publish
        result = publisher.publish_match_updates(matches, changes)
        
        self.assertTrue(result.success)
        self.assertEqual(result.channel, 'fogis:matches:updates')
        self.assertEqual(result.subscribers_notified, 2)
        self.assertIsNotNone(result.message_id)
        
        # Verify connection manager was called
        mock_manager.publish.assert_called_once()
        
        # Verify message format
        call_args = mock_manager.publish.call_args
        channel, message_json = call_args[0]
        
        self.assertEqual(channel, 'fogis:matches:updates')
        
        # Parse and validate message
        message = json.loads(message_json)
        self.assertEqual(message['type'], 'match_updates')
        self.assertEqual(message['source'], 'match-list-processor')
        self.assertIn('message_id', message)
        self.assertIn('timestamp', message)
        self.assertIn('payload', message)
        self.assertEqual(len(message['payload']['matches']), 1)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publish_match_updates_failure(self, mock_connection_manager):
        """Test failed match updates publishing."""
        # Mock connection manager failure
        mock_manager = Mock()
        mock_manager.publish.return_value = -1  # Failure
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test data
        matches = []
        changes = {'new_matches': {}, 'updated_matches': {}, 'cancelled_matches': {}}
        
        # Publish
        result = publisher.publish_match_updates(matches, changes)
        
        self.assertFalse(result.success)
        self.assertEqual(result.subscribers_notified, 0)
        self.assertIsNotNone(result.error)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publish_processing_status_success(self, mock_connection_manager):
        """Test successful processing status publishing."""
        # Mock connection manager
        mock_manager = Mock()
        mock_manager.publish.return_value = 1  # 1 subscriber
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test data
        status = "completed"
        details = {
            'cycle_number': 42,
            'processing_duration_ms': 2500,
            'matches_processed': 15
        }
        
        # Publish
        result = publisher.publish_processing_status(status, details)
        
        self.assertTrue(result.success)
        self.assertEqual(result.channel, 'fogis:processor:status')
        self.assertEqual(result.subscribers_notified, 1)
        
        # Verify message format
        call_args = mock_manager.publish.call_args
        channel, message_json = call_args[0]
        
        message = json.loads(message_json)
        self.assertEqual(message['type'], 'processing_status')
        self.assertEqual(message['payload']['status'], 'completed')
        self.assertEqual(message['payload']['cycle_number'], 42)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publish_system_alert_success(self, mock_connection_manager):
        """Test successful system alert publishing."""
        # Mock connection manager
        mock_manager = Mock()
        mock_manager.publish.return_value = 3  # 3 subscribers
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test data
        alert_type = "processing_error"
        message = "Test error occurred"
        severity = "error"
        details = {"error_code": 500}
        
        # Publish
        result = publisher.publish_system_alert(alert_type, message, severity, details)
        
        self.assertTrue(result.success)
        self.assertEqual(result.channel, 'fogis:system:alerts')
        self.assertEqual(result.subscribers_notified, 3)
        
        # Verify message format
        call_args = mock_manager.publish.call_args
        channel, message_json = call_args[0]
        
        message_obj = json.loads(message_json)
        self.assertEqual(message_obj['type'], 'system_alert')
        self.assertEqual(message_obj['payload']['alert_type'], 'processing_error')
        self.assertEqual(message_obj['payload']['severity'], 'error')
        self.assertEqual(message_obj['payload']['message'], 'Test error occurred')
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publishing_stats(self, mock_connection_manager):
        """Test publishing statistics tracking."""
        # Mock connection manager
        mock_manager = Mock()
        mock_manager.publish.return_value = 1
        mock_manager.get_connection_status.return_value = {
            'redis_available': True,
            'is_connected': True
        }
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Initial stats
        stats = publisher.get_publishing_stats()
        self.assertEqual(stats['publishing_stats']['total_published'], 0)
        self.assertEqual(stats['publishing_stats']['successful_publishes'], 0)
        
        # Publish something
        matches = []
        changes = {'new_matches': {}, 'updated_matches': {}, 'cancelled_matches': {}}
        publisher.publish_match_updates(matches, changes)
        
        # Check updated stats
        stats = publisher.get_publishing_stats()
        self.assertEqual(stats['publishing_stats']['total_published'], 1)
        self.assertEqual(stats['publishing_stats']['successful_publishes'], 1)
        self.assertEqual(stats['publishing_stats']['failed_publishes'], 0)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publisher_exception_handling(self, mock_connection_manager):
        """Test publisher exception handling."""
        # Mock connection manager to raise exception
        mock_manager = Mock()
        mock_manager.publish.side_effect = Exception("Redis connection lost")
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test data
        matches = []
        changes = {'new_matches': {}, 'updated_matches': {}, 'cancelled_matches': {}}
        
        # Publish should handle exception gracefully
        result = publisher.publish_match_updates(matches, changes)
        
        self.assertFalse(result.success)
        self.assertIn("Redis connection lost", result.error)
        
        # Stats should reflect the failure
        stats = publisher.get_publishing_stats()
        self.assertEqual(stats['publishing_stats']['failed_publishes'], 1)
    
    @patch('redis_integration.publisher.RedisConnectionManager')
    def test_publisher_close(self, mock_connection_manager):
        """Test publisher close functionality."""
        # Mock connection manager
        mock_manager = Mock()
        mock_connection_manager.return_value = mock_manager
        
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Close publisher
        publisher.close()
        
        # Verify connection manager close was called
        mock_manager.close.assert_called_once()

class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    @patch('redis_integration.publisher.MatchProcessorRedisPublisher')
    def test_create_redis_publisher(self, mock_publisher_class):
        """Test create_redis_publisher convenience function."""
        mock_publisher = Mock()
        mock_publisher_class.return_value = mock_publisher
        
        # Test with default URL
        publisher = create_redis_publisher()
        
        mock_publisher_class.assert_called_once()
        config_arg = mock_publisher_class.call_args[0][0]
        self.assertEqual(config_arg.url, "redis://fogis-redis:6379")
        
        # Test with custom URL
        mock_publisher_class.reset_mock()
        publisher = create_redis_publisher("redis://custom:6379")
        
        config_arg = mock_publisher_class.call_args[0][0]
        self.assertEqual(config_arg.url, "redis://custom:6379")

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
