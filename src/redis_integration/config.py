#!/usr/bin/env python3
"""
Redis Configuration for Match List Processor

Provides essential Redis configuration for pub/sub integration.
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RedisConfig:
    """Redis configuration for match list processor."""

    # Connection settings
    url: str = "redis://fogis-redis:6379"
    enabled: bool = True

    # Channel configuration
    match_updates_channel: str = "fogis:matches:updates"
    processor_status_channel: str = "fogis:processor:status"
    system_alerts_channel: str = "fogis:system:alerts"

    @classmethod
    def from_environment(cls) -> "RedisConfig":
        """Create Redis configuration from environment variables."""
        return cls(
            url=os.getenv("REDIS_URL", "redis://fogis-redis:6379"),
            enabled=os.getenv("REDIS_PUBSUB_ENABLED", "true").lower() in ("true", "1", "yes"),
            match_updates_channel=os.getenv("REDIS_MATCH_UPDATES_CHANNEL", "fogis:matches:updates"),
            processor_status_channel=os.getenv(
                "REDIS_PROCESSOR_STATUS_CHANNEL", "fogis:processor:status"
            ),
            system_alerts_channel=os.getenv("REDIS_SYSTEM_ALERTS_CHANNEL", "fogis:system:alerts"),
        )

    def get_channels(self) -> Dict[str, str]:
        """Get Redis channel configuration."""
        return {
            "match_updates": self.match_updates_channel,
            "processor_status": self.processor_status_channel,
            "system_alerts": self.system_alerts_channel,
        }


# Global configuration instance
_config: Optional[RedisConfig] = None


def get_redis_config() -> RedisConfig:
    """Get global Redis configuration."""
    global _config
    if _config is None:
        _config = RedisConfig.from_environment()
    return _config


def reload_redis_config() -> None:
    """Reload global Redis configuration from environment."""
    global _config
    _config = RedisConfig.from_environment()
