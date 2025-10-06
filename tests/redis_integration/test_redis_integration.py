#!/usr/bin/env python3
"""
Tests for Redis Integration

Comprehensive test suite for Redis pub/sub integration functionality.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src to path for imports (must be before local imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

# Local imports after path modification
from redis_integration import (  # noqa: E402
    EnhancedMatchProcessingIntegration,
    EnhancedSchemaV2Formatter,
    MatchProcessorRedisPublisher,
    MatchProcessorRedisService,
    MatchUpdateMessageFormatter,
    ProcessingStatusMessageFormatter,
    RedisConfig,
    RedisConnectionManager,
    add_redis_integration_to_processor,
)


class TestRedisConfig(unittest.TestCase):
    """Test Redis configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RedisConfig()
        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertTrue(config.enabled)
        self.assertEqual(config.match_updates_channel, "fogis:matches:updates")

    def test_from_environment(self):
        """Test configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "REDIS_URL": "redis://test:6379",
                "REDIS_PUBSUB_ENABLED": "false",
                "REDIS_MATCH_UPDATES_CHANNEL": "test:matches",
            },
        ):
            config = RedisConfig.from_environment()
            self.assertEqual(config.url, "redis://test:6379")
            self.assertFalse(config.enabled)
            self.assertEqual(config.match_updates_channel, "test:matches")

    def test_get_channels(self):
        """Test channel configuration retrieval."""
        config = RedisConfig()
        channels = config.get_channels()
        self.assertIn("match_updates", channels)
        self.assertIn("processor_status", channels)
        self.assertIn("system_alerts", channels)


class TestRedisPublisher(unittest.TestCase):
    """Test Redis publisher functionality."""

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_match_updates_success(self, mock_connection_manager):
        """Test successful match updates publishing."""
        # Mock Redis client
        mock_client = Mock()
        mock_client.publish.return_value = 2

        mock_manager = Mock()
        mock_manager.get_client.return_value = mock_client
        mock_manager.config.enabled = True
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        matches = [{"id": 1, "team1": "A", "team2": "B"}]
        changes = {"summary": {"new_matches": 1}}

        result = publisher.publish_match_updates(matches, changes)

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 2)
        mock_client.publish.assert_called_once()

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_disabled(self, mock_connection_manager):
        """Test publishing when Redis is disabled."""
        mock_manager = Mock()
        mock_manager.config.enabled = False
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        result = publisher.publish_match_updates([], {})

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 0)

    @patch("redis_integration.publisher.RedisConnectionManager")
    def test_publish_connection_failed(self, mock_connection_manager):
        """Test publishing when Redis connection fails."""
        mock_manager = Mock()
        mock_manager.get_client.return_value = None
        mock_manager.config.enabled = True
        mock_connection_manager.return_value = mock_manager

        publisher = MatchProcessorRedisPublisher()
        result = publisher.publish_match_updates([], {})

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)


class TestRedisService(unittest.TestCase):
    """Test Redis service functionality."""

    @patch("redis_integration.services.MatchProcessorRedisPublisher")
    def test_handle_processing_complete(self, mock_publisher_class):
        """Test handling processing completion."""
        mock_publisher = Mock()
        mock_publisher.publish_match_updates.return_value = Mock(success=True)
        mock_publisher.publish_processing_status.return_value = Mock(success=True)
        mock_publisher_class.return_value = mock_publisher

        service = MatchProcessorRedisService()
        matches = [{"id": 1}]
        changes = {"summary": {}}

        result = service.handle_match_processing_complete(matches, changes)

        self.assertTrue(result)
        mock_publisher.publish_match_updates.assert_called_once()
        mock_publisher.publish_processing_status.assert_called_once()

    @patch("redis_integration.services.MatchProcessorRedisPublisher")
    def test_handle_processing_error(self, mock_publisher_class):
        """Test handling processing errors."""
        mock_publisher = Mock()
        mock_publisher.publish_processing_status.return_value = Mock(success=True)
        mock_publisher.publish_system_alert.return_value = Mock(success=True)
        mock_publisher_class.return_value = mock_publisher

        service = MatchProcessorRedisService()
        error = Exception("Test error")

        result = service.handle_processing_error(error)

        self.assertTrue(result)
        mock_publisher.publish_processing_status.assert_called_once()
        mock_publisher.publish_system_alert.assert_called_once()


class TestAppIntegration(unittest.TestCase):
    """Test application integration functionality."""

    def test_add_redis_integration(self):
        """Test adding Redis integration to processor."""
        # Create mock processor
        processor = Mock()
        processor._process_matches_sync = Mock(return_value=None)

        add_redis_integration_to_processor(processor)

        # Check that Redis integration was added
        self.assertTrue(hasattr(processor, "redis_integration"))
        self.assertTrue(hasattr(processor, "_original_process_matches_sync"))

    def test_integration_without_process_method(self):
        """Test integration with processor without _process_matches_sync method."""
        processor = Mock()
        del processor._process_matches_sync  # Remove the method

        add_redis_integration_to_processor(processor)

        # Should still add redis_integration but warn about missing method
        self.assertTrue(hasattr(processor, "redis_integration"))

    def test_enhanced_processing_with_result(self):
        """Test enhanced processing method with result object."""
        from redis_integration.app_integration import create_redis_service

        # Test create_redis_service function
        service = create_redis_service()
        self.assertIsNotNone(service)

        # Create mock processor with result object
        processor = Mock()
        result_mock = Mock()
        result_mock.matches = [{"id": 1, "team1": "A", "team2": "B"}]
        result_mock.changes = {"summary": {"new_matches": 1}}
        processor._process_matches_sync = Mock(return_value=result_mock)

        add_redis_integration_to_processor(processor)

        # Test enhanced processing
        enhanced_result = processor._process_matches_sync()
        self.assertEqual(enhanced_result, result_mock)

    def test_enhanced_processing_with_exception(self):
        """Test enhanced processing method with exception handling."""
        processor = Mock()
        processor._process_matches_sync = Mock(side_effect=Exception("Test error"))

        add_redis_integration_to_processor(processor)

        # Test that exception is re-raised after Redis handling
        with self.assertRaises(Exception):
            processor._process_matches_sync()

    def test_add_redis_integration_to_unified_processor(self):
        """Test adding Redis integration to UnifiedMatchProcessor."""
        # Create mock UnifiedMatchProcessor
        processor = Mock()
        processor.run_processing_cycle = Mock()

        # Mock ProcessingResult
        result_mock = Mock()
        result_mock.processed = True
        result_mock.changes = Mock()
        processor.run_processing_cycle.return_value = result_mock

        # Mock change_detector
        change_detector_mock = Mock()
        change_detector_mock.load_current_matches.return_value = [
            {"matchid": 1, "lag1namn": "Team A", "lag2namn": "Team B"}
        ]
        processor.change_detector = change_detector_mock

        add_redis_integration_to_processor(processor)

        # Check that Redis integration was added
        self.assertTrue(hasattr(processor, "redis_integration"))
        self.assertTrue(hasattr(processor, "_original_run_processing_cycle"))

        # Test enhanced processing
        enhanced_result = processor.run_processing_cycle()
        self.assertEqual(enhanced_result, result_mock)

        # Verify change_detector.load_current_matches was called
        change_detector_mock.load_current_matches.assert_called_once()

    def test_unified_processor_integration_no_changes(self):
        """Test UnifiedMatchProcessor integration when no changes are processed."""
        processor = Mock()
        processor.run_processing_cycle = Mock()

        # Mock ProcessingResult with no changes
        result_mock = Mock()
        result_mock.processed = False
        processor.run_processing_cycle.return_value = result_mock

        processor.change_detector = Mock()

        add_redis_integration_to_processor(processor)

        # Test enhanced processing
        enhanced_result = processor.run_processing_cycle()
        self.assertEqual(enhanced_result, result_mock)

        # Verify load_current_matches was NOT called when no changes
        processor.change_detector.load_current_matches.assert_not_called()

    def test_unified_processor_integration_with_exception(self):
        """Test UnifiedMatchProcessor integration with exception handling."""
        processor = Mock()
        processor.run_processing_cycle = Mock(side_effect=Exception("Test error"))
        processor.change_detector = Mock()

        add_redis_integration_to_processor(processor)

        # Test that exception is re-raised after Redis handling
        with self.assertRaises(Exception):
            processor.run_processing_cycle()

    def test_unified_processor_without_change_detector(self):
        """Test UnifiedMatchProcessor integration without change_detector."""
        processor = Mock()
        processor.run_processing_cycle = Mock()

        # Mock ProcessingResult
        result_mock = Mock()
        result_mock.processed = True
        result_mock.changes = Mock()
        processor.run_processing_cycle.return_value = result_mock

        # No change_detector attribute
        del processor.change_detector

        add_redis_integration_to_processor(processor)

        # Test enhanced processing - should not fail
        enhanced_result = processor.run_processing_cycle()
        self.assertEqual(enhanced_result, result_mock)


class TestRedisConnectionManager(unittest.TestCase):
    """Test Redis connection manager functionality."""

    @patch("redis_integration.connection_manager.redis")
    def test_connection_manager_initialization(self, mock_redis):
        """Test connection manager initialization."""
        manager = RedisConnectionManager()
        self.assertIsNotNone(manager.config)

    @patch("redis_integration.connection_manager.redis")
    def test_get_client_success(self, mock_redis):
        """Test successful client connection."""
        mock_client = Mock()
        mock_redis.from_url.return_value = mock_client

        manager = RedisConnectionManager()
        client = manager.get_client()

        self.assertEqual(client, mock_client)
        mock_client.ping.assert_called_once()

    @patch("redis_integration.connection_manager.redis")
    def test_get_client_failure(self, mock_redis):
        """Test client connection failure."""
        mock_redis.from_url.side_effect = Exception("Connection failed")

        manager = RedisConnectionManager()
        client = manager.get_client()

        self.assertIsNone(client)

    @patch("redis_integration.connection_manager.redis")
    def test_is_connected_true(self, mock_redis):
        """Test is_connected returns True when connected."""
        mock_client = Mock()
        mock_redis.from_url.return_value = mock_client

        manager = RedisConnectionManager()
        manager.config.enabled = True  # Ensure enabled
        manager.get_client()  # Initialize connection

        self.assertTrue(manager.is_connected())

    @patch("redis_integration.connection_manager.redis")
    def test_is_connected_false(self, mock_redis):
        """Test is_connected returns False when not connected."""
        manager = RedisConnectionManager()
        manager.config.enabled = False

        self.assertFalse(manager.is_connected())

    @patch("redis_integration.connection_manager.redis")
    def test_close_connection(self, mock_redis):
        """Test closing connection."""
        mock_client = Mock()
        mock_redis.from_url.return_value = mock_client

        manager = RedisConnectionManager()
        manager.get_client()  # Initialize connection
        manager.close()

        mock_client.close.assert_called_once()


class TestMessageFormatters(unittest.TestCase):
    """Test message formatting functionality."""

    def test_match_update_message_format(self):
        """Test match update message formatting."""
        matches = [{"id": 1, "team1": "A", "team2": "B"}]
        changes = {"summary": {"new_matches": 1}}
        metadata = {"source": "test"}

        message = MatchUpdateMessageFormatter.format_match_updates(matches, changes, metadata)

        self.assertIsInstance(message, str)
        # Verify it's valid JSON
        import json

        parsed = json.loads(message)
        self.assertEqual(parsed["type"], "match_updates")
        self.assertEqual(parsed["source"], "match-list-processor")
        self.assertEqual(len(parsed["payload"]["matches"]), 1)

    def test_processing_status_message_format(self):
        """Test processing status message formatting."""
        status = "completed"
        details = {"matches_processed": 5}

        message = ProcessingStatusMessageFormatter.format_processing_status(status, details)

        self.assertIsInstance(message, str)
        # Verify it's valid JSON
        import json

        parsed = json.loads(message)
        self.assertEqual(parsed["type"], "processing_status")
        self.assertEqual(parsed["payload"]["status"], "completed")

    def test_system_alert_message_format(self):
        """Test system alert message formatting."""
        alert_type = "error"
        message_text = "Test alert"
        severity = "high"
        details = {"error_code": 500}

        message = ProcessingStatusMessageFormatter.format_system_alert(
            alert_type, message_text, severity, details
        )

        self.assertIsInstance(message, str)
        # Verify it's valid JSON
        import json

        parsed = json.loads(message)
        self.assertEqual(parsed["type"], "system_alert")
        self.assertEqual(parsed["payload"]["alert_type"], "error")
        self.assertEqual(parsed["payload"]["severity"], "high")


class TestEnhancedSchemaV2Formatter(unittest.TestCase):
    """Test Enhanced Schema v2.0 formatter with Organization ID mapping."""

    def setUp(self):
        """Set up test data."""
        self.sample_match = {
            "matchid": 6170049,
            "lag1namn": "Lindome GIF",
            "lag2namn": "Jonsereds IF",
            "lag1lagid": 26405,  # Database ID
            "lag2lagid": 25562,  # Database ID
            "lag1foreningid": 10741,  # Organization ID for logo service
            "lag2foreningid": 9595,  # Organization ID for logo service
            "speldatum": "2025-09-26",
            "avsparkstid": "19:00",
            "anlaggningnamn": "Lindome IP",
            "anlaggningadress": "Lindome Industriområde",
            "serienamn": "Division 4 Göteborg A",
            "serieniva": "Division 4",
            "matchstatus": "scheduled",
            "domaruppdraglista": [
                {
                    "namn": "Bartek Svaberg",
                    "uppdragstyp": "Huvuddomare",
                    "mobil": "0709423055",
                    "epost": "bartek.svaberg@gmail.com",
                    "adress": "Lilla Tulteredsvägen 50",
                    "postnummer": "43331",
                    "postort": "Partille",
                }
            ],
            "lag1kontakt": {
                "namn": "Morgan Johansson",
                "mobil": "0733472740",
                "epost": "morgan@kalltorpsbygg.se",
            },
            "lag2kontakt": {
                "namn": "Erik Andersson",
                "mobil": "0701234567",
                "epost": "erik@jonsereds.se",
            },
        }

        self.sample_changes = {
            "summary": {"total_changes": 1, "change_types": ["time_change"]},
            "detailed_changes": [
                {
                    "field": "avsparkstid",
                    "from": "19:00",
                    "to": "19:15",
                    "category": "time_change",
                    "priority": "high",
                }
            ],
        }

    def test_organization_id_mapping(self):
        """Test that Organization IDs are correctly mapped for logo service."""
        message_json = EnhancedSchemaV2Formatter.format_match_updates_v2(
            [self.sample_match], self.sample_changes
        )

        import json

        message = json.loads(message_json)

        # Verify schema version
        self.assertEqual(message["schema_version"], "2.0")
        self.assertEqual(message["schema_type"], "enhanced_with_contacts_and_logo_ids")

        # Verify Organization ID mapping
        home_team = message["payload"]["matches"][0]["teams"]["home"]
        away_team = message["payload"]["matches"][0]["teams"]["away"]

        # Database IDs should be preserved for database references
        self.assertEqual(home_team["id"], 26405)
        self.assertEqual(away_team["id"], 25562)

        # Organization IDs should be used for logo service
        self.assertEqual(home_team["logo_id"], 10741)
        self.assertEqual(away_team["logo_id"], 9595)
        self.assertEqual(home_team["organization_id"], 10741)
        self.assertEqual(away_team["organization_id"], 9595)

    def test_contact_data_structure(self):
        """Test complete contact data structure for calendar sync."""
        message_json = EnhancedSchemaV2Formatter.format_match_updates_v2(
            [self.sample_match], self.sample_changes
        )

        import json

        message = json.loads(message_json)

        match_data = message["payload"]["matches"][0]

        # Verify referee contact information
        referee = match_data["referees"][0]
        self.assertEqual(referee["name"], "Bartek Svaberg")
        self.assertEqual(referee["role"], "Huvuddomare")
        self.assertIn("contact", referee)
        self.assertEqual(referee["contact"]["mobile"], "0709423055")
        self.assertEqual(referee["contact"]["email"], "bartek.svaberg@gmail.com")

        # Verify referee address information
        address = referee["contact"]["address"]
        self.assertEqual(address["street"], "Lilla Tulteredsvägen 50")
        self.assertEqual(address["postal_code"], "43331")
        self.assertEqual(address["city"], "Partille")

        # Verify team contact information
        team_contacts = match_data["team_contacts"]
        self.assertEqual(len(team_contacts), 2)

        home_contact = team_contacts[0]
        self.assertEqual(home_contact["name"], "Morgan Johansson")
        self.assertEqual(home_contact["team_name"], "Lindome GIF")
        self.assertEqual(home_contact["contact"]["mobile"], "0733472740")

    def test_detailed_changes_structure(self):
        """Test detailed changes structure for intelligent processing."""
        message_json = EnhancedSchemaV2Formatter.format_match_updates_v2(
            [self.sample_match], self.sample_changes
        )

        import json

        message = json.loads(message_json)

        detailed_changes = message["payload"]["detailed_changes"]
        self.assertEqual(len(detailed_changes), 1)

        change = detailed_changes[0]
        self.assertEqual(change["field"], "avsparkstid")
        self.assertEqual(change["from"], "19:00")
        self.assertEqual(change["to"], "19:15")
        self.assertEqual(change["category"], "time_change")
        self.assertEqual(change["priority"], "high")

    def test_legacy_v1_compatibility(self):
        """Test Legacy Schema v1.0 for backward compatibility."""
        message_json = EnhancedSchemaV2Formatter.format_match_updates_v1_legacy(
            [self.sample_match], self.sample_changes
        )

        import json

        message = json.loads(message_json)

        # Verify simplified structure
        self.assertEqual(message["version"], "1.0")
        self.assertEqual(message["type"], "match_updates")

        match_data = message["payload"]["matches"][0]
        self.assertEqual(match_data["match_id"], 6170049)
        self.assertEqual(match_data["teams"], "Lindome GIF vs Jonsereds IF")
        self.assertEqual(match_data["date"], "2025-09-26")
        self.assertEqual(match_data["time"], "19:00")
        self.assertEqual(match_data["venue"], "Lindome IP")
        self.assertEqual(match_data["referees"], ["Bartek Svaberg"])

    def test_message_size_validation(self):
        """Test that Enhanced Schema v2.0 messages are under size limits."""
        message_json = EnhancedSchemaV2Formatter.format_match_updates_v2(
            [self.sample_match], self.sample_changes
        )

        # Test message size (should be under 5KB for Redis efficiency)
        message_size = len(message_json.encode("utf-8"))
        self.assertLess(message_size, 5000, f"Message size {message_size} bytes exceeds 5KB limit")

        # Test legacy message size
        legacy_json = EnhancedSchemaV2Formatter.format_match_updates_v1_legacy(
            [self.sample_match], self.sample_changes
        )
        legacy_size = len(legacy_json.encode("utf-8"))
        self.assertLess(
            legacy_size, 1000, f"Legacy message size {legacy_size} bytes exceeds 1KB limit"
        )


class TestEnhancedMatchProcessingIntegration(unittest.TestCase):
    """Test Enhanced Match Processing Integration with Schema v2.0."""

    def setUp(self):
        """Set up test integration."""
        self.integration = EnhancedMatchProcessingIntegration(enabled=True)
        self.sample_matches = [
            {
                "matchid": 6170049,
                "lag1foreningid": 10741,
                "lag2foreningid": 9595,
                "lag1lagid": 26405,
                "lag2lagid": 25562,
            }
        ]

    @patch("redis_integration.publisher.MatchProcessorRedisPublisher.publish_multi_version_updates")
    def test_enhanced_publishing_success(self, mock_publish):
        """Test successful Enhanced Schema v2.0 publishing."""
        from redis_integration.publisher import PublishResult

        mock_publish.return_value = {
            "v2.0": PublishResult(success=True, subscribers_notified=3),
            "v1.0_legacy": PublishResult(success=True, subscribers_notified=2),
            "default": PublishResult(success=True, subscribers_notified=3),
        }

        # Should not raise any exceptions
        self.integration.handle_match_processing_complete_v2(
            self.sample_matches, {"summary": {"total_changes": 1}}
        )

        mock_publish.assert_called_once()

    def test_organization_id_validation(self):
        """Test Organization ID validation for logo service."""
        # Test with missing Organization IDs
        invalid_matches = [
            {
                "matchid": 123,
                "lag1foreningid": None,  # Missing
                "lag2foreningid": 456,
                "lag1lagid": 789,
                "lag2lagid": 101,
            }
        ]

        # Should log warnings but not fail
        with patch("redis_integration.app_integration.logger") as mock_logger:
            self.integration._validate_organization_ids(invalid_matches)
            mock_logger.warning.assert_called()

        # Test with valid Organization IDs
        with patch("redis_integration.app_integration.logger") as mock_logger:
            self.integration._validate_organization_ids(self.sample_matches)
            mock_logger.info.assert_called_with(
                "✅ All matches have Organization IDs for logo service integration"
            )


class TestRedisPublisherCoverage(unittest.TestCase):
    """Test Redis publisher methods for improved coverage."""

    def setUp(self):
        """Set up test publisher."""
        self.publisher = MatchProcessorRedisPublisher()
        # Store original config state
        self.original_enabled = self.publisher.config.enabled
        self.sample_matches = [
            {
                "matchid": 6170049,
                "lag1foreningid": 10741,
                "lag2foreningid": 9595,
                "lag1lagid": 26405,
                "lag2lagid": 25562,
            }
        ]

    def tearDown(self):
        """Clean up after each test."""
        # Restore original config state
        self.publisher.config.enabled = self.original_enabled

    def test_publish_enhanced_schema_v2_disabled(self):
        """Test Enhanced Schema v2.0 publishing when disabled."""
        self.publisher.config.enabled = False

        result = self.publisher.publish_enhanced_schema_v2(self.sample_matches)

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 0)

    @patch("redis_integration.connection_manager.redis.from_url")
    def test_publish_enhanced_schema_v2_no_client(self, mock_redis):
        """Test Enhanced Schema v2.0 publishing when Redis client unavailable."""
        mock_redis.side_effect = Exception("Connection failed")

        result = self.publisher.publish_enhanced_schema_v2(self.sample_matches)

        self.assertFalse(result.success)
        self.assertIn("Redis client not available", result.error)

    def test_publish_multi_version_updates_disabled(self):
        """Test multi-version publishing when disabled."""
        self.publisher.config.enabled = False

        results = self.publisher.publish_multi_version_updates(self.sample_matches)

        self.assertEqual(len(results), 3)
        for result in results.values():
            self.assertTrue(result.success)
            self.assertEqual(result.subscribers_notified, 0)

    @patch("redis_integration.connection_manager.redis.from_url")
    def test_publish_multi_version_updates_no_client(self, mock_redis):
        """Test multi-version publishing when Redis client unavailable."""
        mock_redis.side_effect = Exception("Connection failed")

        results = self.publisher.publish_multi_version_updates(self.sample_matches)

        self.assertEqual(len(results), 3)
        for result in results.values():
            self.assertFalse(result.success)
            self.assertIn("Redis client not available", result.error)


class TestRedisConnectionManagerCoverage(unittest.TestCase):
    """Test Redis connection manager for improved coverage."""

    def setUp(self):
        """Set up test connection manager."""
        self.connection_manager = RedisConnectionManager()

    def test_get_client_disabled(self):
        """Test get client when Redis is disabled."""
        self.connection_manager.config.enabled = False

        client = self.connection_manager.get_client()

        self.assertIsNone(client)

    @patch("redis_integration.connection_manager.redis.from_url")
    def test_get_client_exception(self, mock_redis):
        """Test Redis client creation with exception."""
        mock_redis.side_effect = Exception("Connection failed")

        client = self.connection_manager.get_client()

        self.assertIsNone(client)

    def test_close_connection_no_client(self):
        """Test closing connection when no client exists."""
        # Should not raise exception
        self.connection_manager.close()

    @patch("redis_integration.connection_manager.redis.from_url")
    def test_close_connection_exception(self, mock_redis):
        """Test closing connection with exception."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.close.side_effect = Exception("Close failed")
        mock_redis.return_value = mock_client

        # Create client first
        self.connection_manager.get_client()

        # Should not raise exception when closing fails
        self.connection_manager.close()


