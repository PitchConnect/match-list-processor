"""
Redis Integration Module for Match List Processor

This module provides Redis pub/sub integration for the FOGIS match list processor,
enabling real-time communication with other services through Redis channels.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration for match processor
"""

from .app_integration import add_redis_integration_to_processor, create_redis_service
from .config import RedisConfig, get_redis_config, reload_redis_config
from .connection_manager import RedisConnectionManager
from .message_formatter import MatchUpdateMessageFormatter, ProcessingStatusMessageFormatter
from .publisher import MatchProcessorRedisPublisher, PublishResult
from .services import MatchProcessorRedisService

__all__ = [
    "RedisConfig",
    "get_redis_config",
    "reload_redis_config",
    "RedisConnectionManager",
    "MatchUpdateMessageFormatter",
    "ProcessingStatusMessageFormatter",
    "MatchProcessorRedisPublisher",
    "PublishResult",
    "MatchProcessorRedisService",
    "add_redis_integration_to_processor",
    "create_redis_service",
]

__version__ = "1.0.0"
__author__ = "FOGIS System Architecture Team"
