"""Integration tests for monitoring and notification flow."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.unified_processor import UnifiedMatchProcessor
from src.notifications.notification_service import NotificationService
from src.services.api_client import DockerNetworkApiClient


class TestMonitoringNotificationIntegration:
    """Test the integration between monitoring and notification systems."""

    @pytest.fixture
    def mock_notification_service(self):
        """Create a mock notification service."""
        service = Mock(spec=NotificationService)
        service.send_system_alert = AsyncMock()
        service.enabled = True
        return service

    @pytest.fixture
    def api_client_with_monitoring(self, mock_notification_service):
        """Create API client with monitoring enabled."""
        with patch.dict("os.environ", {"PYTEST_API_CLIENT_UNIT_TEST": "1"}):
            client = DockerNetworkApiClient()
            client.set_notification_service(mock_notification_service)
            # Override test mode for integration tests that need to test network behavior
            client.is_test_mode = False
            return client

    @pytest.fixture
    def unified_processor_with_monitoring(self, mock_notification_service):
        """Create unified processor with monitoring enabled."""
        with patch("src.core.unified_processor.NotificationService") as mock_ns_class:
            mock_ns_class.return_value = mock_notification_service

            processor = UnifiedMatchProcessor()
            # Ensure the notification service is properly set
            processor.notification_service = mock_notification_service
            # Manually connect it to the API client since the constructor might not have done it
            processor.api_client.set_notification_service(mock_notification_service)
            return processor

    @pytest.mark.asyncio
    async def test_authentication_failure_notification_flow(self, api_client_with_monitoring):
        """Test end-to-end authentication failure notification flow."""
        client = api_client_with_monitoring

        # Simulate authentication failure
        with patch("requests.get") as mock_get:
            import requests

            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            # Mock asyncio.create_task to capture the notification call
            with patch("asyncio.create_task") as mock_create_task:
                # Trigger the failure
                result = client.fetch_matches_list()

                # Verify empty result
                assert result == []

                # Verify that create_task was called (indicating notification was triggered)
                mock_create_task.assert_called_once()

                # Get the coroutine that was passed to create_task
                notification_coro = mock_create_task.call_args[0][0]

                # Execute the coroutine to trigger the actual notification
                await notification_coro

                # Verify notification was sent
                client.notification_service.send_system_alert.assert_called_once()

            # Verify alert data
            call_args = client.notification_service.send_system_alert.call_args[0][0]
            assert call_args["alert_type"] == "authentication_failure"
            assert call_args["service"] == "fogis-api-client"
            assert call_args["severity"] == "critical"
            assert "FOGIS API authentication failed" in call_args["message"]
            assert "recovery_actions" in call_args
            assert len(call_args["recovery_actions"]) > 0

    @pytest.mark.asyncio
    async def test_unified_processor_monitoring_integration(
        self, unified_processor_with_monitoring
    ):
        """Test that unified processor properly integrates monitoring."""
        processor = unified_processor_with_monitoring

        # Verify API client has notification service connected
        assert processor.api_client.notification_service is not None
        assert processor.api_client.notification_service == processor.notification_service

    @pytest.mark.asyncio
    async def test_service_failure_notification_flow(self, api_client_with_monitoring):
        """Test service failure notification flow."""
        client = api_client_with_monitoring

        # Simulate service failure
        with patch("requests.get") as mock_get:
            import requests

            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            mock_get.return_value = mock_response

            result = client.fetch_matches_list()
            assert result == []

            await asyncio.sleep(0.1)

            client.notification_service.send_system_alert.assert_called_once()
            call_args = client.notification_service.send_system_alert.call_args[0][0]
            assert call_args["alert_type"] == "service_failure"
            assert call_args["severity"] == "high"

    @pytest.mark.asyncio
    async def test_timeout_notification_flow(self, api_client_with_monitoring):
        """Test timeout notification flow."""
        client = api_client_with_monitoring

        # Simulate timeout
        with patch("requests.get") as mock_get:
            import requests

            mock_get.side_effect = requests.exceptions.Timeout()

            result = client.fetch_matches_list()
            assert result == []

            await asyncio.sleep(0.1)

            client.notification_service.send_system_alert.assert_called_once()
            call_args = client.notification_service.send_system_alert.call_args[0][0]
            assert call_args["alert_type"] == "timeout_error"
            assert call_args["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_alert_cooldown_prevents_spam(self, api_client_with_monitoring):
        """Test that alert cooldown prevents notification spam."""
        client = api_client_with_monitoring

        # Simulate multiple authentication failures
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_get.return_value = mock_response

            # Trigger multiple failures
            client.fetch_matches_list()
            client.fetch_matches_list()
            client.fetch_matches_list()

            await asyncio.sleep(0.1)

            # Should only send one notification due to cooldown
            assert client.notification_service.send_system_alert.call_count == 1

    @pytest.mark.asyncio
    async def test_different_alert_types_not_affected_by_cooldown(self, api_client_with_monitoring):
        """Test that different alert types are not affected by each other's cooldown."""
        client = api_client_with_monitoring

        # First trigger authentication failure
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_get.return_value = mock_response

            client.fetch_matches_list()

            # Then trigger timeout
            import requests

            mock_get.side_effect = requests.exceptions.Timeout()

            client.fetch_matches_list()

            await asyncio.sleep(0.1)

            # Should send both notifications
            assert client.notification_service.send_system_alert.call_count == 2

    @pytest.mark.asyncio
    async def test_notification_service_failure_doesnt_break_processing(
        self, api_client_with_monitoring
    ):
        """Test that notification service failures don't break main processing."""
        client = api_client_with_monitoring

        # Make notification service fail
        client.notification_service.send_system_alert.side_effect = Exception("Notification failed")

        # Simulate API failure
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_get.return_value = mock_response

            # Should not raise exception despite notification failure
            result = client.fetch_matches_list()
            assert result == []

    def test_monitoring_disabled_when_no_notification_service(self):
        """Test that monitoring gracefully handles missing notification service."""
        with patch.dict("os.environ", {"PYTEST_API_CLIENT_UNIT_TEST": "1"}):
            client = DockerNetworkApiClient()
            # Don't set notification service

            # Simulate API failure
            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
                mock_get.return_value = mock_response

                # Should not raise exception
                result = client.fetch_matches_list()
                assert result == []

    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self, api_client_with_monitoring):
        """Test performance monitoring integration."""
        client = api_client_with_monitoring

        # Simulate slow response
        with (
            patch("requests.get") as mock_get,
            patch("src.services.api_client.time.time") as mock_time,
        ):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = []
            mock_get.return_value = mock_response

            # Simulate 20 second response time
            mock_time.side_effect = [1000, 1020, 1020, 1020]  # Extra calls for cooldown check

            result = client.fetch_matches_list()
            assert result == []

            await asyncio.sleep(0.1)

            client.notification_service.send_system_alert.assert_called_once()
            call_args = client.notification_service.send_system_alert.call_args[0][0]
            assert call_args["alert_type"] == "slow_response"
            assert call_args["severity"] == "medium"
            assert "20.0s" in call_args["message"]
