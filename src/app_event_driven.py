"""Event-driven FastAPI application for webhook-triggered match processing."""

import asyncio
import logging
import os
import signal
import sys
import threading
import time
from contextlib import asynccontextmanager
from types import FrameType
from typing import Optional

try:
    from typing import AsyncGenerator
except ImportError:
    from typing_extensions import AsyncGenerator

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import JSONResponse

from src.config import settings
from src.core.data_manager import MatchDataManager
from src.core.match_processor import MatchProcessor
from src.services.api_client import DockerNetworkApiClient
from src.services.avatar_service import WhatsAppAvatarService
from src.services.health_service import HealthService
from src.services.phonebook_service import FogisPhonebookSyncService
from src.services.storage_service import GoogleDriveStorageService
from src.services.webhook_service import WebhookProcessingService
from src.utils.description_generator import generate_whatsapp_description

logger = logging.getLogger(__name__)


class EventDrivenMatchProcessor:
    """Event-driven match processor with webhook endpoints."""

    def __init__(self) -> None:
        """Initialize the event-driven processor."""
        # Core services
        self.data_manager = MatchDataManager()
        self.api_client = DockerNetworkApiClient()
        self.avatar_service = WhatsAppAvatarService()
        self.storage_service = GoogleDriveStorageService()
        self.phonebook_service = FogisPhonebookSyncService()
        self.health_service = HealthService(settings)

        # Webhook processing service
        self.webhook_service = WebhookProcessingService()

        # Legacy processor for compatibility
        self.match_processor = MatchProcessor(
            self.avatar_service,
            self.storage_service,
            generate_whatsapp_description,
        )

        # Processing state
        self.processing = False
        self.processing_count = 0
        self.last_processing_time: Optional[float] = None
        self.processing_lock = threading.Lock()

        # Server configuration
        self.port = int(os.environ.get("PORT", "8000"))
        self.host = os.environ.get("HOST", "0.0.0.0")  # nosec B104

        # Create FastAPI app
        self.app = self._create_app()
        self.server: Optional[uvicorn.Server] = None

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if self.server:
            self.server.should_exit = True

    def _create_app(self) -> FastAPI:
        """Create FastAPI application with webhook and health endpoints."""

        @asynccontextmanager
        async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
            """Manage application lifespan."""
            logger.info("Event-driven match processor starting up...")
            yield
            logger.info("Event-driven match processor shutting down...")

        app = FastAPI(
            title="Match List Processor - Event Driven",
            description="Event-driven match list processor with webhook processing",
            version="2.0.0",
            lifespan=lifespan,
        )

        @app.get("/")
        async def root() -> JSONResponse:
            """Service information endpoint."""
            return JSONResponse(
                content={
                    "service_name": "match-list-processor",
                    "version": "2.0.0",
                    "mode": "event-driven",
                    "status": "running",
                    "processing": self.processing,
                    "processing_count": self.webhook_service.processing_count,
                    "last_processing_time": self.webhook_service.last_processing_time,
                }
            )

        @app.get("/health")
        async def health_check() -> JSONResponse:
            """Enhanced health check with processing status."""
            try:
                # Get dependency health status
                health_status = await self.health_service.get_health_status()

                # Convert dependencies to dict for JSON serialization
                dependencies_dict = {}
                for name, dep_status in health_status.dependencies.items():
                    dependencies_dict[name] = {
                        "name": dep_status.name,
                        "url": dep_status.url,
                        "status": dep_status.status,
                        "response_time_ms": dep_status.response_time_ms,
                        "error": dep_status.error,
                        "last_checked": (
                            dep_status.last_checked.isoformat() if dep_status.last_checked else None
                        ),
                    }

                return JSONResponse(
                    content={
                        "service_name": "match-list-processor",
                        "status": health_status.status,
                        "mode": "event-driven",
                        "processing": self.processing,
                        "processing_count": self.webhook_service.processing_count,
                        "last_processing_time": self.webhook_service.last_processing_time,
                        "dependencies": dependencies_dict,
                        "timestamp": time.time(),
                    }
                )
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "service_name": "match-list-processor",
                        "status": "unhealthy",
                        "error": str(e),
                        "timestamp": time.time(),
                    },
                )

        @app.get("/health/simple")
        async def simple_health_check() -> JSONResponse:
            """Simple health check for basic monitoring."""
            return JSONResponse(content={"status": "healthy"})

        @app.post("/process")
        async def process_webhook(background_tasks: BackgroundTasks) -> JSONResponse:
            """Webhook endpoint to trigger match processing."""
            # Check if already processing
            with self.processing_lock:
                if self.processing:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "status": "busy",
                            "message": "Processing already in progress",
                            "processing_count": self.webhook_service.processing_count,
                        },
                    )

                # Mark as processing
                self.processing = True

            # Start background processing
            background_tasks.add_task(self._process_matches_background)

            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Match processing triggered",
                    "processing_count": self.webhook_service.processing_count + 1,
                }
            )

        @app.get("/status")
        async def processing_status() -> JSONResponse:
            """Get current processing status and metrics."""
            status = self.webhook_service.get_processing_status()
            status["currently_processing"] = self.processing
            return JSONResponse(content=status)

        @app.get("/status/detailed")
        async def detailed_processing_status() -> JSONResponse:
            """Get detailed processing status with full history."""
            status = self.webhook_service.get_detailed_status()
            status["currently_processing"] = self.processing
            return JSONResponse(content=status)

        @app.get("/metrics")
        async def processing_metrics() -> JSONResponse:
            """Get processing performance metrics."""
            metrics = self.webhook_service.get_processing_metrics()
            metrics["currently_processing"] = self.processing
            return JSONResponse(content=metrics)

        return app

    async def _process_matches_background(self) -> None:
        """Process matches in background thread."""
        try:
            # Run processing in thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._process_matches_sync)
        except Exception as e:
            logger.error(f"Background processing failed: {e}")
            logger.exception("Stack trace:")
        finally:
            # Always reset processing state
            with self.processing_lock:
                self.processing = False

    def _process_matches_sync(self) -> None:
        """Synchronous match processing logic."""
        try:
            logger.info("Starting webhook-triggered match processing...")

            # Use webhook service for smart processing
            result = self.webhook_service.process_webhook_trigger()

            if result.get("changes_detected"):
                logger.info(f"Changes detected and processed: {result.get('summary')}")
            else:
                logger.info("No changes detected - processing completed")

        except Exception as e:
            logger.error(f"Match processing failed: {e}")
            logger.exception("Stack trace:")
            raise

    async def run_server(self) -> None:
        """Run the FastAPI server."""
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True,
        )

        self.server = uvicorn.Server(config)
        logger.info(f"Starting event-driven server on {self.host}:{self.port}")

        try:
            await self.server.serve()
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

    def run(self) -> None:
        """Run the event-driven application."""
        logger.info("Starting event-driven match list processor...")

        try:
            # Run the async server
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error(f"Application error: {e}")
            logger.exception("Stack trace:")
            sys.exit(1)


def main() -> None:
    """Main entry point for event-driven mode."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run the event-driven processor
    processor = EventDrivenMatchProcessor()
    processor.run()


if __name__ == "__main__":
    main()
