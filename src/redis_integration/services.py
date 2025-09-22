#!/usr/bin/env python3
"""
Redis Service Integration for Match List Processor

This module provides high-level Redis service integration for the FOGIS match list processor,
coordinating Redis publishing with the existing match processing workflow.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis service integration for match processor
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from .publisher import MatchProcessorRedisPublisher
from .connection_manager import RedisConnectionConfig

logger = logging.getLogger(__name__)

class MatchProcessorRedisService:
    """High-level Redis service integration for match processor."""
    
    def __init__(self, redis_url: str = None, enabled: bool = None):
        """
        Initialize Redis service integration.
        
        Args:
            redis_url: Redis connection URL (optional, uses environment variable if not provided)
            enabled: Whether Redis integration is enabled (optional, uses environment variable if not provided)
        """
        # Configuration from environment variables
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://fogis-redis:6379')
        self.enabled = enabled if enabled is not None else os.getenv('REDIS_PUBSUB_ENABLED', 'true').lower() == 'true'
        
        # Initialize publisher if enabled
        self.publisher: Optional[MatchProcessorRedisPublisher] = None
        self.initialization_error: Optional[str] = None
        
        logger.info(f"🔧 Match Processor Redis Service initializing...")
        logger.info(f"   Redis URL: {self.redis_url}")
        logger.info(f"   Enabled: {self.enabled}")
        
        if self.enabled:
            self._initialize_redis_publisher()
        else:
            logger.info("📋 Redis integration disabled by configuration")
    
    def _initialize_redis_publisher(self) -> bool:
        """
        Initialize Redis publisher with error handling.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            config = RedisConnectionConfig(url=self.redis_url)
            self.publisher = MatchProcessorRedisPublisher(config)
            
            logger.info("✅ Redis publisher initialized successfully")
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"❌ Failed to initialize Redis publisher: {e}")
            logger.warning("⚠️ Redis integration will be disabled for this session")
            return False
    
    def initialize_redis_publishing(self) -> bool:
        """
        Initialize Redis publishing capabilities.
        
        Returns:
            bool: True if Redis publishing is available
        """
        if not self.enabled:
            logger.info("📋 Redis publishing disabled by configuration")
            return False
        
        if self.publisher is None:
            return self._initialize_redis_publisher()
        
        # Test connection
        stats = self.publisher.get_publishing_stats()
        if stats.get('is_connected', False):
            logger.info("✅ Redis publishing already initialized and connected")
            return True
        else:
            logger.warning("⚠️ Redis publisher initialized but not connected")
            return False
    
    def handle_match_processing_complete(self, matches: List[Dict[str, Any]], 
                                       changes: Dict[str, Any],
                                       processing_details: Dict[str, Any] = None) -> bool:
        """
        Handle match processing completion with Redis publishing.
        
        Args:
            matches: List of processed matches
            changes: Change detection results
            processing_details: Additional processing details
            
        Returns:
            bool: True if Redis publishing successful (or disabled)
        """
        if not self.enabled or self.publisher is None:
            logger.debug("📋 Redis publishing disabled - skipping match updates")
            return True
        
        try:
            logger.info("📡 Publishing match processing completion to Redis...")
            
            # Publish match updates
            match_result = self.publisher.publish_match_updates(matches, changes)
            
            # Prepare processing status details
            status_details = {
                'cycle_number': changes.get('processing_cycle', 0),
                'processing_duration_ms': processing_details.get('processing_duration_ms', 0) if processing_details else 0,
                'matches_processed': len(matches),
                'changes_detected': changes.get('has_changes', False),
                'start_time': processing_details.get('start_time') if processing_details else None,
                'end_time': processing_details.get('end_time') if processing_details else datetime.now().isoformat(),
                'services_notified': [],
                'redis_publishing': {
                    'match_updates': {
                        'success': match_result.success,
                        'subscribers': match_result.subscribers_notified,
                        'message_id': match_result.message_id
                    }
                }
            }
            
            # Add Redis publishing result to services notified
            if match_result.success:
                status_details['services_notified'].append('redis_pubsub')
            
            # Publish processing status
            status_result = self.publisher.publish_processing_status("completed", status_details)
            
            # Update Redis publishing details
            status_details['redis_publishing']['processing_status'] = {
                'success': status_result.success,
                'subscribers': status_result.subscribers_notified,
                'message_id': status_result.message_id
            }
            
            # Log results
            if match_result.success and status_result.success:
                logger.info("✅ Match processing completion published to Redis successfully")
                logger.info(f"   Match updates: {match_result.subscribers_notified} subscribers")
                logger.info(f"   Processing status: {status_result.subscribers_notified} subscribers")
                return True
            else:
                logger.warning("⚠️ Partial Redis publishing failure")
                if not match_result.success:
                    logger.warning(f"   Match updates failed: {match_result.error}")
                if not status_result.success:
                    logger.warning(f"   Processing status failed: {status_result.error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to handle match processing completion: {e}")
            return False
    
    def handle_processing_error(self, error: Exception, 
                              processing_details: Dict[str, Any] = None) -> bool:
        """
        Handle processing errors with Redis notifications.
        
        Args:
            error: Processing error that occurred
            processing_details: Additional processing details
            
        Returns:
            bool: True if Redis notification successful (or disabled)
        """
        if not self.enabled or self.publisher is None:
            logger.debug("📋 Redis publishing disabled - skipping error notification")
            return True
        
        try:
            logger.info("🚨 Publishing processing error to Redis...")
            
            # Prepare error details
            error_details = {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'processing_details': processing_details or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Publish system alert
            alert_result = self.publisher.publish_system_alert(
                alert_type="processing_error",
                message=f"Match processing failed: {str(error)}",
                severity="error",
                details=error_details
            )
            
            # Publish processing status
            status_details = {
                'cycle_number': processing_details.get('processing_cycle', 0) if processing_details else 0,
                'processing_duration_ms': processing_details.get('processing_duration_ms', 0) if processing_details else 0,
                'matches_processed': 0,
                'errors': [str(error)],
                'start_time': processing_details.get('start_time') if processing_details else None,
                'end_time': datetime.now().isoformat(),
                'redis_publishing': {
                    'system_alert': {
                        'success': alert_result.success,
                        'subscribers': alert_result.subscribers_notified,
                        'message_id': alert_result.message_id
                    }
                }
            }
            
            status_result = self.publisher.publish_processing_status("failed", status_details)
            
            # Log results
            if alert_result.success and status_result.success:
                logger.info("✅ Processing error published to Redis successfully")
                logger.info(f"   System alert: {alert_result.subscribers_notified} subscribers")
                logger.info(f"   Processing status: {status_result.subscribers_notified} subscribers")
                return True
            else:
                logger.warning("⚠️ Partial Redis error notification failure")
                if not alert_result.success:
                    logger.warning(f"   System alert failed: {alert_result.error}")
                if not status_result.success:
                    logger.warning(f"   Processing status failed: {status_result.error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to handle processing error notification: {e}")
            return False
    
    def handle_processing_start(self, processing_details: Dict[str, Any] = None) -> bool:
        """
        Handle processing start with Redis notifications.
        
        Args:
            processing_details: Processing details and configuration
            
        Returns:
            bool: True if Redis notification successful (or disabled)
        """
        if not self.enabled or self.publisher is None:
            logger.debug("📋 Redis publishing disabled - skipping start notification")
            return True
        
        try:
            logger.info("🚀 Publishing processing start to Redis...")
            
            # Prepare status details
            status_details = {
                'cycle_number': processing_details.get('processing_cycle', 0) if processing_details else 0,
                'start_time': processing_details.get('start_time') if processing_details else datetime.now().isoformat(),
                'expected_duration_ms': processing_details.get('expected_duration_ms', 0) if processing_details else 0,
                'matches_to_process': processing_details.get('matches_to_process', 0) if processing_details else 0
            }
            
            # Publish processing status
            result = self.publisher.publish_processing_status("started", status_details)
            
            if result.success:
                logger.info("✅ Processing start published to Redis successfully")
                logger.info(f"   Subscribers notified: {result.subscribers_notified}")
                return True
            else:
                logger.warning(f"⚠️ Failed to publish processing start: {result.error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to handle processing start notification: {e}")
            return False
    
    def get_redis_status(self) -> Dict[str, Any]:
        """
        Get Redis service status and statistics.
        
        Returns:
            Dict[str, Any]: Redis service status information
        """
        if not self.enabled:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "Redis integration disabled by configuration"
            }
        
        if self.publisher is None:
            return {
                "enabled": True,
                "status": "error",
                "message": "Redis publisher not initialized",
                "initialization_error": self.initialization_error
            }
        
        # Get publisher statistics
        stats = self.publisher.get_publishing_stats()
        
        return {
            "enabled": True,
            "status": "connected" if stats.get('is_connected', False) else "disconnected",
            "redis_url": self.redis_url,
            "publishing_stats": stats.get('publishing_stats', {}),
            "connection_status": stats.get('connection_status', {}),
            "channels": stats.get('channels', {}),
            "redis_available": stats.get('redis_available', False)
        }
    
    def close(self) -> None:
        """Close Redis service gracefully."""
        if self.publisher:
            logger.info("🔌 Closing Redis service")
            self.publisher.close()
            self.publisher = None

# Convenience functions for external use
def create_redis_service(redis_url: str = None, enabled: bool = None) -> MatchProcessorRedisService:
    """
    Create Redis service with optional configuration.
    
    Args:
        redis_url: Custom Redis URL (optional)
        enabled: Whether Redis integration is enabled (optional)
        
    Returns:
        MatchProcessorRedisService: Configured Redis service
    """
    return MatchProcessorRedisService(redis_url, enabled)

if __name__ == "__main__":
    # Test Redis service
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis service...")
    
    # Create service
    service = create_redis_service()
    
    # Test initialization
    if service.initialize_redis_publishing():
        logger.info("✅ Redis service initialization test successful")
    else:
        logger.warning("⚠️ Redis service initialization test failed (expected if Redis not available)")
    
    # Get status
    status = service.get_redis_status()
    logger.info(f"📊 Redis Service Status: {status['status']}")
    logger.info(f"   Enabled: {status['enabled']}")
    
    if status.get('redis_available'):
        logger.info(f"   Redis Available: {status['redis_available']}")
        logger.info(f"   Publishing Stats: {status.get('publishing_stats', {})}")
    
    # Close service
    service.close()
