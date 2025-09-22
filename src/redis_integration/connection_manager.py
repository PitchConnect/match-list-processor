#!/usr/bin/env python3
"""
Redis Connection Manager for Match List Processor

This module provides Redis connection management with automatic reconnection,
health monitoring, and graceful degradation for the match list processor.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis connection management for match processor
"""

import logging
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class RedisConnectionConfig:
    """Configuration for Redis connection."""
    url: str = "redis://fogis-redis:6379"
    decode_responses: bool = True
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

class RedisConnectionManager:
    """Manages Redis connections with automatic reconnection and health monitoring."""
    
    def __init__(self, config: RedisConnectionConfig = None):
        """
        Initialize Redis connection manager.
        
        Args:
            config: Redis connection configuration
        """
        self.config = config or RedisConnectionConfig()
        self.client: Optional[redis.Redis] = None
        self.last_health_check = datetime.min
        self.connection_attempts = 0
        self.is_connected = False
        self.last_error: Optional[str] = None
        
        logger.info(f"🔧 Redis Connection Manager initialized")
        logger.info(f"   Redis URL: {self.config.url}")
        logger.info(f"   Redis Available: {REDIS_AVAILABLE}")
        
        if REDIS_AVAILABLE:
            self._connect()
        else:
            logger.warning("⚠️ Redis package not available - Redis functionality disabled")
    
    def _connect(self) -> bool:
        """
        Establish Redis connection with retry logic.
        
        Returns:
            bool: True if connection successful
        """
        if not REDIS_AVAILABLE:
            return False
        
        try:
            logger.debug(f"🔌 Attempting Redis connection (attempt {self.connection_attempts + 1})")
            
            self.client = redis.from_url(
                self.config.url,
                decode_responses=self.config.decode_responses,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_timeout=self.config.socket_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # Test connection
            self.client.ping()
            
            self.is_connected = True
            self.last_error = None
            self.connection_attempts = 0
            self.last_health_check = datetime.now()
            
            logger.info("✅ Redis connection established successfully")
            return True
            
        except Exception as e:
            self.is_connected = False
            self.last_error = str(e)
            self.connection_attempts += 1
            
            logger.warning(f"⚠️ Redis connection failed (attempt {self.connection_attempts}): {e}")
            return False
    
    def ensure_connection(self) -> bool:
        """
        Ensure Redis connection is active, reconnect if necessary.
        
        Returns:
            bool: True if connection is active
        """
        if not REDIS_AVAILABLE:
            return False
        
        # Check if we need to perform health check
        now = datetime.now()
        if (now - self.last_health_check).seconds >= self.config.health_check_interval:
            self._health_check()
        
        # If not connected, try to reconnect
        if not self.is_connected:
            if self.connection_attempts < self.config.max_retries:
                time.sleep(self.config.retry_delay)
                return self._connect()
            else:
                logger.error(f"❌ Redis connection failed after {self.config.max_retries} attempts")
                return False
        
        return True
    
    def _health_check(self) -> bool:
        """
        Perform Redis health check.
        
        Returns:
            bool: True if Redis is healthy
        """
        if not REDIS_AVAILABLE or not self.client:
            return False
        
        try:
            self.client.ping()
            self.is_connected = True
            self.last_health_check = datetime.now()
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Redis health check failed: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return False
    
    def publish(self, channel: str, message: str) -> int:
        """
        Publish message to Redis channel with automatic reconnection.
        
        Args:
            channel: Redis channel name
            message: Message to publish
            
        Returns:
            int: Number of subscribers that received the message, -1 if failed
        """
        if not self.ensure_connection():
            logger.warning(f"⚠️ Cannot publish to {channel}: Redis not available")
            return -1
        
        try:
            result = self.client.publish(channel, message)
            logger.debug(f"📡 Published to {channel}: {result} subscribers notified")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to publish to {channel}: {e}")
            self.is_connected = False
            self.last_error = str(e)
            return -1
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and statistics.
        
        Returns:
            Dict[str, Any]: Connection status information
        """
        return {
            "redis_available": REDIS_AVAILABLE,
            "is_connected": self.is_connected,
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check != datetime.min else None,
            "config": {
                "url": self.config.url,
                "timeout": self.config.socket_timeout,
                "max_retries": self.config.max_retries
            }
        }
    
    def close(self) -> None:
        """Close Redis connection gracefully."""
        if self.client:
            try:
                self.client.close()
                logger.info("🔌 Redis connection closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing Redis connection: {e}")
            finally:
                self.client = None
                self.is_connected = False

# Convenience functions for external use
def create_redis_connection(redis_url: str = None) -> RedisConnectionManager:
    """
    Create Redis connection manager with optional custom URL.
    
    Args:
        redis_url: Custom Redis URL (optional)
        
    Returns:
        RedisConnectionManager: Configured connection manager
    """
    config = RedisConnectionConfig()
    if redis_url:
        config.url = redis_url
    
    return RedisConnectionManager(config)

def test_redis_connection(redis_url: str = None) -> bool:
    """
    Test Redis connection availability.
    
    Args:
        redis_url: Custom Redis URL (optional)
        
    Returns:
        bool: True if Redis is available and connectable
    """
    manager = create_redis_connection(redis_url)
    status = manager.ensure_connection()
    manager.close()
    return status

if __name__ == "__main__":
    # Test Redis connection
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis connection manager...")
    
    # Test connection
    if test_redis_connection():
        logger.info("✅ Redis connection test successful")
    else:
        logger.error("❌ Redis connection test failed")
    
    # Test connection manager
    manager = create_redis_connection()
    status = manager.get_connection_status()
    
    logger.info(f"📊 Connection Status:")
    logger.info(f"   Redis Available: {status['redis_available']}")
    logger.info(f"   Is Connected: {status['is_connected']}")
    logger.info(f"   Connection Attempts: {status['connection_attempts']}")
    
    if status['last_error']:
        logger.info(f"   Last Error: {status['last_error']}")
    
    manager.close()
