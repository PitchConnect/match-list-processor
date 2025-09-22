#!/usr/bin/env python3
"""
Tests for Redis Message Formatter

This module tests the message formatting functionality for Redis pub/sub communication.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis message formatter testing
"""

import unittest
import json
from datetime import datetime
import sys
from pathlib import Path

# Add src to path for testing
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from redis_integration.message_formatter import (
    MatchUpdateMessageFormatter,
    ProcessingStatusMessageFormatter,
    ValidationResult,
    create_match_update_message,
    create_processing_status_message,
    create_system_alert_message
)

class TestValidationResult(unittest.TestCase):
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test validation result creation."""
        result = ValidationResult(
            is_valid=True,
            errors=["Error 1"],
            warnings=["Warning 1"]
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, ["Error 1"])
        self.assertEqual(result.warnings, ["Warning 1"])
    
    def test_validation_result_defaults(self):
        """Test validation result with defaults."""
        result = ValidationResult(is_valid=False, errors=[])
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

class TestMatchUpdateMessageFormatter(unittest.TestCase):
    """Test match update message formatter."""
    
    def setUp(self):
        """Set up test data."""
        self.test_matches = [
            {
                'matchid': 123456,
                'datum': '2025-09-23',
                'tid': '14:00',
                'hemmalag': 'Team A',
                'bortalag': 'Team B',
                'arena': 'Stadium Name',
                'domare1': 'Referee Name',
                'domare1_telefon': '+46701234567'
            },
            {
                'matchid': 123457,
                'datum': '2025-09-24',
                'tid': '16:00',
                'hemmalag': 'Team C',
                'bortalag': 'Team D',
                'arena': 'Another Stadium'
            }
        ]
        
        self.test_changes = {
            'new_matches': {123456: self.test_matches[0]},
            'updated_matches': {123457: {'tid': '16:00', 'domare1': 'New Referee'}},
            'cancelled_matches': {},
            'processing_cycle': 42
        }
    
    def test_format_match_updates_basic(self):
        """Test basic match updates formatting."""
        message = MatchUpdateMessageFormatter.format_match_updates(
            self.test_matches, self.test_changes
        )
        
        # Check top-level structure
        self.assertIn('message_id', message)
        self.assertIn('timestamp', message)
        self.assertEqual(message['source'], 'match-list-processor')
        self.assertEqual(message['version'], '1.0')
        self.assertEqual(message['type'], 'match_updates')
        self.assertIn('payload', message)
        
        # Check payload structure
        payload = message['payload']
        self.assertIn('matches', payload)
        self.assertIn('metadata', payload)
        self.assertEqual(len(payload['matches']), 2)
        
        # Check metadata
        metadata = payload['metadata']
        self.assertEqual(metadata['total_matches'], 2)
        self.assertTrue(metadata['has_changes'])
        self.assertEqual(metadata['processing_cycle'], 42)
        
        # Check change summary
        change_summary = metadata['change_summary']
        self.assertEqual(change_summary['new_matches'], 1)
        self.assertEqual(change_summary['updated_matches'], 1)
        self.assertEqual(change_summary['cancelled_matches'], 0)
        self.assertEqual(change_summary['total_changes'], 2)
        
        # Check change detection
        change_detection = metadata['change_detection']
        self.assertEqual(change_detection['new_match_ids'], [123456])
        self.assertEqual(change_detection['updated_match_ids'], [123457])
        self.assertEqual(change_detection['cancelled_match_ids'], [])
        self.assertIn('new_matches', change_detection['change_types'])
        self.assertIn('match_updates', change_detection['change_types'])
        self.assertIn('referee_assignment', change_detection['change_types'])
    
    def test_format_match_updates_no_changes(self):
        """Test match updates formatting with no changes."""
        no_changes = {
            'new_matches': {},
            'updated_matches': {},
            'cancelled_matches': {},
            'processing_cycle': 1
        }
        
        message = MatchUpdateMessageFormatter.format_match_updates(
            self.test_matches, no_changes
        )
        
        metadata = message['payload']['metadata']
        self.assertFalse(metadata['has_changes'])
        self.assertEqual(metadata['change_summary']['total_changes'], 0)
        self.assertEqual(len(metadata['change_detection']['change_types']), 0)
    
    def test_format_match_updates_change_types(self):
        """Test change type detection."""
        # Test time change
        time_changes = {
            'new_matches': {},
            'updated_matches': {123456: {'tid': '15:00', 'datum': '2025-09-24'}},
            'cancelled_matches': {},
            'processing_cycle': 1
        }
        
        message = MatchUpdateMessageFormatter.format_match_updates(
            [self.test_matches[0]], time_changes
        )
        
        change_types = message['payload']['metadata']['change_detection']['change_types']
        self.assertIn('match_updates', change_types)
        self.assertIn('time_change', change_types)
        
        # Test venue change
        venue_changes = {
            'new_matches': {},
            'updated_matches': {123456: {'arena': 'New Stadium'}},
            'cancelled_matches': {},
            'processing_cycle': 1
        }
        
        message = MatchUpdateMessageFormatter.format_match_updates(
            [self.test_matches[0]], venue_changes
        )
        
        change_types = message['payload']['metadata']['change_detection']['change_types']
        self.assertIn('venue_change', change_types)
        
        # Test cancellation
        cancellation_changes = {
            'new_matches': {},
            'updated_matches': {},
            'cancelled_matches': {123456: self.test_matches[0]},
            'processing_cycle': 1
        }
        
        message = MatchUpdateMessageFormatter.format_match_updates(
            [], cancellation_changes
        )
        
        change_types = message['payload']['metadata']['change_detection']['change_types']
        self.assertIn('match_cancellations', change_types)
    
    def test_validate_match_update_message_valid(self):
        """Test validation of valid match update message."""
        message = MatchUpdateMessageFormatter.format_match_updates(
            self.test_matches, self.test_changes
        )
        
        validation = MatchUpdateMessageFormatter.validate_match_update_message(message)
        
        self.assertTrue(validation.is_valid)
        self.assertEqual(len(validation.errors), 0)
    
    def test_validate_match_update_message_missing_fields(self):
        """Test validation with missing required fields."""
        invalid_message = {
            'message_id': 'test-id',
            # Missing timestamp, source, version, type, payload
        }
        
        validation = MatchUpdateMessageFormatter.validate_match_update_message(invalid_message)
        
        self.assertFalse(validation.is_valid)
        self.assertGreater(len(validation.errors), 0)
        self.assertIn("Missing required field: timestamp", validation.errors)
        self.assertIn("Missing required field: source", validation.errors)
    
    def test_validate_match_update_message_invalid_type(self):
        """Test validation with invalid message type."""
        message = MatchUpdateMessageFormatter.format_match_updates(
            self.test_matches, self.test_changes
        )
        message['type'] = 'invalid_type'
        
        validation = MatchUpdateMessageFormatter.validate_match_update_message(message)
        
        self.assertFalse(validation.is_valid)
        self.assertIn("Invalid message type: invalid_type", validation.errors)
    
    def test_validate_match_update_message_warnings(self):
        """Test validation warnings."""
        message = MatchUpdateMessageFormatter.format_match_updates(
            self.test_matches, self.test_changes
        )
        
        # Remove metadata to trigger warnings
        del message['payload']['metadata']['total_matches']
        
        validation = MatchUpdateMessageFormatter.validate_match_update_message(message)
        
        self.assertTrue(validation.is_valid)  # Still valid, just warnings
        self.assertGreater(len(validation.warnings), 0)
        self.assertIn("Missing 'total_matches' in metadata", validation.warnings)

class TestProcessingStatusMessageFormatter(unittest.TestCase):
    """Test processing status message formatter."""
    
    def test_format_processing_status_basic(self):
        """Test basic processing status formatting."""
        status = "completed"
        details = {
            'cycle_number': 42,
            'processing_duration_ms': 2500,
            'matches_processed': 15,
            'errors': [],
            'start_time': '2025-09-21T10:00:00',
            'end_time': '2025-09-21T10:02:30'
        }
        
        message = ProcessingStatusMessageFormatter.format_processing_status(status, details)
        
        # Check top-level structure
        self.assertIn('message_id', message)
        self.assertIn('timestamp', message)
        self.assertEqual(message['source'], 'match-list-processor')
        self.assertEqual(message['version'], '1.0')
        self.assertEqual(message['type'], 'processing_status')
        
        # Check payload
        payload = message['payload']
        self.assertEqual(payload['status'], 'completed')
        self.assertEqual(payload['cycle_number'], 42)
        self.assertEqual(payload['processing_duration_ms'], 2500)
        self.assertEqual(payload['matches_processed'], 15)
        self.assertEqual(payload['errors'], [])
        
        # Check details
        details_obj = payload['details']
        self.assertEqual(details_obj['start_time'], '2025-09-21T10:00:00')
        self.assertEqual(details_obj['end_time'], '2025-09-21T10:02:30')
    
    def test_format_processing_status_minimal(self):
        """Test processing status formatting with minimal details."""
        status = "started"
        details = {}
        
        message = ProcessingStatusMessageFormatter.format_processing_status(status, details)
        
        payload = message['payload']
        self.assertEqual(payload['status'], 'started')
        self.assertEqual(payload['cycle_number'], 0)
        self.assertEqual(payload['processing_duration_ms'], 0)
        self.assertEqual(payload['matches_processed'], 0)
        self.assertEqual(payload['errors'], [])
    
    def test_format_system_alert_basic(self):
        """Test basic system alert formatting."""
        alert_type = "processing_error"
        message_text = "Processing failed due to network error"
        severity = "error"
        details = {"error_code": 500, "retry_count": 3}
        
        message = ProcessingStatusMessageFormatter.format_system_alert(
            alert_type, message_text, severity, details
        )
        
        # Check top-level structure
        self.assertIn('message_id', message)
        self.assertIn('timestamp', message)
        self.assertEqual(message['source'], 'match-list-processor')
        self.assertEqual(message['version'], '1.0')
        self.assertEqual(message['type'], 'system_alert')
        
        # Check payload
        payload = message['payload']
        self.assertEqual(payload['alert_type'], 'processing_error')
        self.assertEqual(payload['severity'], 'error')
        self.assertEqual(payload['message'], 'Processing failed due to network error')
        self.assertEqual(payload['details'], {"error_code": 500, "retry_count": 3})
    
    def test_format_system_alert_minimal(self):
        """Test system alert formatting with minimal parameters."""
        alert_type = "info"
        message_text = "Processing completed successfully"
        
        message = ProcessingStatusMessageFormatter.format_system_alert(alert_type, message_text)
        
        payload = message['payload']
        self.assertEqual(payload['alert_type'], 'info')
        self.assertEqual(payload['severity'], 'info')
        self.assertEqual(payload['message'], 'Processing completed successfully')
        self.assertEqual(payload['details'], {})

class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def test_create_match_update_message(self):
        """Test create_match_update_message convenience function."""
        matches = [{'matchid': 123456, 'hemmalag': 'Team A', 'bortalag': 'Team B'}]
        changes = {'new_matches': {123456: matches[0]}, 'updated_matches': {}, 'cancelled_matches': {}}
        
        message_json = create_match_update_message(matches, changes)
        
        # Should be valid JSON
        message = json.loads(message_json)
        
        self.assertEqual(message['type'], 'match_updates')
        self.assertEqual(message['source'], 'match-list-processor')
        self.assertEqual(len(message['payload']['matches']), 1)
    
    def test_create_processing_status_message(self):
        """Test create_processing_status_message convenience function."""
        status = "completed"
        details = {'cycle_number': 42, 'matches_processed': 10}
        
        message_json = create_processing_status_message(status, details)
        
        # Should be valid JSON
        message = json.loads(message_json)
        
        self.assertEqual(message['type'], 'processing_status')
        self.assertEqual(message['payload']['status'], 'completed')
        self.assertEqual(message['payload']['cycle_number'], 42)
    
    def test_create_system_alert_message(self):
        """Test create_system_alert_message convenience function."""
        alert_type = "warning"
        message_text = "High memory usage detected"
        severity = "warning"
        details = {"memory_usage": "85%"}
        
        message_json = create_system_alert_message(alert_type, message_text, severity, details)
        
        # Should be valid JSON
        message = json.loads(message_json)
        
        self.assertEqual(message['type'], 'system_alert')
        self.assertEqual(message['payload']['alert_type'], 'warning')
        self.assertEqual(message['payload']['severity'], 'warning')
        self.assertEqual(message['payload']['details'], {"memory_usage": "85%"})

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
