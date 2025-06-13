"""Tests for the health server."""

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.services.health_service import DependencyStatus, HealthStatus
from src.web.health_server import HealthServer, create_health_server


class TestHealthServer:
    """Test HealthServer functionality."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def health_server(self, settings):
        """Create health server instance."""
        return HealthServer(settings, port=8001)  # Use different port for testing

    def test_health_server_initialization(self, health_server, settings):
        """Test health server initialization."""
        assert health_server.settings == settings
        assert health_server.port == 8001
        assert health_server.health_service is not None
        assert health_server.app is not None
        assert health_server.server_thread is None

    def test_create_health_server_factory(self, settings):
        """Test health server factory function."""
        server = create_health_server(settings, port=8002)

        assert isinstance(server, HealthServer)
        assert server.settings == settings
        assert server.port == 8002

    def test_fastapi_app_creation(self, health_server):
        """Test FastAPI app is created correctly."""
        app = health_server.app

        assert app.title == "Match List Processor Health API"
        assert app.version == "1.0.0"

        # Check routes are registered
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes
        assert "/health/simple" in routes
        assert "/health/dependencies" in routes


class TestHealthEndpoints:
    """Test health check endpoints using TestClient."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def health_server(self, settings):
        """Create health server for testing."""
        return HealthServer(settings, port=8001)

    @pytest.fixture
    def client(self, health_server):
        """Create test client."""
        return TestClient(health_server.app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns service information."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "match-list-processor"
        assert data["version"] == "1.0.0"
        assert data["health_endpoint"] == "/health"
        assert data["simple_health_endpoint"] == "/health/simple"
        assert data["dependencies_endpoint"] == "/health/dependencies"

    def test_simple_health_endpoint(self, client):
        """Test simple health endpoint."""
        response = client.get("/health/simple")

        assert response.status_code == 200
        data = response.json()

        assert data["service_name"] == "match-list-processor"
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data
        assert "timestamp" in data
        assert data["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_health_endpoint_healthy(self, client, health_server):
        """Test health endpoint when service is healthy."""
        # Mock the health service to return healthy status
        mock_health_status = HealthStatus(
            status="healthy",
            uptime_seconds=3600.0,
            timestamp="2024-01-01T12:00:00Z",
            dependencies={
                "test-service": DependencyStatus(
                    name="test-service",
                    url="http://test:8080/health",
                    status="healthy",
                    last_checked="2024-01-01T12:00:00Z",
                )
            },
            details={"environment": "test"},
        )

        with patch.object(
            health_server.health_service, "get_health_status", return_value=mock_health_status
        ):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()

            assert data["service_name"] == "match-list-processor"
            assert data["status"] == "healthy"
            assert data["uptime_seconds"] == 3600.0
            assert "dependencies" in data
            assert "details" in data

    @pytest.mark.asyncio
    async def test_health_endpoint_degraded(self, client, health_server):
        """Test health endpoint when service is degraded."""
        mock_health_status = HealthStatus(
            status="degraded",
            uptime_seconds=1800.0,
            timestamp="2024-01-01T12:00:00Z",
            dependencies={},
            details={},
        )

        with patch.object(
            health_server.health_service, "get_health_status", return_value=mock_health_status
        ):
            response = client.get("/health")

            assert response.status_code == 200  # Still operational
            data = response.json()
            assert data["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_health_endpoint_unhealthy(self, client, health_server):
        """Test health endpoint when service is unhealthy."""
        mock_health_status = HealthStatus(
            status="unhealthy",
            uptime_seconds=900.0,
            timestamp="2024-01-01T12:00:00Z",
            dependencies={},
            details={},
        )

        with patch.object(
            health_server.health_service, "get_health_status", return_value=mock_health_status
        ):
            response = client.get("/health")

            assert response.status_code == 503  # Service unavailable
            data = response.json()
            assert data["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_endpoint_exception(self, client, health_server):
        """Test health endpoint when health check fails."""
        with patch.object(
            health_server.health_service,
            "get_health_status",
            side_effect=Exception("Health check failed"),
        ):
            response = client.get("/health")

            assert response.status_code == 503
            data = response.json()

            assert data["service_name"] == "match-list-processor"
            assert data["status"] == "unhealthy"
            assert "Health check failed" in data["error"]

    @pytest.mark.asyncio
    async def test_dependencies_endpoint(self, client, health_server):
        """Test dependencies health endpoint."""
        mock_dependencies = {
            "service1": DependencyStatus(
                name="service1",
                url="http://service1:8080/health",
                status="healthy",
                last_checked="2024-01-01T12:00:00Z",
            ),
            "service2": DependencyStatus(
                name="service2",
                url="http://service2:8080/health",
                status="unhealthy",
                error="Connection timeout",
                last_checked="2024-01-01T12:00:00Z",
            ),
        }

        with patch.object(
            health_server.health_service, "check_all_dependencies", return_value=mock_dependencies
        ):
            response = client.get("/health/dependencies")

            assert response.status_code == 200
            data = response.json()

            assert "dependencies" in data
            assert len(data["dependencies"]) == 2
            assert data["dependencies"]["service1"]["status"] == "healthy"
            assert data["dependencies"]["service2"]["status"] == "unhealthy"
            assert data["dependencies"]["service2"]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_dependencies_endpoint_exception(self, client, health_server):
        """Test dependencies endpoint when check fails."""
        with patch.object(
            health_server.health_service,
            "check_all_dependencies",
            side_effect=Exception("Dependencies check failed"),
        ):
            response = client.get("/health/dependencies")

            assert response.status_code == 500
            data = response.json()
            assert "Dependencies check failed" in data["detail"]


class TestHealthServerLifecycle:
    """Test health server lifecycle management."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def health_server(self, settings):
        """Create health server for testing."""
        return HealthServer(settings, port=8003)  # Use unique port

    def test_server_not_running_initially(self, health_server):
        """Test server is not running initially."""
        assert not health_server.is_running()

    def test_start_server(self, health_server):
        """Test starting the health server."""
        try:
            health_server.start_server()

            # Give server time to start
            time.sleep(1)

            assert health_server.is_running()
            assert health_server.server_thread is not None
            assert health_server.server_thread.is_alive()

        finally:
            health_server.stop_server()

    def test_stop_server(self, health_server):
        """Test stopping the health server."""
        health_server.start_server()
        time.sleep(1)

        assert health_server.is_running()

        health_server.stop_server()
        time.sleep(1)

        # Server should be stopped
        assert not health_server.is_running()

    def test_start_server_twice(self, health_server):
        """Test starting server twice doesn't create multiple threads."""
        try:
            health_server.start_server()
            time.sleep(0.5)

            first_thread = health_server.server_thread

            # Try to start again
            health_server.start_server()

            # Should be the same thread
            assert health_server.server_thread == first_thread

        finally:
            health_server.stop_server()

    def test_stop_server_when_not_running(self, health_server):
        """Test stopping server when it's not running."""
        # Should not raise an exception
        health_server.stop_server()
        assert not health_server.is_running()
