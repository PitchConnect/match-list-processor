"""
Redis Integration Module for Match List Processor

This module provides Redis pub/sub integration for the FOGIS match list processor,
enabling real-time communication with other services through Redis channels.

Enhanced Schema v2.0 Support:
- Organization ID mapping for logo service integration (issue #69)
- Complete contact data structure for calendar sync
- Multi-version publishing for backward compatibility

Author: FOGIS System Architecture Team
Date: 2025-09-26
Issue: Enhanced Schema v2.0 with Organization ID mapping (#69)
"""

from .app_integration import (
    EnhancedMatchProcessingIntegration,
    add_enhanced_redis_integration_to_processor,
    add_redis_integration_to_processor,
    create_redis_service,
)
from .config import RedisConfig, get_redis_config, reload_redis_config
from .connection_manager import RedisConnectionManager
from .message_formatter import (
    EnhancedSchemaV2Formatter,
    MatchUpdateMessageFormatter,
    ProcessingStatusMessageFormatter,
)
from .publisher import MatchProcessorRedisPublisher, PublishResult
from .services import MatchProcessorRedisService

__all__ = [
    "RedisConfig",
    "get_redis_config",
    "reload_redis_config",
    "RedisConnectionManager",
    "MatchUpdateMessageFormatter",
    "ProcessingStatusMessageFormatter",
    "EnhancedSchemaV2Formatter",
    "MatchProcessorRedisPublisher",
    "PublishResult",
    "MatchProcessorRedisService",
    "add_redis_integration_to_processor",
    "create_redis_service",
    "EnhancedMatchProcessingIntegration",
    "add_enhanced_redis_integration_to_processor",
]

__version__ = "2.0.0"
__author__ = "FOGIS System Architecture Team"
