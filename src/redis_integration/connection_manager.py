#!/usr/bin/env python3
"""
Redis Connection Manager for Match List Processor

Provides Redis connection management for pub/sub integration.
"""

import logging
from typing import Optional

import redis

from .config import get_redis_config

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Manages Redis connections for the match processor."""

    def __init__(self):
        """Initialize Redis connection manager."""
        self.config = get_redis_config()
        self._client: Optional[redis.Redis] = None

    def get_client(self) -> Optional[redis.Redis]:
        """
        Get Redis client connection.

        Returns:
            Optional[redis.Redis]: Redis client or None if disabled/unavailable
        """
        if not self.config.enabled:
            return None

        if self._client is None:
            try:
                self._client = redis.from_url(self.config.url, decode_responses=True)
                # Test connection
                self._client.ping()
                logger.info(f"✅ Connected to Redis at {self.config.url}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to connect to Redis: {e}")
                self._client = None

        return self._client

    def is_connected(self) -> bool:
        """
        Check if Redis is connected and available.

        Returns:
            bool: True if Redis is connected
        """
        if not self.config.enabled:
            return False

        client = self.get_client()
        if client is None:
            return False

        try:
            client.ping()
            return True
        except Exception:
            logger.warning("⚠️ Redis connection lost")
            self._client = None
            return False

    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                self._client.close()
                logger.info("🔌 Redis connection closed")
            except Exception as e:
                logger.warning(f"⚠️ Error closing Redis connection: {e}")
            finally:
                self._client = None
