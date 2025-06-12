"""FastAPI web server for health check endpoints."""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

import uvicorn  # type: ignore[import-not-found]
from fastapi import FastAPI, HTTPException  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from ..config import Settings
from ..services.health_service import HealthService

logger = logging.getLogger(__name__)


class HealthServer:
    """Web server for health check endpoints."""

    def __init__(self, settings: Settings, port: int = 8000):
        """Initialize health server."""
        self.settings = settings
        self.port = port
        self.health_service = HealthService(settings)
        self.server_thread: Optional[threading.Thread] = None
        self.app = self._create_app()
        self._server: Optional[uvicorn.Server] = None

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with health endpoints."""

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
            """Manage application lifespan."""
            logger.info("Health server starting up...")
            yield
            logger.info("Health server shutting down...")

        app = FastAPI(
            title="Match List Processor Health API",
            description="Health check endpoints for the match list processor service",
            version="1.0.0",
            lifespan=lifespan,
        )

        @app.get("/health", response_model=None)  # type: ignore[misc]
        async def health_check() -> JSONResponse:
            """
            Comprehensive health check endpoint.

            Returns:
                JSONResponse: Health status with dependency checks

            Status Codes:
                200: Service is healthy
                503: Service is unhealthy or degraded
            """
            try:
                health_status = await self.health_service.get_health_status()

                # Determine HTTP status code based on health
                if health_status.status == "healthy":
                    status_code = 200
                elif health_status.status == "degraded":
                    status_code = 200  # Still operational but with issues
                else:  # unhealthy
                    status_code = 503

                return JSONResponse(
                    status_code=status_code, content=health_status.model_dump(mode="json")
                )

            except Exception as e:
                logger.exception("Health check failed")
                return JSONResponse(
                    status_code=503,
                    content={
                        "service_name": "match-list-processor",
                        "status": "unhealthy",
                        "error": f"Health check failed: {str(e)}",
                        "timestamp": "2024-01-01T00:00:00Z",
                    },
                )

        @app.get("/health/simple")  # type: ignore[misc]
        async def simple_health_check() -> Dict[str, Any]:
            """
            Simple health check endpoint without dependency checks.

            Returns:
                Dict: Basic health status

            Status Codes:
                200: Service is running
            """
            return self.health_service.get_simple_health_status()

        @app.get("/health/dependencies")  # type: ignore[misc]
        async def dependencies_health_check() -> Dict[str, Any]:
            """
            Check only the health of service dependencies.

            Returns:
                Dict: Status of all dependencies

            Status Codes:
                200: Dependencies checked (individual status in response)
            """
            try:
                dependencies = await self.health_service.check_all_dependencies()
                return {
                    "dependencies": {
                        name: dep.model_dump(mode="json") for name, dep in dependencies.items()
                    }
                }
            except Exception as e:
                logger.exception("Dependencies check failed")
                raise HTTPException(status_code=500, detail=f"Dependencies check failed: {str(e)}")

        @app.get("/")  # type: ignore[misc]
        async def root() -> Dict[str, str]:
            """Root endpoint with basic service information."""
            return {
                "service": "match-list-processor",
                "version": "1.0.0",
                "health_endpoint": "/health",
                "simple_health_endpoint": "/health/simple",
                "dependencies_endpoint": "/health/dependencies",
            }

        return app

    def start_server(self) -> None:
        """Start the health server in a separate thread."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("Health server is already running")
            return

        def run_server() -> None:
            """Run the uvicorn server."""
            try:
                config = uvicorn.Config(
                    self.app,
                    host="0.0.0.0",  # nosec B104 - Health check server needs to bind to all interfaces
                    port=self.port,
                    log_level="info",
                    access_log=False,  # Reduce noise in logs
                )
                self._server = uvicorn.Server(config)
                if self._server:
                    asyncio.run(self._server.serve())
            except Exception as e:
                logger.exception(f"Health server failed to start: {e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"Health server started on port {self.port}")

    def stop_server(self) -> None:
        """Stop the health server."""
        if self._server:
            self._server.should_exit = True

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
            logger.info("Health server stopped")

    def is_running(self) -> bool:
        """Check if the health server is running."""
        return bool(self.server_thread and self.server_thread.is_alive())


def create_health_server(settings: Settings, port: int = 8000) -> HealthServer:
    """Factory function to create a health server instance."""
    return HealthServer(settings, port)
