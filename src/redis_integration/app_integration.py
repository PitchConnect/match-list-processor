#!/usr/bin/env python3
"""
Redis Integration for Event-Driven Match List Processor

This module provides the Redis integration points for the existing EventDrivenMatchListProcessor,
enabling non-blocking Redis pub/sub communication while maintaining existing HTTP functionality.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis integration for event-driven match processor
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .services import MatchProcessorRedisService
from .config import get_redis_config

logger = logging.getLogger(__name__)

class MatchProcessorRedisIntegration:
    """Redis integration for the EventDrivenMatchListProcessor."""
    
    def __init__(self):
        """Initialize Redis integration."""
        self.redis_service: Optional[MatchProcessorRedisService] = None
        self.integration_enabled = False
        self.initialization_error: Optional[str] = None
        
        logger.info("🔧 Match Processor Redis Integration initializing...")
        
        # Initialize Redis service
        self._initialize_redis_service()
    
    def _initialize_redis_service(self) -> None:
        """Initialize Redis service with error handling."""
        try:
            config = get_redis_config()
            
            if not config.enabled:
                logger.info("📋 Redis integration disabled by configuration")
                return
            
            self.redis_service = MatchProcessorRedisService(
                redis_url=config.url,
                enabled=config.enabled
            )
            
            if self.redis_service.initialize_redis_publishing():
                self.integration_enabled = True
                logger.info("✅ Redis integration initialized successfully")
            else:
                logger.warning("⚠️ Redis integration initialized but not connected")
                # Keep integration enabled for retry attempts
                self.integration_enabled = True
                
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"❌ Failed to initialize Redis integration: {e}")
            logger.warning("⚠️ Redis integration will be disabled for this session")
    
    def publish_processing_start(self, processing_cycle: int = 0) -> bool:
        """
        Publish processing start notification.
        
        Args:
            processing_cycle: Current processing cycle number
            
        Returns:
            bool: True if published successfully (or disabled)
        """
        if not self.integration_enabled or not self.redis_service:
            return True
        
        try:
            processing_details = {
                'processing_cycle': processing_cycle,
                'start_time': datetime.now().isoformat()
            }
            
            return self.redis_service.handle_processing_start(processing_details)
            
        except Exception as e:
            logger.error(f"❌ Failed to publish processing start: {e}")
            return False
    
    def publish_match_updates(self, all_matches: List[Dict[str, Any]], 
                            changes: Dict[str, Any],
                            processing_start_time: datetime = None,
                            processing_cycle: int = 0) -> bool:
        """
        Publish match updates and processing completion.
        
        Args:
            all_matches: List of all processed matches
            changes: Change detection results
            processing_start_time: When processing started
            processing_cycle: Current processing cycle number
            
        Returns:
            bool: True if published successfully (or disabled)
        """
        if not self.integration_enabled or not self.redis_service:
            return True
        
        try:
            # Calculate processing duration
            processing_duration_ms = 0
            if processing_start_time:
                duration = datetime.now() - processing_start_time
                processing_duration_ms = int(duration.total_seconds() * 1000)
            
            # Prepare processing details
            processing_details = {
                'processing_cycle': processing_cycle,
                'processing_duration_ms': processing_duration_ms,
                'start_time': processing_start_time.isoformat() if processing_start_time else None,
                'end_time': datetime.now().isoformat()
            }
            
            # Add processing cycle to changes if not present
            if 'processing_cycle' not in changes:
                changes['processing_cycle'] = processing_cycle
            
            return self.redis_service.handle_match_processing_complete(
                all_matches, changes, processing_details
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to publish match updates: {e}")
            return False
    
    def publish_processing_error(self, error: Exception, 
                               processing_cycle: int = 0,
                               processing_start_time: datetime = None) -> bool:
        """
        Publish processing error notification.
        
        Args:
            error: Processing error that occurred
            processing_cycle: Current processing cycle number
            processing_start_time: When processing started
            
        Returns:
            bool: True if published successfully (or disabled)
        """
        if not self.integration_enabled or not self.redis_service:
            return True
        
        try:
            # Calculate processing duration
            processing_duration_ms = 0
            if processing_start_time:
                duration = datetime.now() - processing_start_time
                processing_duration_ms = int(duration.total_seconds() * 1000)
            
            processing_details = {
                'processing_cycle': processing_cycle,
                'processing_duration_ms': processing_duration_ms,
                'start_time': processing_start_time.isoformat() if processing_start_time else None
            }
            
            return self.redis_service.handle_processing_error(error, processing_details)
            
        except Exception as e:
            logger.error(f"❌ Failed to publish processing error: {e}")
            return False
    
    def get_redis_status(self) -> Dict[str, Any]:
        """
        Get Redis integration status.
        
        Returns:
            Dict[str, Any]: Redis integration status
        """
        if not self.integration_enabled:
            return {
                "integration_enabled": False,
                "status": "disabled",
                "message": "Redis integration disabled",
                "initialization_error": self.initialization_error
            }
        
        if not self.redis_service:
            return {
                "integration_enabled": False,
                "status": "error",
                "message": "Redis service not initialized",
                "initialization_error": self.initialization_error
            }
        
        redis_status = self.redis_service.get_redis_status()
        
        return {
            "integration_enabled": True,
            "redis_service": redis_status,
            "config": get_redis_config().to_dict()
        }
    
    def close(self) -> None:
        """Close Redis integration gracefully."""
        if self.redis_service:
            logger.info("🔌 Closing Redis integration")
            self.redis_service.close()

# Integration helper functions for existing match processor
def create_redis_integration() -> MatchProcessorRedisIntegration:
    """
    Create Redis integration instance.
    
    Returns:
        MatchProcessorRedisIntegration: Redis integration instance
    """
    return MatchProcessorRedisIntegration()

def add_redis_integration_to_processor(processor_instance, redis_integration: MatchProcessorRedisIntegration = None):
    """
    Add Redis integration to existing match processor instance.
    
    Args:
        processor_instance: Existing EventDrivenMatchListProcessor instance
        redis_integration: Redis integration instance (optional, creates new if not provided)
    """
    if redis_integration is None:
        redis_integration = create_redis_integration()
    
    # Add Redis integration as attribute
    processor_instance.redis_integration = redis_integration
    
    # Store original _process_matches_sync method
    original_process_matches_sync = processor_instance._process_matches_sync
    
    def _process_matches_sync_with_redis(self):
        """Enhanced _process_matches_sync with Redis integration."""
        processing_start_time = datetime.now()
        processing_cycle = getattr(self, '_processing_cycle', 0)
        
        # Increment processing cycle
        self._processing_cycle = processing_cycle + 1
        
        try:
            # Publish processing start
            if hasattr(self, 'redis_integration'):
                self.redis_integration.publish_processing_start(self._processing_cycle)
            
            # Call original processing method
            result = original_process_matches_sync()
            
            # Publish match updates if processing was successful
            if hasattr(self, 'redis_integration') and hasattr(self, '_all_matches') and hasattr(self, '_changes'):
                self.redis_integration.publish_match_updates(
                    self._all_matches,
                    self._changes,
                    processing_start_time,
                    self._processing_cycle
                )
            
            return result
            
        except Exception as e:
            # Publish processing error
            if hasattr(self, 'redis_integration'):
                self.redis_integration.publish_processing_error(
                    e, self._processing_cycle, processing_start_time
                )
            
            # Re-raise the exception to maintain existing error handling
            raise
    
    # Replace the method with Redis-enhanced version
    import types
    processor_instance._process_matches_sync = types.MethodType(_process_matches_sync_with_redis, processor_instance)
    
    # Initialize processing cycle counter
    processor_instance._processing_cycle = 0
    
    logger.info("✅ Redis integration added to match processor")

# Example integration code for existing match processor
INTEGRATION_EXAMPLE = '''
# Example of how to integrate Redis into existing EventDrivenMatchListProcessor

from app_event_driven_redis_integration import add_redis_integration_to_processor

class EventDrivenMatchListProcessor:
    def __init__(self):
        # Existing initialization code...
        
        # Add Redis integration
        add_redis_integration_to_processor(self)
    
    def _process_matches_sync(self):
        # This method will be automatically enhanced with Redis publishing
        # when add_redis_integration_to_processor() is called
        pass
    
    def get_status(self):
        # Add Redis status to existing status endpoint
        status = {
            # Existing status fields...
        }
        
        if hasattr(self, 'redis_integration'):
            status['redis'] = self.redis_integration.get_redis_status()
        
        return status
'''

if __name__ == "__main__":
    # Test Redis integration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis integration...")
    
    # Create integration
    integration = create_redis_integration()
    
    # Test status
    status = integration.get_redis_status()
    logger.info(f"📊 Integration Status: {status.get('status', 'unknown')}")
    
    if status.get('integration_enabled'):
        logger.info("✅ Redis integration test successful")
        
        # Test publishing
        test_matches = [
            {
                'matchid': 123456,
                'datum': '2025-09-23',
                'tid': '14:00',
                'hemmalag': 'Team A',
                'bortalag': 'Team B'
            }
        ]
        
        test_changes = {
            'new_matches': {123456: test_matches[0]},
            'updated_matches': {},
            'cancelled_matches': {}
        }
        
        # Test publishing
        if integration.publish_match_updates(test_matches, test_changes):
            logger.info("✅ Test publishing successful")
        else:
            logger.warning("⚠️ Test publishing failed (expected if Redis not available)")
    else:
        logger.warning("⚠️ Redis integration disabled or failed")
    
    # Close integration
    integration.close()
