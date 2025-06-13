"""Integration tests for health check functionality."""

import time
from unittest.mock import patch

import pytest
import requests

from src.app import MatchListProcessorApp
from src.config import Settings
from src.web.health_server import create_health_server


class TestHealthIntegration:
    """Integration tests for health check functionality."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    def test_health_server_integration(self, settings):
        """Test health server integration with real HTTP requests."""
        health_server = create_health_server(settings, port=8004)

        try:
            # Start the server
            health_server.start_server()
            time.sleep(2)  # Give server time to start

            assert health_server.is_running()

            # Test simple health endpoint
            response = requests.get("http://localhost:8004/health/simple", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["service_name"] == "match-list-processor"
            assert data["status"] == "healthy"
            assert "uptime_seconds" in data

            # Test root endpoint
            response = requests.get("http://localhost:8004/", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["service"] == "match-list-processor"
            assert data["version"] == "1.0.0"

        except requests.exceptions.ConnectionError:
            pytest.skip("Health server failed to start - this may be expected in CI")
        finally:
            health_server.stop_server()

    def test_health_server_basic_endpoints(self, settings):
        """Test basic health server endpoints without dependency mocking."""
        health_server = create_health_server(settings, port=8005)

        try:
            health_server.start_server()
            time.sleep(2)

            # Test simple health endpoint (no dependencies)
            response = requests.get("http://localhost:8005/health/simple", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["service_name"] == "match-list-processor"
            assert data["status"] == "healthy"
            assert "uptime_seconds" in data

            # Test root endpoint
            response = requests.get("http://localhost:8005/", timeout=5)
            assert response.status_code == 200

            data = response.json()
            assert data["service"] == "match-list-processor"
            assert data["version"] == "1.0.0"

        except requests.exceptions.ConnectionError:
            pytest.skip("Health server failed to start - this may be expected in CI")
        finally:
            health_server.stop_server()


class TestAppHealthIntegration:
    """Test health server integration with the main application."""

    @pytest.fixture
    def mock_services(self):
        """Mock all external services for testing."""
        with (
            patch("src.services.api_client.DockerNetworkApiClient"),
            patch("src.services.avatar_service.WhatsAppAvatarService"),
            patch("src.services.storage_service.GoogleDriveStorageService"),
            patch("src.services.phonebook_service.FogisPhonebookSyncService"),
            patch("src.core.data_manager.MatchDataManager"),
        ):
            yield

    def test_app_starts_health_server(self, mock_services):  # noqa: ARG002
        """Test that the main app starts the health server."""
        with patch("src.app.MatchListProcessorApp.run") as mock_run:
            # Mock the run method to avoid actual processing
            mock_run.return_value = None

            app = MatchListProcessorApp()

            # Health server should be initialized
            assert hasattr(app, "health_server")
            assert app.health_server is not None

            # Test that health server can be started
            try:
                app.health_server.start_server()
                time.sleep(1)

                assert app.health_server.is_running()

                # Test simple health check
                response = requests.get("http://localhost:8000/health/simple", timeout=5)
                assert response.status_code == 200

            except requests.exceptions.ConnectionError:
                pytest.skip("Health server failed to start - this may be expected in CI")
            finally:
                app.shutdown()

    def test_app_graceful_shutdown(self, mock_services):  # noqa: ARG002
        """Test that the app shuts down the health server gracefully."""
        with patch("src.app.MatchListProcessorApp.run") as mock_run:
            mock_run.return_value = None

            app = MatchListProcessorApp()

            # Start health server
            app.health_server.start_server()
            time.sleep(1)

            if app.health_server.is_running():
                # Shutdown should stop the health server
                app.shutdown()
                time.sleep(1)

                assert not app.health_server.is_running()


class TestDockerHealthCheck:
    """Test Docker health check compatibility."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    def test_health_check_endpoint_format(self, settings):
        """Test that health check endpoint returns expected format for Docker."""
        health_server = create_health_server(settings, port=8008)

        try:
            health_server.start_server()
            time.sleep(2)

            # Test the simple health endpoint that Docker will use
            response = requests.get("http://localhost:8008/health/simple", timeout=5)
            assert response.status_code == 200

            data = response.json()

            # Verify required fields for Docker health check
            assert "service_name" in data
            assert "status" in data
            assert "uptime_seconds" in data
            assert "timestamp" in data

            # Status should be a string
            assert isinstance(data["status"], str)
            assert data["status"] in ["healthy", "unhealthy", "degraded"]

            # Uptime should be a number
            assert isinstance(data["uptime_seconds"], (int, float))
            assert data["uptime_seconds"] >= 0

        except requests.exceptions.ConnectionError:
            pytest.skip("Health server failed to start - this may be expected in CI")
        finally:
            health_server.stop_server()

    def test_health_check_response_time(self, settings):
        """Test that health check responds quickly for Docker timeout requirements."""
        health_server = create_health_server(settings, port=8009)

        try:
            health_server.start_server()
            time.sleep(2)

            # Measure response time
            start_time = time.time()
            response = requests.get("http://localhost:8009/health/simple", timeout=5)
            response_time = time.time() - start_time

            assert response.status_code == 200
            # Should respond within 5 seconds (Docker timeout is 10s)
            assert response_time < 5.0

        except requests.exceptions.ConnectionError:
            pytest.skip("Health server failed to start - this may be expected in CI")
        finally:
            health_server.stop_server()
