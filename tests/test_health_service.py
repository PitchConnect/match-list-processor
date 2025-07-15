"""Tests for the health service."""

import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from src.config import Settings
from src.services.health_service import DependencyStatus, HealthService, HealthStatus


class TestDependencyStatus:
    """Test DependencyStatus model."""

    def test_dependency_status_creation(self):
        """Test creating a DependencyStatus instance."""
        now = datetime.now(timezone.utc)
        status = DependencyStatus(
            name="test-service",
            url="http://test:8080/health",
            status="healthy",
            response_time_ms=150.5,
            last_checked=now,
        )

        assert status.name == "test-service"
        assert status.url == "http://test:8080/health"
        assert status.status == "healthy"
        assert status.response_time_ms == 150.5
        assert status.error is None
        assert status.last_checked == now

    def test_dependency_status_with_error(self):
        """Test creating a DependencyStatus with error."""
        now = datetime.now(timezone.utc)
        status = DependencyStatus(
            name="failing-service",
            url="http://failing:8080/health",
            status="unhealthy",
            error="Connection timeout",
            last_checked=now,
        )

        assert status.status == "unhealthy"
        assert status.error == "Connection timeout"


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_health_status_creation(self):
        """Test creating a HealthStatus instance."""
        now = datetime.now(timezone.utc)
        dependencies = {
            "test-service": DependencyStatus(
                name="test-service",
                url="http://test:8080/health",
                status="healthy",
                last_checked=now,
            )
        }

        health_status = HealthStatus(
            status="healthy",
            uptime_seconds=3600.0,
            timestamp=now,
            dependencies=dependencies,
            details={"environment": "test"},
        )

        assert health_status.service_name == "match-list-processor"
        assert health_status.version == "1.0.0"
        assert health_status.status == "healthy"
        assert health_status.uptime_seconds == 3600.0
        assert health_status.timestamp == now
        assert len(health_status.dependencies) == 1
        assert health_status.details["environment"] == "test"