class TestRedisServicesCoverage(unittest.TestCase):
    """Test Redis services for improved coverage."""

    def setUp(self):
        """Set up test service."""
        self.service = MatchProcessorRedisService()

    def test_handle_processing_start_disabled(self):
        """Test handling processing start when Redis disabled."""
        self.service.publisher.config.enabled = False

        # Should not raise exception
        result = self.service.handle_processing_start({"test": "metadata"})

        self.assertTrue(result)

    def test_handle_processing_error_disabled(self):
        """Test handling processing error when Redis disabled."""
        self.service.publisher.config.enabled = False

        error = Exception("Test error")

        # Should not raise exception
        result = self.service.handle_processing_error(error, {"test": "metadata"})

        self.assertTrue(result)

    def test_handle_match_processing_complete_disabled(self):
        """Test handling match processing completion when Redis disabled."""
        self.service.publisher.config.enabled = False

        matches = [{"matchid": 123}]
        changes = {"summary": {"total_changes": 1}}

        # Should not raise exception
        result = self.service.handle_match_processing_complete(matches, changes)

        self.assertTrue(result)


class TestEnhancedAppIntegrationCoverage(unittest.TestCase):
    """Test Enhanced App Integration for improved coverage."""

    def setUp(self):
        """Set up test integration."""
        self.integration = EnhancedMatchProcessingIntegration(enabled=False)

    def test_handle_match_processing_complete_v2_disabled(self):
        """Test Enhanced Schema v2.0 processing when disabled."""
        matches = [{"matchid": 123}]
        changes = {"summary": {"total_changes": 1}}

        # Should not raise exception when disabled
        self.integration.handle_match_processing_complete_v2(matches, changes)

    def test_log_enhanced_message_details(self):
        """Test enhanced message details logging."""
        matches = [{"matchid": 123, "lag1foreningid": 456, "lag2foreningid": 789}]
        changes = {"detailed_changes": [{"field": "time", "from": "19:00", "to": "19:15"}]}

        # Should not raise exception
        self.integration._log_enhanced_message_details(matches, changes)

    def test_log_enhanced_message_details_no_changes(self):
        """Test enhanced message details logging with no changes."""
        matches = [{"matchid": 123}]

        # Should not raise exception
        self.integration._log_enhanced_message_details(matches, None)

    def test_log_publishing_results(self):
        """Test publishing results logging."""
        from redis_integration.publisher import PublishResult

        results = {
            "v2.0": PublishResult(success=True, subscribers_notified=3),
            "v1.0": PublishResult(success=False, error="Test error"),
        }

        # Should not raise exception
        self.integration._log_publishing_results(results)


