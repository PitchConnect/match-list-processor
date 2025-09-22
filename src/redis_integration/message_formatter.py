#!/usr/bin/env python3
"""
Message Formatting for Match List Processor Redis Integration

This module provides message formatting utilities for Redis pub/sub communication,
ensuring consistent message structure across FOGIS services.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis message formatting for match processor
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of message validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class MatchUpdateMessageFormatter:
    """Formats match update messages for Redis publishing."""
    
    @staticmethod
    def format_match_updates(matches: List[Dict[str, Any]], changes: Dict[str, Any], 
                           source: str = "match-list-processor") -> Dict[str, Any]:
        """
        Format match updates message according to FOGIS Redis schema.
        
        Args:
            matches: List of match dictionaries
            changes: Change detection results
            source: Source service identifier
            
        Returns:
            Dict[str, Any]: Formatted message ready for Redis publishing
        """
        # Generate change summary
        change_summary = {
            "new_matches": len(changes.get('new_matches', {})),
            "updated_matches": len(changes.get('updated_matches', {})),
            "cancelled_matches": len(changes.get('cancelled_matches', {})),
            "total_changes": 0
        }
        change_summary["total_changes"] = (
            change_summary["new_matches"] + 
            change_summary["updated_matches"] + 
            change_summary["cancelled_matches"]
        )
        
        # Extract change details
        change_detection = {
            "new_match_ids": list(changes.get('new_matches', {}).keys()),
            "updated_match_ids": list(changes.get('updated_matches', {}).keys()),
            "cancelled_match_ids": list(changes.get('cancelled_matches', {}).keys()),
            "change_types": []
        }
        
        # Determine change types
        if change_summary["new_matches"] > 0:
            change_detection["change_types"].append("new_matches")
        if change_summary["updated_matches"] > 0:
            change_detection["change_types"].append("match_updates")
        if change_summary["cancelled_matches"] > 0:
            change_detection["change_types"].append("match_cancellations")
        
        # Add specific change types for updated matches
        for match_id, match_changes in changes.get('updated_matches', {}).items():
            if 'domare1' in match_changes or 'domare1_telefon' in match_changes:
                if "referee_assignment" not in change_detection["change_types"]:
                    change_detection["change_types"].append("referee_assignment")
            if 'tid' in match_changes or 'datum' in match_changes:
                if "time_change" not in change_detection["change_types"]:
                    change_detection["change_types"].append("time_change")
            if 'arena' in match_changes or 'anlaggningnamn' in match_changes:
                if "venue_change" not in change_detection["change_types"]:
                    change_detection["change_types"].append("venue_change")
        
        # Build the complete message
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": matches,
                "metadata": {
                    "total_matches": len(matches),
                    "has_changes": change_summary["total_changes"] > 0,
                    "change_summary": change_summary,
                    "processing_cycle": changes.get('processing_cycle', 0),
                    "change_detection": change_detection,
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
        }
        
        return message
    
    @staticmethod
    def validate_match_update_message(message: Dict[str, Any]) -> ValidationResult:
        """
        Validate match update message format.
        
        Args:
            message: Message to validate
            
        Returns:
            ValidationResult: Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Required top-level fields
        required_fields = ['message_id', 'timestamp', 'source', 'version', 'type', 'payload']
        for field in required_fields:
            if field not in message:
                errors.append(f"Missing required field: {field}")
        
        # Validate message type
        if message.get('type') != 'match_updates':
            errors.append(f"Invalid message type: {message.get('type')}, expected 'match_updates'")
        
        # Validate payload structure
        if 'payload' in message:
            payload = message['payload']
            
            if 'matches' not in payload:
                errors.append("Missing 'matches' in payload")
            elif not isinstance(payload['matches'], list):
                errors.append("'matches' must be a list")
            
            if 'metadata' not in payload:
                errors.append("Missing 'metadata' in payload")
            elif isinstance(payload['metadata'], dict):
                metadata = payload['metadata']
                
                # Check metadata fields
                if 'total_matches' not in metadata:
                    warnings.append("Missing 'total_matches' in metadata")
                elif metadata['total_matches'] != len(payload.get('matches', [])):
                    warnings.append("'total_matches' doesn't match actual matches count")
                
                if 'has_changes' not in metadata:
                    warnings.append("Missing 'has_changes' in metadata")
                
                if 'change_summary' not in metadata:
                    warnings.append("Missing 'change_summary' in metadata")
        
        # Validate match structure
        if 'payload' in message and 'matches' in message['payload']:
            matches = message['payload']['matches']
            for i, match in enumerate(matches):
                if not isinstance(match, dict):
                    errors.append(f"Match {i} is not a dictionary")
                    continue
                
                # Check for essential match fields
                essential_fields = ['matchid', 'datum', 'hemmalag', 'bortalag']
                for field in essential_fields:
                    if field not in match:
                        warnings.append(f"Match {i} missing recommended field: {field}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class ProcessingStatusMessageFormatter:
    """Formats processing status messages for Redis publishing."""
    
    @staticmethod
    def format_processing_status(status: str, details: Dict[str, Any], 
                               source: str = "match-list-processor") -> Dict[str, Any]:
        """
        Format processing status message.
        
        Args:
            status: Processing status (started, completed, failed, etc.)
            details: Processing details and statistics
            source: Source service identifier
            
        Returns:
            Dict[str, Any]: Formatted status message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "version": "1.0",
            "type": "processing_status",
            "payload": {
                "status": status,
                "cycle_number": details.get('cycle_number', 0),
                "processing_duration_ms": details.get('processing_duration_ms', 0),
                "matches_processed": details.get('matches_processed', 0),
                "errors": details.get('errors', []),
                "next_processing_time": details.get('next_processing_time'),
                "details": {
                    "start_time": details.get('start_time'),
                    "end_time": details.get('end_time'),
                    "changes_detected": details.get('changes_detected', False),
                    "services_notified": details.get('services_notified', []),
                    "redis_publishing": details.get('redis_publishing', {})
                }
            }
        }
        
        return message
    
    @staticmethod
    def format_system_alert(alert_type: str, message: str, severity: str = "info",
                          details: Dict[str, Any] = None, 
                          source: str = "match-list-processor") -> Dict[str, Any]:
        """
        Format system alert message.
        
        Args:
            alert_type: Type of alert (error, warning, info, etc.)
            message: Alert message
            severity: Alert severity level
            details: Additional alert details
            source: Source service identifier
            
        Returns:
            Dict[str, Any]: Formatted alert message
        """
        alert_message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "version": "1.0",
            "type": "system_alert",
            "payload": {
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "details": details or {},
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return alert_message

# Convenience functions for external use
def create_match_update_message(matches: List[Dict], changes: Dict, 
                              source: str = "match-list-processor") -> str:
    """
    Create and serialize match update message.
    
    Args:
        matches: List of match dictionaries
        changes: Change detection results
        source: Source service identifier
        
    Returns:
        str: JSON-serialized message ready for Redis publishing
    """
    message = MatchUpdateMessageFormatter.format_match_updates(matches, changes, source)
    return json.dumps(message)

def create_processing_status_message(status: str, details: Dict, 
                                   source: str = "match-list-processor") -> str:
    """
    Create and serialize processing status message.
    
    Args:
        status: Processing status
        details: Processing details
        source: Source service identifier
        
    Returns:
        str: JSON-serialized message ready for Redis publishing
    """
    message = ProcessingStatusMessageFormatter.format_processing_status(status, details, source)
    return json.dumps(message)

def create_system_alert_message(alert_type: str, message: str, severity: str = "info",
                              details: Dict = None, source: str = "match-list-processor") -> str:
    """
    Create and serialize system alert message.
    
    Args:
        alert_type: Type of alert
        message: Alert message
        severity: Alert severity
        details: Additional details
        source: Source service identifier
        
    Returns:
        str: JSON-serialized message ready for Redis publishing
    """
    alert_message = ProcessingStatusMessageFormatter.format_system_alert(
        alert_type, message, severity, details, source
    )
    return json.dumps(alert_message)

if __name__ == "__main__":
    # Test message formatting
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 Testing message formatting...")
    
    # Test match update message
    test_matches = [
        {
            'matchid': 123456,
            'datum': '2025-09-23',
            'tid': '14:00',
            'hemmalag': 'Team A',
            'bortalag': 'Team B',
            'arena': 'Stadium Name'
        }
    ]
    
    test_changes = {
        'new_matches': {123456: test_matches[0]},
        'updated_matches': {},
        'cancelled_matches': {},
        'processing_cycle': 42
    }
    
    # Create and validate message
    message_json = create_match_update_message(test_matches, test_changes)
    message = json.loads(message_json)
    
    validation = MatchUpdateMessageFormatter.validate_match_update_message(message)
    
    if validation.is_valid:
        logger.info("✅ Match update message formatting test successful")
        logger.info(f"📊 Message size: {len(message_json)} bytes")
    else:
        logger.error("❌ Match update message formatting test failed")
        for error in validation.errors:
            logger.error(f"   - {error}")
    
    if validation.warnings:
        for warning in validation.warnings:
            logger.warning(f"   ⚠️ {warning}")
    
    # Test processing status message
    status_json = create_processing_status_message("completed", {
        'cycle_number': 42,
        'processing_duration_ms': 2500,
        'matches_processed': 15
    })
    
    logger.info("✅ Processing status message formatting test successful")
    logger.info(f"📊 Status message size: {len(status_json)} bytes")