class TestHealthService:
    """Test HealthService functionality."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        # Use default settings and override via environment variables if needed
        return Settings()

    @pytest.fixture
    def health_service(self, settings):
        """Create health service instance."""
        return HealthService(settings)

    def test_health_service_initialization(self, health_service, settings):
        """Test health service initialization."""
        assert health_service.settings == settings
        assert health_service.start_time <= time.time()
        assert len(health_service._dependency_endpoints) == 4

        # Check dependency endpoints are configured correctly
        assert "fogis-api-client" in health_service._dependency_endpoints
        assert "whatsapp-avatar-service" in health_service._dependency_endpoints
        assert "google-drive-service" in health_service._dependency_endpoints
        assert "phonebook-sync-service" in health_service._dependency_endpoints

        # Check URLs are properly configured
        endpoints = health_service._dependency_endpoints
        assert endpoints["fogis-api-client"]["url"] == f"{settings.fogis_api_client_url}/health"
        assert (
            endpoints["whatsapp-avatar-service"]["url"]
            == f"{settings.whatsapp_avatar_service_url}/health"
        )
        assert (
            endpoints["google-drive-service"]["url"]
            == f"{settings.google_drive_service_url}/health"
        )
        assert (
            endpoints["phonebook-sync-service"]["url"]
            == f"{settings.phonebook_sync_service_url}/health"
        )

    @pytest.mark.asyncio
    async def test_check_dependency_healthy(self, health_service):
        """Test checking a healthy dependency."""
        config = {"url": "http://test:8080/health", "timeout": 5}

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_get.return_value = mock_response

            status = await health_service.check_dependency("test-service", config)

            assert status.name == "test-service"
            assert status.url == "http://test:8080/health"
            assert status.status == "healthy"
            assert status.error is None
            assert status.response_time_ms is not None
            assert status.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_check_dependency_unhealthy_http_error(self, health_service):
        """Test checking a dependency that returns HTTP error."""
        config = {"url": "http://test:8080/health", "timeout": 5}

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_get.return_value = mock_response

            status = await health_service.check_dependency("test-service", config)

            assert status.status == "unhealthy"
            assert "HTTP 500" in status.error
            assert status.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_dependency_timeout(self, health_service):
        """Test checking a dependency that times out."""
        config = {"url": "http://test:8080/health", "timeout": 5}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout()

            status = await health_service.check_dependency("test-service", config)

            assert status.status == "unhealthy"
            assert status.error == "Request timeout"
            assert status.response_time_ms is not None

    @pytest.mark.asyncio
    async def test_check_dependency_connection_error(self, health_service):
        """Test checking a dependency with connection error."""
        config = {"url": "http://test:8080/health", "timeout": 5}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            status = await health_service.check_dependency("test-service", config)

            assert status.status == "unhealthy"
            assert status.error == "Connection error"

    @pytest.mark.asyncio
    async def test_check_dependency_unexpected_error(self, health_service):
        """Test checking a dependency with unexpected error."""
        config = {"url": "http://test:8080/health", "timeout": 5}

        with patch("requests.get") as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")

            status = await health_service.check_dependency("test-service", config)

            assert status.status == "unknown"
            assert "Unexpected error" in status.error

    @pytest.mark.asyncio
    async def test_check_all_dependencies(self, health_service):
        """Test checking all dependencies."""
        with patch.object(health_service, "check_dependency") as mock_check:
            # Mock dependency check results
            mock_results = [
                DependencyStatus(
                    name="fogis-api-client",
                    url="http://fogis-api:8080/hello",
                    status="healthy",
                    last_checked=datetime.now(timezone.utc),
                ),
                DependencyStatus(
                    name="whatsapp-avatar-service",
                    url="http://avatar:5002/health",
                    status="unhealthy",
                    error="Connection error",
                    last_checked=datetime.now(timezone.utc),
                ),
                DependencyStatus(
                    name="google-drive-service",
                    url="http://gdrive:5000/health",
                    status="healthy",
                    last_checked=datetime.now(timezone.utc),
                ),
                DependencyStatus(
                    name="phonebook-sync-service",
                    url="http://phonebook:5003/health",
                    status="healthy",
                    last_checked=datetime.now(timezone.utc),
                ),
            ]

            mock_check.side_effect = mock_results

            dependencies = await health_service.check_all_dependencies()

            assert len(dependencies) == 4
            assert dependencies["fogis-api-client"].status == "healthy"
            assert dependencies["whatsapp-avatar-service"].status == "unhealthy"
            assert dependencies["google-drive-service"].status == "healthy"
            assert dependencies["phonebook-sync-service"].status == "healthy"

    def test_determine_overall_status_all_healthy(self, health_service):
        """Test overall status when all dependencies are healthy."""
        dependencies = {
            "service1": Mock(status="healthy"),
            "service2": Mock(status="healthy"),
            "service3": Mock(status="healthy"),
            "service4": Mock(status="healthy"),
        }

        status = health_service._determine_overall_status(dependencies)
        assert status == "healthy"

    def test_determine_overall_status_degraded(self, health_service):
        """Test overall status when some dependencies are unhealthy."""
        dependencies = {
            "service1": Mock(status="healthy"),
            "service2": Mock(status="unhealthy"),
            "service3": Mock(status="healthy"),
            "service4": Mock(status="healthy"),
        }

        status = health_service._determine_overall_status(dependencies)
        assert status == "degraded"

    def test_determine_overall_status_unhealthy(self, health_service):
        """Test overall status when most dependencies are unhealthy."""
        dependencies = {
            "service1": Mock(status="unhealthy"),
            "service2": Mock(status="unhealthy"),
            "service3": Mock(status="unhealthy"),
            "service4": Mock(status="healthy"),
        }

        status = health_service._determine_overall_status(dependencies)
        assert status == "unhealthy"

    def test_get_service_details(self, health_service):
        """Test getting service details."""
        details = health_service._get_service_details()

        assert "data_folder" in details
        assert "min_referees_for_whatsapp" in details
        assert "log_level" in details
        assert "python_version" in details
        assert "environment" in details

    @pytest.mark.asyncio
    async def test_get_health_status(self, health_service):
        """Test getting comprehensive health status."""
        with patch.object(health_service, "check_all_dependencies") as mock_check_deps:
            mock_dependencies = {
                "service1": DependencyStatus(
                    name="service1",
                    url="http://service1:8080/health",
                    status="healthy",
                    last_checked=datetime.now(timezone.utc),
                ),
                "service2": DependencyStatus(
                    name="service2",
                    url="http://service2:8080/health",
                    status="healthy",
                    last_checked=datetime.now(timezone.utc),
                ),
            }
            mock_check_deps.return_value = mock_dependencies

            health_status = await health_service.get_health_status()

            assert isinstance(health_status, HealthStatus)
            assert health_status.service_name == "match-list-processor"
            assert health_status.version == "1.0.0"
            assert health_status.status == "healthy"
            assert health_status.uptime_seconds > 0
            assert len(health_status.dependencies) == 2
            assert health_status.details is not None

    def test_get_simple_health_status(self, health_service):
        """Test getting simple health status."""
        status = health_service.get_simple_health_status()

        assert status["service_name"] == "match-list-processor"
        assert status["status"] == "healthy"
        assert status["uptime_seconds"] > 0
        assert "timestamp" in status
