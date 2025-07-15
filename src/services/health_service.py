"""Health check service for monitoring service status and dependencies."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from pydantic import BaseModel

from ..config import Settings

logger = logging.getLogger(__name__)


class DependencyStatus(BaseModel):
    """Status of a service dependency."""

    name: str
    url: str
    status: str  # "healthy", "unhealthy", "unknown"
    response_time_ms: Optional[float] = None
    error: Optional[str] = None
    last_checked: datetime


class HealthStatus(BaseModel):
    """Overall health status of the service."""

    service_name: str = "match-list-processor"
    version: str = "1.0.0"
    status: str  # "healthy", "unhealthy", "degraded"
    uptime_seconds: float
    timestamp: datetime
    dependencies: Dict[str, DependencyStatus]
    details: Dict[str, Any]


class HealthService:
    """Service for checking health status and dependencies."""

    def __init__(self, settings: Settings):
        """Initialize health service with configuration."""
        self.settings = settings
        self.start_time = time.time()
        self._dependency_endpoints = {
            "fogis-api-client": {
                "url": f"{settings.fogis_api_client_url}/health",
                "timeout": 5,
            },
            "whatsapp-avatar-service": {
                "url": f"{settings.whatsapp_avatar_service_url}/health",
                "timeout": 5,
            },
            "google-drive-service": {
                "url": f"{settings.google_drive_service_url}/health",
                "timeout": 5,
            },
            "phonebook-sync-service": {
                "url": f"{settings.phonebook_sync_service_url}/health",
                "timeout": 5,
            },
        }

    async def check_dependency(self, name: str, config: Dict[str, Any]) -> DependencyStatus:
        """Check the health of a single dependency."""
        start_time = time.time()

        try:
            # Use asyncio to run the synchronous request in a thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(  # nosec B113 - timeout is specified in config
                    config["url"],
                    timeout=config["timeout"],
                    headers={"User-Agent": "match-list-processor-health-check"},
                ),
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                status = "healthy"
                error = None
            else:
                status = "unhealthy"
                error = f"HTTP {response.status_code}: {response.text[:100]}"

        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            status = "unhealthy"
            error = "Request timeout"

        except requests.exceptions.ConnectionError:
            response_time = (time.time() - start_time) * 1000
            status = "unhealthy"
            error = "Connection error"

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = "unknown"
            error = f"Unexpected error: {str(e)}"
            logger.exception(f"Unexpected error checking {name}")

        return DependencyStatus(
            name=name,
            url=config["url"],
            status=status,
            response_time_ms=response_time,
            error=error,
            last_checked=datetime.now(timezone.utc),
        )

    async def check_all_dependencies(self) -> Dict[str, DependencyStatus]:
        """Check all service dependencies concurrently."""
        tasks = [
            self.check_dependency(name, config)
            for name, config in self._dependency_endpoints.items()
        ]

        dependency_results = await asyncio.gather(*tasks, return_exceptions=True)

        dependencies = {}
        for i, result in enumerate(dependency_results):
            name = list(self._dependency_endpoints.keys())[i]
            if isinstance(result, Exception):
                logger.exception(f"Failed to check dependency {name}")
                dependencies[name] = DependencyStatus(
                    name=name,
                    url=str(self._dependency_endpoints[name]["url"]),
                    status="unknown",
                    error=f"Health check failed: {str(result)}",
                    last_checked=datetime.now(timezone.utc),
                )
            elif isinstance(result, DependencyStatus):
                dependencies[name] = result

        return dependencies

    def _determine_overall_status(self, dependencies: Dict[str, DependencyStatus]) -> str:
        """Determine overall service status based on dependencies."""
        healthy_count = sum(1 for dep in dependencies.values() if dep.status == "healthy")
        total_count = len(dependencies)

        if healthy_count == total_count:
            return "healthy"
        elif healthy_count >= total_count * 0.5:  # At least 50% healthy
            return "degraded"
        else:
            return "unhealthy"

    def _get_service_details(self) -> Dict[str, Any]:
        """Get additional service details for health check."""
        return {
            "data_folder": self.settings.data_folder,
            "min_referees_for_whatsapp": self.settings.min_referees_for_whatsapp,
            "log_level": self.settings.log_level,
            "python_version": "3.9+",
            "environment": "production",
        }

    async def get_health_status(self) -> HealthStatus:
        """Get comprehensive health status of the service."""
        dependencies = await self.check_all_dependencies()
        overall_status = self._determine_overall_status(dependencies)
        uptime = time.time() - self.start_time

        return HealthStatus(
            status=overall_status,
            uptime_seconds=uptime,
            timestamp=datetime.now(timezone.utc),
            dependencies=dependencies,
            details=self._get_service_details(),
        )

    def get_simple_health_status(self) -> Dict[str, Any]:
        """Get a simple synchronous health status (for basic checks)."""
        uptime = time.time() - self.start_time

        return {
            "service_name": "match-list-processor",
            "status": "healthy",  # Basic status without dependency checks
            "uptime_seconds": uptime,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
