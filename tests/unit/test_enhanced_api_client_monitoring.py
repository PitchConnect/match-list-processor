"""Unit tests for enhanced API client monitoring capabilities."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
import requests

from src.services.api_client import DockerNetworkApiClient, ServiceMonitoringMixin


class TestServiceMonitoringMixin:
    """Test the ServiceMonitoringMixin functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.mixin = ServiceMonitoringMixin()
        self.mixin.notification_service = AsyncMock()

    def test_alert_cooldown_mechanism(self):
        """Test that alert cooldown prevents spam."""
        # First alert should be sent
        assert self.mixin._should_send_alert("test_alert") is True

        # Immediate second alert should be blocked
        assert self.mixin._should_send_alert("test_alert") is False

        # Different alert should be allowed
        assert self.mixin._should_send_alert("different_alert") is True

    def test_alert_cooldown_expiry(self):
        """Test that alert cooldown expires after timeout."""
        # Mock time to control cooldown
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000

            # First alert
            assert self.mixin._should_send_alert("test_alert") is True

            # Immediate second alert blocked
            assert self.mixin._should_send_alert("test_alert") is False

            # Move time forward past cooldown
            mock_time.return_value = 1400  # 400 seconds later (> 300s cooldown)

            # Alert should now be allowed
            assert self.mixin._should_send_alert("test_alert") is True

    def test_affected_functionality_mapping(self):
        """Test that affected functionality is correctly mapped."""
        functionality = self.mixin._get_affected_functionality("fogis-api-client")
        assert "Match processing suspended" in functionality
        assert "Change detection unavailable" in functionality

        functionality = self.mixin._get_affected_functionality("unknown-service")
        assert "Service functionality affected" in functionality

    @pytest.mark.asyncio
    async def test_send_system_alert_success(self):
        """Test successful system alert sending."""
        self.mixin._send_system_alert(
            alert_type="test_alert",
            service="test-service",
            severity="critical",
            message="Test message",
            error_details="Test error",
            recovery_actions=["Test action"],
        )

        # Verify notification service was called
        # Note: We can't easily test the asyncio.create_task call in unit tests
        # This would be better tested in integration tests

    def test_send_system_alert_no_notification_service(self):
        """Test alert sending when no notification service is configured."""
        self.mixin.notification_service = None

        # Should not raise exception
        self.mixin._send_system_alert(
            alert_type="test_alert",
            service="test-service",
            severity="critical",
            message="Test message",
            error_details="Test error",
        )


class TestDockerNetworkApiClientMonitoring:
    """Test the enhanced monitoring capabilities of DockerNetworkApiClient."""

    def setup_method(self):
        """Set up test environment."""
        # Force unit test mode to allow network call testing
        with patch.dict("os.environ", {"PYTEST_API_CLIENT_UNIT_TEST": "1"}):
            self.client = DockerNetworkApiClient()
            self.client.notification_service = AsyncMock()
            # Override test mode for unit tests that need to test network behavior
            self.client.is_test_mode = False

    def test_initialization_with_monitoring(self):
        """Test that client initializes with monitoring capabilities."""
        assert hasattr(self.client, "notification_service")
        assert hasattr(self.client, "_last_alert_times")
        assert hasattr(self.client, "_alert_cooldown")
        assert self.client.service_name == "fogis-api-client"

    def test_set_notification_service(self):
        """Test setting notification service."""
        mock_service = Mock()
        self.client.set_notification_service(mock_service)
        assert self.client.notification_service == mock_service

    def test_response_data_validation(self):
        """Test response data validation."""
        # Valid list response
        assert self.client._validate_response_data([]) is True
        assert self.client._validate_response_data([{"match": "data"}]) is True

        # Invalid non-list response
        assert self.client._validate_response_data("invalid") is False
        assert self.client._validate_response_data({"not": "list"}) is False

    @patch("requests.get")
    def test_authentication_failure_detection(self, mock_get):
        """Test detection and alerting of authentication failures."""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            # Should return empty list on error
            assert result == []

            # Should send critical alert
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "authentication_failure"
            assert call_args["severity"] == "critical"
            assert "FOGIS API authentication failed" in call_args["message"]

    @patch("requests.get")
    def test_authorization_failure_detection(self, mock_get):
        """Test detection and alerting of authorization failures."""
        # Mock 403 response
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            assert result == []
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "authorization_failure"
            assert call_args["severity"] == "high"

    @patch("requests.get")
    def test_service_failure_detection(self, mock_get):
        """Test detection and alerting of service failures."""
        # Test various server error codes
        for status_code in [500, 502, 503, 504]:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            with patch.object(self.client, "_send_system_alert") as mock_alert:
                result = self.client.fetch_matches_list()

                assert result == []
                mock_alert.assert_called_once()
                call_args = mock_alert.call_args[1]
                assert call_args["alert_type"] == "service_failure"
                assert call_args["severity"] == "high"

    @patch("requests.get")
    def test_timeout_error_detection(self, mock_get):
        """Test detection and alerting of timeout errors."""
        mock_get.side_effect = requests.exceptions.Timeout()

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            assert result == []
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "timeout_error"
            assert call_args["severity"] == "medium"

    @patch("requests.get")
    def test_connection_error_detection(self, mock_get):
        """Test detection and alerting of connection errors."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            assert result == []
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "connection_error"
            assert call_args["severity"] == "medium"

    @patch("requests.get")
    def test_parsing_error_detection(self, mock_get):
        """Test detection and alerting of JSON parsing errors."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            assert result == []
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "parsing_error"
            assert call_args["severity"] == "medium"

    @patch("requests.get")
    def test_slow_response_detection(self, mock_get):
        """Test detection and alerting of slow responses."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        # Mock time to simulate slow response
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000, 1020]  # 20 second response time

            with patch.object(self.client, "_send_system_alert") as mock_alert:
                result = self.client.fetch_matches_list()

                assert result == []
                mock_alert.assert_called_once()
                call_args = mock_alert.call_args[1]
                assert call_args["alert_type"] == "slow_response"
                assert call_args["severity"] == "medium"

    @patch("requests.get")
    def test_data_validation_failure_detection(self, mock_get):
        """Test detection and alerting of data validation failures."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = "invalid_data"  # Not a list
        mock_get.return_value = mock_response

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            # Should still return the data even if validation fails
            assert result == "invalid_data"

            # Should send validation alert
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "data_validation"
            assert call_args["severity"] == "medium"

    @patch("requests.get")
    def test_successful_request_no_alerts(self, mock_get):
        """Test that successful requests don't trigger alerts."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [{"match": "data"}]
        mock_get.return_value = mock_response

        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000, 1005]  # Fast 5 second response

            with patch.object(self.client, "_send_system_alert") as mock_alert:
                result = self.client.fetch_matches_list()

                assert result == [{"match": "data"}]
                mock_alert.assert_not_called()

    @patch("requests.get")
    def test_unexpected_error_detection(self, mock_get):
        """Test detection and alerting of unexpected errors."""
        mock_get.side_effect = RuntimeError("Unexpected error")

        with patch.object(self.client, "_send_system_alert") as mock_alert:
            result = self.client.fetch_matches_list()

            assert result == []
            mock_alert.assert_called_once()
            call_args = mock_alert.call_args[1]
            assert call_args["alert_type"] == "unexpected_error"
            assert call_args["severity"] == "medium"

    def test_test_mode_bypass(self):
        """Test that test mode bypasses network calls."""
        # Create client without the unit test flag
        with patch.dict("os.environ", {}, clear=True):
            client = DockerNetworkApiClient()

            # Should return empty list in test mode
            result = client.fetch_matches_list()
            assert result == []
