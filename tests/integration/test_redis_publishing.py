#!/usr/bin/env python3
"""
Integration Tests for Redis Publishing

This module provides integration tests for Redis publishing functionality
in the match list processor.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis publishing integration testing
"""

import unittest
import json
import time
from unittest.mock import patch, Mock
import sys
from pathlib import Path

# Add src to path for testing
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from redis_integration.publisher import MatchProcessorRedisPublisher
from redis_integration.connection_manager import RedisConnectionManager, RedisConnectionConfig
from redis_integration.message_formatter import MatchUpdateMessageFormatter
from services.redis_service import MatchProcessorRedisService
from app_event_driven_redis_integration import MatchProcessorRedisIntegration

class TestRedisPublishingIntegration(unittest.TestCase):
    """Integration tests for Redis publishing."""
    
    def setUp(self):
        """Set up test environment."""
        self.config = RedisConnectionConfig(url="redis://test:6379")
        self.test_matches = [
            {
                'matchid': 123456,
                'datum': '2025-09-23',
                'tid': '14:00',
                'hemmalag': 'Team A',
                'bortalag': 'Team B',
                'arena': 'Stadium Name'
            }
        ]
        self.test_changes = {
            'new_matches': {123456: self.test_matches[0]},
            'updated_matches': {},
            'cancelled_matches': {},
            'processing_cycle': 42
        }
    
    @patch('redis_integration.connection_manager.redis')
    def test_end_to_end_publishing_flow(self, mock_redis_module):
        """Test complete end-to-end publishing flow."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 2  # 2 subscribers
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create publisher
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Test match updates publishing
        result = publisher.publish_match_updates(self.test_matches, self.test_changes)
        
        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 2)
        self.assertIsNotNone(result.message_id)
        
        # Verify Redis client was called
        mock_client.publish.assert_called()
        
        # Get the published message
        call_args = mock_client.publish.call_args
        channel, message_json = call_args[0]
        
        self.assertEqual(channel, 'fogis:matches:updates')
        
        # Validate message format
        message = json.loads(message_json)
        validation = MatchUpdateMessageFormatter.validate_match_update_message(message)
        self.assertTrue(validation.is_valid)
        
        # Test processing status publishing
        status_result = publisher.publish_processing_status("completed", {
            'cycle_number': 42,
            'processing_duration_ms': 2500,
            'matches_processed': 1
        })
        
        self.assertTrue(status_result.success)
        self.assertEqual(status_result.subscribers_notified, 2)
        
        # Test system alert publishing
        alert_result = publisher.publish_system_alert(
            "info", "Test completed successfully", "info"
        )
        
        self.assertTrue(alert_result.success)
        self.assertEqual(alert_result.subscribers_notified, 2)
        
        # Verify statistics
        stats = publisher.get_publishing_stats()
        self.assertEqual(stats['publishing_stats']['total_published'], 3)
        self.assertEqual(stats['publishing_stats']['successful_publishes'], 3)
        self.assertEqual(stats['publishing_stats']['failed_publishes'], 0)
    
    @patch('redis_integration.connection_manager.redis')
    def test_redis_service_integration(self, mock_redis_module):
        """Test Redis service integration."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create Redis service
        service = MatchProcessorRedisService(redis_url="redis://test:6379", enabled=True)
        
        # Test initialization
        self.assertTrue(service.initialize_redis_publishing())
        
        # Test match processing completion
        processing_details = {
            'processing_duration_ms': 2500,
            'start_time': '2025-09-21T10:00:00',
            'end_time': '2025-09-21T10:02:30'
        }
        
        result = service.handle_match_processing_complete(
            self.test_matches, self.test_changes, processing_details
        )
        
        self.assertTrue(result)
        
        # Verify multiple publishes occurred (match updates + processing status)
        self.assertEqual(mock_client.publish.call_count, 2)
        
        # Test error handling
        error = Exception("Test processing error")
        error_result = service.handle_processing_error(error, processing_details)
        
        self.assertTrue(error_result)
        
        # Verify additional publishes for error (system alert + processing status)
        self.assertEqual(mock_client.publish.call_count, 4)
    
    @patch('redis_integration.connection_manager.redis')
    def test_match_processor_integration(self, mock_redis_module):
        """Test match processor Redis integration."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create integration
        integration = MatchProcessorRedisIntegration()
        
        # Test status
        status = integration.get_redis_status()
        self.assertTrue(status.get('integration_enabled', False))
        
        # Test processing start
        start_result = integration.publish_processing_start(42)
        self.assertTrue(start_result)
        
        # Test match updates
        update_result = integration.publish_match_updates(
            self.test_matches, self.test_changes, processing_cycle=42
        )
        self.assertTrue(update_result)
        
        # Test error publishing
        error = Exception("Test error")
        error_result = integration.publish_processing_error(error, 42)
        self.assertTrue(error_result)
        
        # Verify publishes occurred
        self.assertGreater(mock_client.publish.call_count, 0)
    
    def test_redis_unavailable_graceful_degradation(self):
        """Test graceful degradation when Redis is unavailable."""
        # Test with Redis module not available
        with patch('redis_integration.connection_manager.REDIS_AVAILABLE', False):
            # Create publisher
            publisher = MatchProcessorRedisPublisher(self.config)
            
            # Publishing should fail gracefully
            result = publisher.publish_match_updates(self.test_matches, self.test_changes)
            
            self.assertFalse(result.success)
            self.assertEqual(result.subscribers_notified, 0)
            self.assertIsNotNone(result.error)
            
            # Stats should reflect the failure
            stats = publisher.get_publishing_stats()
            self.assertEqual(stats['publishing_stats']['failed_publishes'], 1)
            self.assertFalse(stats.get('redis_available', True))
    
    @patch('redis_integration.connection_manager.redis')
    def test_connection_failure_recovery(self, mock_redis_module):
        """Test connection failure and recovery."""
        # Mock Redis client that initially fails
        mock_client = Mock()
        mock_client.ping.side_effect = [Exception("Connection failed"), True, True]
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create connection manager
        manager = RedisConnectionManager(self.config)
        
        # First connection should fail
        self.assertFalse(manager.ensure_connection())
        
        # Second attempt should succeed (after retry)
        self.assertTrue(manager.ensure_connection())
        
        # Publishing should now work
        result = manager.publish("test_channel", "test_message")
        self.assertGreater(result, 0)
    
    @patch('redis_integration.connection_manager.redis')
    def test_message_format_consistency(self, mock_redis_module):
        """Test message format consistency across different publishing methods."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create publisher
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Publish different message types
        publisher.publish_match_updates(self.test_matches, self.test_changes)
        publisher.publish_processing_status("completed", {'cycle_number': 42})
        publisher.publish_system_alert("info", "Test message", "info")
        
        # Verify all messages have consistent format
        self.assertEqual(mock_client.publish.call_count, 3)
        
        for call in mock_client.publish.call_args_list:
            channel, message_json = call[0]
            
            # Parse message
            message = json.loads(message_json)
            
            # Check required fields
            self.assertIn('message_id', message)
            self.assertIn('timestamp', message)
            self.assertIn('source', message)
            self.assertIn('version', message)
            self.assertIn('type', message)
            self.assertIn('payload', message)
            
            # Check source consistency
            self.assertEqual(message['source'], 'match-list-processor')
            self.assertEqual(message['version'], '1.0')
    
    @patch('redis_integration.connection_manager.redis')
    def test_concurrent_publishing(self, mock_redis_module):
        """Test concurrent publishing scenarios."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create multiple publishers
        publisher1 = MatchProcessorRedisPublisher(self.config)
        publisher2 = MatchProcessorRedisPublisher(self.config)
        
        # Publish from both simultaneously
        result1 = publisher1.publish_match_updates(self.test_matches, self.test_changes)
        result2 = publisher2.publish_processing_status("started", {'cycle_number': 1})
        
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        
        # Both should have published successfully
        self.assertEqual(mock_client.publish.call_count, 2)
    
    @patch('redis_integration.connection_manager.redis')
    def test_large_message_handling(self, mock_redis_module):
        """Test handling of large messages."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.publish.return_value = 1
        mock_redis_module.from_url.return_value = mock_client
        mock_redis_module.REDIS_AVAILABLE = True
        
        # Create large dataset
        large_matches = []
        large_changes = {'new_matches': {}, 'updated_matches': {}, 'cancelled_matches': {}}
        
        for i in range(1000):  # 1000 matches
            match = {
                'matchid': 100000 + i,
                'datum': '2025-09-23',
                'tid': '14:00',
                'hemmalag': f'Team A {i}',
                'bortalag': f'Team B {i}',
                'arena': f'Stadium {i}',
                'description': 'A' * 100  # Add some bulk to each match
            }
            large_matches.append(match)
            large_changes['new_matches'][100000 + i] = match
        
        # Create publisher
        publisher = MatchProcessorRedisPublisher(self.config)
        
        # Publish large message
        result = publisher.publish_match_updates(large_matches, large_changes)
        
        self.assertTrue(result.success)
        
        # Verify message was published
        mock_client.publish.assert_called_once()
        
        # Check message size
        call_args = mock_client.publish.call_args
        channel, message_json = call_args[0]
        
        # Message should be substantial but still valid JSON
        self.assertGreater(len(message_json), 100000)  # Should be > 100KB
        
        # Should still be valid JSON
        message = json.loads(message_json)
        self.assertEqual(len(message['payload']['matches']), 1000)

if __name__ == '__main__':
    # Run integration tests
    unittest.main(verbosity=2)
