#!/usr/bin/env python3
"""
Redis Publisher for Match List Processor

This module provides Redis publishing capabilities for the FOGIS match list processor,
enabling real-time communication with other services through Redis pub/sub channels.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis publishing for match processor
"""

import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .connection_manager import RedisConnectionManager, RedisConnectionConfig
from .message_formatter import (
    MatchUpdateMessageFormatter,
    ProcessingStatusMessageFormatter,
    create_match_update_message,
    create_processing_status_message,
    create_system_alert_message
)

logger = logging.getLogger(__name__)

@dataclass
class PublishResult:
    """Result of a Redis publish operation."""
    success: bool
    channel: str
    subscribers_notified: int
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class MatchProcessorRedisPublisher:
    """Redis publisher for match list processor with comprehensive error handling."""
    
    def __init__(self, redis_config: RedisConnectionConfig = None):
        """
        Initialize Redis publisher.
        
        Args:
            redis_config: Redis connection configuration
        """
        self.connection_manager = RedisConnectionManager(redis_config)
        self.channels = {
            'match_updates': 'fogis:matches:updates',
            'processor_status': 'fogis:processor:status',
            'system_alerts': 'fogis:system:alerts'
        }
        self.publish_stats = {
            'total_published': 0,
            'successful_publishes': 0,
            'failed_publishes': 0,
            'last_publish_time': None
        }
        
        logger.info(f"📡 Match Processor Redis Publisher initialized")
        logger.info(f"   Channels: {list(self.channels.values())}")
        
        # Test connection on initialization
        if self.connection_manager.ensure_connection():
            logger.info("✅ Redis connection established for publishing")
        else:
            logger.warning("⚠️ Redis connection not available - publishing will be disabled")
    
    def publish_match_updates(self, matches: List[Dict[str, Any]], 
                            changes: Dict[str, Any]) -> PublishResult:
        """
        Publish match updates to Redis channel.
        
        Args:
            matches: List of match dictionaries
            changes: Change detection results
            
        Returns:
            PublishResult: Result of publish operation
        """
        channel = self.channels['match_updates']
        
        try:
            # Format message
            message_json = create_match_update_message(matches, changes)
            message_dict = json.loads(message_json)
            message_id = message_dict.get('message_id')
            
            logger.info(f"📡 Publishing match updates to {channel}")
            logger.info(f"   Matches: {len(matches)}")
            logger.info(f"   Changes: {len(changes.get('new_matches', {}))} new, {len(changes.get('updated_matches', {}))} updated")
            logger.info(f"   Message ID: {message_id}")
            
            # Publish to Redis
            subscribers = self.connection_manager.publish(channel, message_json)
            
            if subscribers >= 0:
                self.publish_stats['successful_publishes'] += 1
                self.publish_stats['last_publish_time'] = datetime.now()
                
                logger.info(f"✅ Match updates published successfully")
                logger.info(f"   Subscribers notified: {subscribers}")
                
                return PublishResult(
                    success=True,
                    channel=channel,
                    subscribers_notified=subscribers,
                    message_id=message_id
                )
            else:
                self.publish_stats['failed_publishes'] += 1
                error_msg = "Redis publish failed - connection not available"
                
                logger.warning(f"⚠️ {error_msg}")
                
                return PublishResult(
                    success=False,
                    channel=channel,
                    subscribers_notified=0,
                    message_id=message_id,
                    error=error_msg
                )
                
        except Exception as e:
            self.publish_stats['failed_publishes'] += 1
            error_msg = f"Failed to publish match updates: {e}"
            
            logger.error(f"❌ {error_msg}")
            
            return PublishResult(
                success=False,
                channel=channel,
                subscribers_notified=0,
                error=error_msg
            )
        finally:
            self.publish_stats['total_published'] += 1
    
    def publish_processing_status(self, status: str, details: Dict[str, Any]) -> PublishResult:
        """
        Publish processing status to Redis channel.
        
        Args:
            status: Processing status (started, completed, failed, etc.)
            details: Processing details and statistics
            
        Returns:
            PublishResult: Result of publish operation
        """
        channel = self.channels['processor_status']
        
        try:
            # Format message
            message_json = create_processing_status_message(status, details)
            message_dict = json.loads(message_json)
            message_id = message_dict.get('message_id')
            
            logger.info(f"📊 Publishing processing status to {channel}")
            logger.info(f"   Status: {status}")
            logger.info(f"   Cycle: {details.get('cycle_number', 'N/A')}")
            logger.info(f"   Message ID: {message_id}")
            
            # Publish to Redis
            subscribers = self.connection_manager.publish(channel, message_json)
            
            if subscribers >= 0:
                self.publish_stats['successful_publishes'] += 1
                self.publish_stats['last_publish_time'] = datetime.now()
                
                logger.info(f"✅ Processing status published successfully")
                logger.info(f"   Subscribers notified: {subscribers}")
                
                return PublishResult(
                    success=True,
                    channel=channel,
                    subscribers_notified=subscribers,
                    message_id=message_id
                )
            else:
                self.publish_stats['failed_publishes'] += 1
                error_msg = "Redis publish failed - connection not available"
                
                logger.warning(f"⚠️ {error_msg}")
                
                return PublishResult(
                    success=False,
                    channel=channel,
                    subscribers_notified=0,
                    message_id=message_id,
                    error=error_msg
                )
                
        except Exception as e:
            self.publish_stats['failed_publishes'] += 1
            error_msg = f"Failed to publish processing status: {e}"
            
            logger.error(f"❌ {error_msg}")
            
            return PublishResult(
                success=False,
                channel=channel,
                subscribers_notified=0,
                error=error_msg
            )
        finally:
            self.publish_stats['total_published'] += 1
    
    def publish_system_alert(self, alert_type: str, message: str, severity: str = "info",
                           details: Dict[str, Any] = None) -> PublishResult:
        """
        Publish system alert to Redis channel.
        
        Args:
            alert_type: Type of alert (error, warning, info, etc.)
            message: Alert message
            severity: Alert severity level
            details: Additional alert details
            
        Returns:
            PublishResult: Result of publish operation
        """
        channel = self.channels['system_alerts']
        
        try:
            # Format message
            message_json = create_system_alert_message(alert_type, message, severity, details)
            message_dict = json.loads(message_json)
            message_id = message_dict.get('message_id')
            
            logger.info(f"🚨 Publishing system alert to {channel}")
            logger.info(f"   Type: {alert_type}")
            logger.info(f"   Severity: {severity}")
            logger.info(f"   Message ID: {message_id}")
            
            # Publish to Redis
            subscribers = self.connection_manager.publish(channel, message_json)
            
            if subscribers >= 0:
                self.publish_stats['successful_publishes'] += 1
                self.publish_stats['last_publish_time'] = datetime.now()
                
                logger.info(f"✅ System alert published successfully")
                logger.info(f"   Subscribers notified: {subscribers}")
                
                return PublishResult(
                    success=True,
                    channel=channel,
                    subscribers_notified=subscribers,
                    message_id=message_id
                )
            else:
                self.publish_stats['failed_publishes'] += 1
                error_msg = "Redis publish failed - connection not available"
                
                logger.warning(f"⚠️ {error_msg}")
                
                return PublishResult(
                    success=False,
                    channel=channel,
                    subscribers_notified=0,
                    message_id=message_id,
                    error=error_msg
                )
                
        except Exception as e:
            self.publish_stats['failed_publishes'] += 1
            error_msg = f"Failed to publish system alert: {e}"
            
            logger.error(f"❌ {error_msg}")
            
            return PublishResult(
                success=False,
                channel=channel,
                subscribers_notified=0,
                error=error_msg
            )
        finally:
            self.publish_stats['total_published'] += 1
    
    def get_publishing_stats(self) -> Dict[str, Any]:
        """
        Get publishing statistics and connection status.
        
        Returns:
            Dict[str, Any]: Publishing statistics and status
        """
        connection_status = self.connection_manager.get_connection_status()
        
        return {
            "publishing_stats": self.publish_stats.copy(),
            "connection_status": connection_status,
            "channels": self.channels.copy(),
            "redis_available": connection_status.get("redis_available", False),
            "is_connected": connection_status.get("is_connected", False)
        }
    
    def close(self) -> None:
        """Close Redis connection gracefully."""
        logger.info("🔌 Closing Redis publisher connection")
        self.connection_manager.close()

