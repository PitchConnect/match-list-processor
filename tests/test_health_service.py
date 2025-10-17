"""Tests for the health service."""

import os
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest
import requests

from src.config import Settings
from src.services.health_service import DependencyStatus, HealthService, HealthStatus


@pytest.fixture
def health_service():
    """Create a HealthService instance for testing."""
    settings = Settings()
    return HealthService(settings)


class TestDependencyStatus:
    """Test DependencyStatus model."""

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
