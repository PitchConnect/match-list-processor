"""Webhook processing service for event-driven match processing."""

import logging
import time
from typing import Any, Dict, List, Optional

from src.config import settings
from src.core.unified_processor import UnifiedMatchProcessor
from src.services.api_client import DockerNetworkApiClient

logger = logging.getLogger(__name__)


class WebhookProcessingService:
    """Service for processing webhook-triggered match updates."""

    def __init__(self) -> None:
        """Initialize the webhook processing service."""
        self.unified_processor = UnifiedMatchProcessor()
        self.api_client = DockerNetworkApiClient()

        # Processing metrics
        self.processing_count = 0
        self.last_processing_time: Optional[float] = None
        self.last_changes_detected = False
        self.processing_history: List[Dict[str, Any]] = []

    def process_webhook_trigger(
        self, trigger_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a webhook trigger with smart change detection.

        Args:
            trigger_data: Optional data from webhook trigger

        Returns:
            Processing result with metrics and status
        """
        start_time = time.time()
        processing_id = f"webhook_{int(start_time)}"

        logger.info(f"Processing webhook trigger {processing_id}")

        try:
            # Run unified processing cycle
            result = self.unified_processor.run_processing_cycle()

            # Calculate processing metrics
            processing_duration = time.time() - start_time
            self.processing_count += 1
            self.last_processing_time = time.time()

            # Determine if changes were detected
            changes_detected = False
            changes_summary = "No changes detected"

            if result and hasattr(result, "changes_detected"):
                changes_detected = result.changes_detected
                if changes_detected:
                    changes_summary = getattr(result, "summary", "Changes detected and processed")

            self.last_changes_detected = changes_detected

            # Create processing record
            processing_record = {
                "processing_id": processing_id,
                "timestamp": start_time,
                "duration": processing_duration,
                "changes_detected": changes_detected,
                "summary": changes_summary,
                "trigger_data": trigger_data,
                "status": "success",
            }

            # Add to history (keep last 10 records)
            self.processing_history.append(processing_record)
            if len(self.processing_history) > 10:
                self.processing_history.pop(0)

            logger.info(
                f"Webhook processing {processing_id} completed in {processing_duration:.2f}s - "
                f"Changes: {changes_detected}"
            )

            return processing_record

        except Exception as e:
            processing_duration = time.time() - start_time
            error_message = str(e)

            logger.error(f"Webhook processing {processing_id} failed: {error_message}")
            logger.exception("Stack trace:")

            # Create error record
            error_record = {
                "processing_id": processing_id,
                "timestamp": start_time,
                "duration": processing_duration,
                "changes_detected": False,
                "summary": f"Processing failed: {error_message}",
                "trigger_data": trigger_data,
                "status": "error",
                "error": error_message,
            }

            # Add to history
            self.processing_history.append(error_record)
            if len(self.processing_history) > 10:
                self.processing_history.pop(0)

            raise

    def get_processing_status(self) -> Dict[str, Any]:
        """
        Get current processing status and metrics.

        Returns:
            Status information including metrics and history
        """
        return {
            "processing_count": self.processing_count,
            "last_processing_time": self.last_processing_time,
            "last_changes_detected": self.last_changes_detected,
            "processing_history": self.processing_history[-5:],  # Last 5 records
            "service_status": "ready",
        }

    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed processing status with full history.

        Returns:
            Detailed status information
        """
        return {
            "processing_count": self.processing_count,
            "last_processing_time": self.last_processing_time,
            "last_changes_detected": self.last_changes_detected,
            "processing_history": self.processing_history,
            "service_status": "ready",
            "configuration": {
                "data_folder": settings.data_folder,
                "temp_file_directory": settings.temp_file_directory,
                "fogis_api_client_url": getattr(settings, "fogis_api_client_url", "N/A"),
            },
        }

    def validate_webhook_data(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Validate incoming webhook data.

        Args:
            webhook_data: Data from webhook request

        Returns:
            True if data is valid, False otherwise
        """
        # For now, accept any webhook data
        # In the future, this could validate specific webhook formats
        return True

    def should_process_webhook(self, webhook_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if webhook should trigger processing.

        Args:
            webhook_data: Optional webhook data to analyze

        Returns:
            True if processing should be triggered
        """
        # For now, always process webhooks
        # In the future, this could implement smart filtering based on:
        # - Time since last processing
        # - Webhook data content
        # - System load
        # - Configuration settings

        return True

    def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Get processing performance metrics.

        Returns:
            Performance metrics and statistics
        """
        if not self.processing_history:
            return {
                "total_processing_count": self.processing_count,
                "average_duration": 0.0,
                "success_rate": 0.0,
                "changes_detection_rate": 0.0,
                "last_processing_time": self.last_processing_time,
            }

        # Calculate metrics from history
        successful_processes = [p for p in self.processing_history if p.get("status") == "success"]
        processes_with_changes = [p for p in self.processing_history if p.get("changes_detected")]

        total_duration = sum(p.get("duration", 0) for p in self.processing_history)
        average_duration = (
            total_duration / len(self.processing_history) if self.processing_history else 0.0
        )

        success_rate = (
            len(successful_processes) / len(self.processing_history)
            if self.processing_history
            else 0.0
        )
        changes_rate = (
            len(processes_with_changes) / len(self.processing_history)
            if self.processing_history
            else 0.0
        )

        return {
            "total_processing_count": self.processing_count,
            "average_duration": round(average_duration, 3),
            "success_rate": round(success_rate, 3),
            "changes_detection_rate": round(changes_rate, 3),
            "last_processing_time": self.last_processing_time,
            "recent_processes": len(self.processing_history),
        }
