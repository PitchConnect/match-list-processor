#!/usr/bin/env python3
"""
Tests for Redis Connection Manager

This module tests the Redis connection management functionality.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis connection manager testing for CI/CD coverage
"""

import unittest
from unittest.mock import Mock, patch

import redis

from src.redis_integration.connection_manager import (
    RedisConnectionConfig,
    RedisConnectionManager,
    create_redis_connection,
    test_redis_connection,
)


class TestRedisConnectionManager(unittest.TestCase):
    """Test Redis connection manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = RedisConnectionConfig(
            url="redis://test_host:6379",
            socket_connect_timeout=5,
            socket_timeout=5,
            max_retries=3,
            retry_delay=1.0,
        )
        self.manager = RedisConnectionManager(self.config)

    def test_connection_manager_initialization(self):
        """Test connection manager initialization."""
        self.assertEqual(self.manager.config, self.config)
        self.assertIsNone(self.manager.client)
        self.assertFalse(self.manager.is_connected)

    def test_connection_manager_default_config(self):
        """Test connection manager with default config."""
        manager = RedisConnectionManager()

        self.assertIsNotNone(manager.config)
        self.assertFalse(manager.is_connected)

    @patch("redis.from_url")
    def test_connect_success(self, mock_redis_from_url):
        """Test successful Redis connection."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_redis_from_url.return_value = mock_connection

        result = self.manager._connect()

        self.assertTrue(result)
        self.assertTrue(self.manager.is_connected)
        mock_redis_from_url.assert_called_once_with(
            self.config.url,
            decode_responses=self.config.decode_responses,
            socket_connect_timeout=self.config.socket_connect_timeout,
            socket_timeout=self.config.socket_timeout,
            retry_on_timeout=self.config.retry_on_timeout,
        )

    @patch("redis.from_url")
    def test_connect_failure(self, mock_redis_from_url):
        """Test Redis connection failure."""
        mock_redis_from_url.side_effect = redis.ConnectionError("Connection failed")

        result = self.manager._connect()

        self.assertFalse(result)
        self.assertFalse(self.manager.is_connected)

    @patch("redis.from_url")
    def test_connect_ping_failure(self, mock_redis_from_url):
        """Test Redis connection with ping failure."""
        mock_connection = Mock()
        mock_connection.ping.side_effect = redis.ConnectionError("Ping failed")
        mock_redis_from_url.return_value = mock_connection

        result = self.manager._connect()

        self.assertFalse(result)
        self.assertFalse(self.manager.is_connected)

    @patch("redis.from_url")
    def test_ensure_connection_success(self, mock_redis_from_url):
        """Test ensure connection success."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_redis_from_url.return_value = mock_connection

        result = self.manager.ensure_connection()

        self.assertTrue(result)
        self.assertTrue(self.manager.is_connected)

    def test_close_connection(self):
        """Test closing Redis connection."""
        # Set up connected state
        mock_connection = Mock()
        self.manager.client = mock_connection
        self.manager.is_connected = True

        self.manager.close()

        mock_connection.close.assert_called_once()
        self.assertIsNone(self.manager.client)
        self.assertFalse(self.manager.is_connected)

    def test_close_no_connection(self):
        """Test closing when not connected."""
        self.manager.close()

        self.assertIsNone(self.manager.client)
        self.assertFalse(self.manager.is_connected)

    def test_close_with_exception(self):
        """Test closing with exception."""
        mock_connection = Mock()
        mock_connection.close.side_effect = Exception("Close failed")
        self.manager.client = mock_connection
        self.manager.is_connected = True

        # Should not raise exception
        self.manager.close()

        self.assertIsNone(self.manager.client)
        self.assertFalse(self.manager.is_connected)

    @patch("redis.from_url")
    def test_publish_message_success(self, mock_redis_from_url):
        """Test successful message publishing."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_connection.publish.return_value = 1
        mock_redis_from_url.return_value = mock_connection

        # Connect first
        self.manager._connect()

        # Publish message
        result = self.manager.publish("test_channel", "test_message")

        self.assertEqual(result, 1)
        mock_connection.publish.assert_called_once_with("test_channel", "test_message")

    def test_publish_when_not_connected(self):
        """Test publishing when not connected."""
        result = self.manager.publish("test_channel", "test_message")

        self.assertEqual(result, -1)

    @patch("redis.from_url")
    def test_health_check_success(self, mock_redis_from_url):
        """Test successful health check."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_redis_from_url.return_value = mock_connection

        self.manager._connect()
        result = self.manager._health_check()

        self.assertTrue(result)

    def test_health_check_not_connected(self):
        """Test health check when not connected."""
        result = self.manager._health_check()

        self.assertFalse(result)

    @patch("redis.from_url")
    def test_health_check_ping_failure(self, mock_redis_from_url):
        """Test health check with ping failure."""
        mock_connection = Mock()
        mock_connection.ping.side_effect = redis.ConnectionError("Ping failed")
        mock_redis_from_url.return_value = mock_connection

        self.manager._connect()
        result = self.manager._health_check()

        self.assertFalse(result)

    def test_get_status_not_connected(self):
        """Test getting status when not connected."""
        status = self.manager.get_status()

        self.assertIsInstance(status, dict)
        self.assertFalse(status["connected"])
        self.assertFalse(status["healthy"])

    @patch("redis.from_url")
    def test_get_status_connected(self, mock_redis_from_url):
        """Test getting status when connected."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_redis_from_url.return_value = mock_connection

        self.manager._connect()
        status = self.manager.get_status()

        self.assertTrue(status["connected"])
        self.assertTrue(status["healthy"])

    def test_create_redis_connection_function(self):
        """Test create_redis_connection helper function."""
        redis_url = "redis://test:6379"

        connection = create_redis_connection(redis_url)

        self.assertIsInstance(connection, RedisConnectionManager)

    @patch("redis.from_url")
    def test_test_redis_connection_success(self, mock_redis_from_url):
        """Test test_redis_connection helper function success."""
        mock_connection = Mock()
        mock_connection.ping.return_value = True
        mock_redis_from_url.return_value = mock_connection

        result = test_redis_connection("redis://test:6379")

        self.assertTrue(result)

    @patch("redis.from_url")
    def test_test_redis_connection_failure(self, mock_redis_from_url):
        """Test test_redis_connection helper function failure."""
        mock_redis_from_url.side_effect = redis.ConnectionError("Connection failed")

        result = test_redis_connection("redis://test:6379")

        self.assertFalse(result)

    def test_redis_connection_config_creation(self):
        """Test RedisConnectionConfig creation."""
        config = RedisConnectionConfig(url="redis://test:6380", socket_timeout=10, max_retries=5)

        self.assertEqual(config.url, "redis://test:6380")
        self.assertEqual(config.socket_timeout, 10)
        self.assertEqual(config.max_retries, 5)

    def test_context_manager_success(self):
        """Test connection manager as context manager."""
        with patch("redis.from_url") as mock_redis_from_url:
            mock_connection = Mock()
            mock_connection.ping.return_value = True
            mock_redis_from_url.return_value = mock_connection

            with self.manager as manager:
                self.assertTrue(manager.is_connected)

            # Should be disconnected after context
            self.assertFalse(self.manager.is_connected)

    def test_context_manager_connection_failure(self):
        """Test context manager with connection failure."""
        with patch("redis.from_url") as mock_redis_from_url:
            mock_redis_from_url.side_effect = redis.ConnectionError("Connection failed")

            with self.manager as manager:
                # Should handle connection failure gracefully
                self.assertFalse(manager.is_connected)

    def test_connection_config_defaults(self):
        """Test RedisConnectionConfig default values."""
        config = RedisConnectionConfig()

        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertEqual(config.socket_connect_timeout, 5)
        self.assertEqual(config.socket_timeout, 5)
        self.assertEqual(config.max_retries, 3)
        self.assertTrue(config.decode_responses)
        self.assertTrue(config.retry_on_timeout)

    def test_connection_config_custom_values(self):
        """Test RedisConnectionConfig with custom values."""
        config = RedisConnectionConfig(
            url="redis://custom:6380",
            socket_timeout=10,
            max_retries=5,
            decode_responses=False,
        )

        self.assertEqual(config.url, "redis://custom:6380")
        self.assertEqual(config.socket_timeout, 10)
        self.assertEqual(config.max_retries, 5)
        self.assertFalse(config.decode_responses)


if __name__ == "__main__":
    unittest.main()