# Convenience functions for external use
def create_redis_publisher(redis_url: str = None) -> MatchProcessorRedisPublisher:
    """
    Create Redis publisher with optional custom URL.
    
    Args:
        redis_url: Custom Redis URL (optional)
        
    Returns:
        MatchProcessorRedisPublisher: Configured Redis publisher
    """
    config = RedisConnectionConfig()
    if redis_url:
        config.url = redis_url
    
    return MatchProcessorRedisPublisher(config)

if __name__ == "__main__":
    # Test Redis publisher
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis publisher...")
    
    # Create publisher
    publisher = create_redis_publisher()
    
    # Test match updates publishing
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
    
    # Publish test message
    result = publisher.publish_match_updates(test_matches, test_changes)
    
    if result.success:
        logger.info("✅ Redis publisher test successful")
        logger.info(f"📊 Subscribers notified: {result.subscribers_notified}")
    else:
        logger.warning("⚠️ Redis publisher test failed (expected if Redis not available)")
        logger.warning(f"   Error: {result.error}")
    
    # Get statistics
    stats = publisher.get_publishing_stats()
    logger.info(f"📊 Publishing Statistics:")
    logger.info(f"   Total Published: {stats['publishing_stats']['total_published']}")
    logger.info(f"   Successful: {stats['publishing_stats']['successful_publishes']}")
    logger.info(f"   Failed: {stats['publishing_stats']['failed_publishes']}")
    logger.info(f"   Redis Available: {stats['redis_available']}")
    logger.info(f"   Is Connected: {stats['is_connected']}")
    
    # Close publisher
    publisher.close()