class TestRedisConfigCoverage(unittest.TestCase):
    """Test Redis config for improved coverage."""

    def test_redis_config_defaults(self):
        """Test Redis config default values."""
        from redis_integration.config import RedisConfig

        config = RedisConfig()

        self.assertTrue(config.enabled)
        self.assertEqual(config.url, "redis://fogis-redis:6379")
        self.assertEqual(config.match_updates_channel, "fogis:matches:updates")

    def test_redis_config_from_env(self):
        """Test Redis config from environment variables."""
        import os

        from redis_integration.config import RedisConfig

        # Set environment variables
        os.environ["REDIS_PUBSUB_ENABLED"] = "false"
        os.environ["REDIS_URL"] = "redis://test:6379/1"
        os.environ["REDIS_MATCH_UPDATES_CHANNEL"] = "test:matches"

        config = RedisConfig.from_environment()

        self.assertFalse(config.enabled)
        self.assertEqual(config.url, "redis://test:6379/1")
        self.assertEqual(config.match_updates_channel, "test:matches")

        # Clean up
        del os.environ["REDIS_PUBSUB_ENABLED"]
        del os.environ["REDIS_URL"]
        del os.environ["REDIS_MATCH_UPDATES_CHANNEL"]

    def test_redis_config_get_channels(self):
        """Test Redis config get channels method."""
        from redis_integration.config import RedisConfig

        config = RedisConfig()
        channels = config.get_channels()

        self.assertIn("match_updates", channels)
        self.assertIn("processor_status", channels)
        self.assertIn("system_alerts", channels)

    def test_global_config_functions(self):
        """Test global config functions."""
        from redis_integration.config import get_redis_config, reload_redis_config

        config1 = get_redis_config()
        config2 = get_redis_config()

        # Should return same instance
        self.assertIs(config1, config2)

        # Test reload
        reload_redis_config()
        config3 = get_redis_config()

        # Should be different instance after reload
        self.assertIsNot(config1, config3)


