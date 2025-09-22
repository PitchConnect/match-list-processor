#!/usr/bin/env python3
"""
Tests for Redis Configuration Module

This module tests the Redis configuration functionality for the match list processor.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis configuration testing for CI/CD coverage
"""

import os
import unittest
from unittest.mock import patch

from src.redis_integration.config import (
    RedisConfig,
    RedisConfigManager,
    get_redis_config,
    get_redis_config_manager,
    reload_redis_config,
)


class TestRedisConfig(unittest.TestCase):
    """Test Redis configuration functionality."""

    def test_redis_config_creation_with_defaults(self):
        """Test Redis config creation with default values."""
        config = RedisConfig()

        self.assertTrue(config.enabled)
        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertEqual(config.socket_connect_timeout, 5)
        self.assertEqual(config.socket_timeout, 5)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.retry_delay, 1.0)
        self.assertTrue(config.decode_responses)

    def test_redis_config_creation_with_custom_values(self):
        """Test Redis config creation with custom values."""
        config = RedisConfig(
            enabled=False,
            url="redis://custom:6380",
            socket_connect_timeout=10,
            socket_timeout=10,
            max_retries=5,
            retry_delay=2.0
        )

        self.assertFalse(config.enabled)
        self.assertEqual(config.url, "redis://custom:6380")
        self.assertEqual(config.socket_connect_timeout, 10)
        self.assertEqual(config.socket_timeout, 10)
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.retry_delay, 2.0)

    def test_redis_config_to_dict(self):
        """Test Redis config to_dict method."""
        config = RedisConfig(enabled=True, url="redis://test:6380")
        config_dict = config.to_dict()

        self.assertIsInstance(config_dict, dict)
        self.assertTrue(config_dict["enabled"])
        self.assertEqual(config_dict["url"], "redis://test:6380")
        self.assertIn("socket_timeout", config_dict)
        self.assertIn("max_retries", config_dict)

    def test_redis_config_from_environment(self):
        """Test Redis config from environment variables."""
        with patch.dict(os.environ, {
            "REDIS_ENABLED": "false",
            "REDIS_URL": "redis://env:6380",
            "REDIS_SOCKET_TIMEOUT": "10"
        }):
            config = RedisConfig.from_environment()

            self.assertFalse(config.enabled)
            self.assertEqual(config.url, "redis://env:6380")
            self.assertEqual(config.socket_timeout, 10)

    def test_redis_config_channels(self):
        """Test Redis config channel configuration."""
        config = RedisConfig()
        channels = config.get_channels()

        self.assertIsInstance(channels, dict)
        self.assertIn("match_updates", channels)
        self.assertIn("processor_status", channels)
        self.assertIn("system_alerts", channels)

    def test_get_redis_config_function(self):
        """Test getting Redis config through global function."""
        config = get_redis_config()

        self.assertIsInstance(config, RedisConfig)
        self.assertIsNotNone(config.url)

    def test_get_redis_config_manager_function(self):
        """Test getting Redis config manager."""
        manager = get_redis_config_manager()

        self.assertIsInstance(manager, RedisConfigManager)

    def test_reload_redis_config_function(self):
        """Test reloading Redis config."""
        # Should not raise exception
        reload_redis_config()

    def test_redis_config_manager_initialization(self):
        """Test Redis config manager initialization."""
        manager = RedisConfigManager()

        self.assertIsNotNone(manager.get_config())

    def test_redis_config_manager_with_custom_config(self):
        """Test Redis config manager with custom config."""
        custom_config = RedisConfig(enabled=False)
        manager = RedisConfigManager(custom_config)

        config = manager.get_config()
        self.assertFalse(config.enabled)

    def test_redis_config_manager_reload(self):
        """Test Redis config manager reload functionality."""
        manager = RedisConfigManager()
        original_config = manager.get_config()

        # Reload should not raise exception
        manager.reload_from_environment()

        reloaded_config = manager.get_config()
        self.assertIsInstance(reloaded_config, RedisConfig)

    def test_redis_config_manager_update(self):
        """Test Redis config manager update functionality."""
        manager = RedisConfigManager()
        new_config = RedisConfig(enabled=False, url="redis://test:6380")

        manager.update_config(new_config)

        updated_config = manager.get_config()
        self.assertFalse(updated_config.enabled)
        self.assertEqual(updated_config.url, "redis://test:6380")

    def test_redis_config_manager_validate(self):
        """Test Redis config manager validation."""
        manager = RedisConfigManager()

        # Should return validation result
        is_valid = manager.validate_config()
        self.assertIsInstance(is_valid, bool)

    def test_redis_config_str_representation(self):
        """Test Redis config string representation."""
        config = RedisConfig(enabled=True, url="redis://test:6380")
        config_str = str(config)

        self.assertIsInstance(config_str, str)
        self.assertIn("RedisConfig", config_str)

    def test_redis_config_repr_representation(self):
        """Test Redis config repr representation."""
        config = RedisConfig(enabled=True, url="redis://test:6380")
        config_repr = repr(config)

        self.assertIsInstance(config_repr, str)
        self.assertIn("RedisConfig", config_repr)

    def test_redis_config_equality(self):
        """Test Redis config equality comparison."""
        config1 = RedisConfig(enabled=True, url="redis://test:6379")
        config2 = RedisConfig(enabled=True, url="redis://test:6379")
        config3 = RedisConfig(enabled=False, url="redis://test:6379")

        self.assertEqual(config1, config2)
        self.assertNotEqual(config1, config3)

    def test_redis_config_environment_parsing(self):
        """Test Redis config environment variable parsing."""
        with patch.dict(os.environ, {
            "REDIS_ENABLED": "true",
            "REDIS_MAX_RETRIES": "5"
        }):
            config = RedisConfig.from_environment()

            self.assertTrue(config.enabled)
            self.assertEqual(config.max_retries, 5)


if __name__ == "__main__":
    unittest.main()
