"""
Redis Integration Module for Match List Processor

This module provides Redis pub/sub integration for the FOGIS match list processor,
enabling real-time communication with other services through Redis channels.

Author: FOGIS System Architecture Team
Date: 2025-09-21
Issue: Redis pub/sub integration for match processor
"""

from .publisher import MatchProcessorRedisPublisher
from .message_formatter import MatchUpdateMessageFormatter, ProcessingStatusMessageFormatter
from .connection_manager import RedisConnectionManager
from .redis_service import MatchProcessorRedisService

__all__ = [
    'MatchProcessorRedisPublisher',
    'MatchUpdateMessageFormatter', 
    'ProcessingStatusMessageFormatter',
    'RedisConnectionManager',
    'MatchProcessorRedisService'
]

__version__ = "1.0.0"
__author__ = "FOGIS System Architecture Team"