class TestMessageFormatterEdgeCases(unittest.TestCase):
    """Test message formatter edge cases for improved coverage."""

    def test_format_match_updates_empty_matches(self):
        """Test formatting with empty matches list."""
        import json

        from redis_integration.message_formatter import MatchUpdateMessageFormatter

        message_str = MatchUpdateMessageFormatter.format_match_updates([], {})
        message = json.loads(message_str)

        self.assertIn("payload", message)
        self.assertIn("matches", message["payload"])
        self.assertEqual(len(message["payload"]["matches"]), 0)

    def test_format_match_updates_with_changes(self):
        """Test formatting with changes summary."""
        import json

        from redis_integration.message_formatter import MatchUpdateMessageFormatter

        matches = [{"matchid": 123}]
        changes = {"summary": {"total_changes": 1}}
        message_str = MatchUpdateMessageFormatter.format_match_updates(matches, changes)
        message = json.loads(message_str)

        self.assertIn("payload", message)
        self.assertIn("matches", message["payload"])
        self.assertIn("metadata", message["payload"])

    def test_format_processing_status_edge_cases(self):
        """Test processing status formatting edge cases."""
        import json

        from redis_integration.message_formatter import ProcessingStatusMessageFormatter

        # Test with minimal metadata
        message_str = ProcessingStatusMessageFormatter.format_processing_status("started", {})
        message = json.loads(message_str)

        self.assertEqual(message["payload"]["status"], "started")
        self.assertIn("timestamp", message)

    def test_format_system_alert_edge_cases(self):
        """Test system alert formatting edge cases."""
        import json

        from redis_integration.message_formatter import ProcessingStatusMessageFormatter

        # Test with minimal alert
        message_str = ProcessingStatusMessageFormatter.format_system_alert(
            "error", "Test error", "critical"
        )
        message = json.loads(message_str)

        self.assertEqual(message["payload"]["alert_type"], "error")
        self.assertEqual(message["payload"]["message"], "Test error")
        self.assertEqual(message["payload"]["severity"], "critical")


class TestPublishResultCoverage(unittest.TestCase):
    """Test PublishResult class for improved coverage."""

    def test_publish_result_success(self):
        """Test successful PublishResult."""
        from redis_integration.publisher import PublishResult

        result = PublishResult(success=True, subscribers_notified=5)

        self.assertTrue(result.success)
        self.assertEqual(result.subscribers_notified, 5)
        self.assertIsNone(result.error)

    def test_publish_result_failure(self):
        """Test failed PublishResult."""
        from redis_integration.publisher import PublishResult

        result = PublishResult(success=False, error="Test error")

        self.assertFalse(result.success)
        self.assertEqual(result.subscribers_notified, 0)
        self.assertEqual(result.error, "Test error")

    def test_publish_result_repr(self):
        """Test PublishResult string representation."""
        from redis_integration.publisher import PublishResult

        result = PublishResult(success=True, subscribers_notified=3)
        repr_str = repr(result)

        self.assertIn("PublishResult", repr_str)
        self.assertIn("success=True", repr_str)
        self.assertIn("subscribers_notified=3", repr_str)


if __name__ == "__main__":
    unittest.main()
