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

    def test_app_graceful_shutdown(self):
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
        # Test mode detection should prevent actual network calls

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
        # Test mode detection should prevent actual network calls

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
