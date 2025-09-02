"""Tests for event-driven architecture and webhook processing."""

import os
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.app_event_driven import EventDrivenMatchProcessor
from src.services.webhook_service import WebhookProcessingService


class TestWebhookProcessingService(unittest.TestCase):
    """Test webhook processing service functionality."""

    def setUp(self):
        """Set up test environment."""
        self.webhook_service = WebhookProcessingService()

    @patch("src.services.webhook_service.UnifiedMatchProcessor")
    def test_process_webhook_trigger_success(self, mock_processor_class):
        """Test successful webhook processing."""
        # Mock the unified processor
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.changes_detected = True
        mock_result.summary = "Test changes detected"
        mock_processor.run_processing_cycle.return_value = mock_result
        mock_processor_class.return_value = mock_processor

        # Create new service instance to use mocked processor
        service = WebhookProcessingService()

        # Process webhook trigger
        result = service.process_webhook_trigger({"test": "data"})

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["changes_detected"])
        self.assertEqual(result["summary"], "Test changes detected")
        self.assertIn("processing_id", result)
        self.assertIn("duration", result)
        self.assertIsNotNone(result["trigger_data"])

    @patch("src.services.webhook_service.UnifiedMatchProcessor")
    def test_process_webhook_trigger_no_changes(self, mock_processor_class):
        """Test webhook processing with no changes detected."""
        # Mock the unified processor
        mock_processor = MagicMock()
        mock_result = MagicMock()
        mock_result.changes_detected = False
        mock_processor.run_processing_cycle.return_value = mock_result
        mock_processor_class.return_value = mock_processor

        # Create new service instance to use mocked processor
        service = WebhookProcessingService()

        # Process webhook trigger
        result = service.process_webhook_trigger()

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["changes_detected"])
        self.assertEqual(result["summary"], "No changes detected")

    @patch("src.services.webhook_service.UnifiedMatchProcessor")
    def test_process_webhook_trigger_error(self, mock_processor_class):
        """Test webhook processing with error."""
        # Mock the unified processor to raise an exception
        mock_processor = MagicMock()
        mock_processor.run_processing_cycle.side_effect = Exception("Test error")
        mock_processor_class.return_value = mock_processor

        # Create new service instance to use mocked processor
        service = WebhookProcessingService()

        # Process webhook trigger should raise exception
        with self.assertRaises(Exception) as context:
            service.process_webhook_trigger()

        self.assertEqual(str(context.exception), "Test error")

        # Check that error was recorded in history
        self.assertEqual(len(service.processing_history), 1)
        self.assertEqual(service.processing_history[0]["status"], "error")

    def test_get_processing_status(self):
        """Test getting processing status."""
        status = self.webhook_service.get_processing_status()

        self.assertIn("processing_count", status)
        self.assertIn("last_processing_time", status)
        self.assertIn("last_changes_detected", status)
        self.assertIn("processing_history", status)
        self.assertIn("service_status", status)
        self.assertEqual(status["service_status"], "ready")

    def test_get_detailed_status(self):
        """Test getting detailed processing status."""
        status = self.webhook_service.get_detailed_status()

        self.assertIn("processing_count", status)
        self.assertIn("configuration", status)
        self.assertIn("data_folder", status["configuration"])

    def test_get_processing_metrics(self):
        """Test getting processing metrics."""
        metrics = self.webhook_service.get_processing_metrics()

        self.assertIn("total_processing_count", metrics)
        self.assertIn("average_duration", metrics)
        self.assertIn("success_rate", metrics)
        self.assertIn("changes_detection_rate", metrics)

    def test_validate_webhook_data(self):
        """Test webhook data validation."""
        # Currently accepts any data
        self.assertTrue(self.webhook_service.validate_webhook_data({}))
        self.assertTrue(self.webhook_service.validate_webhook_data({"test": "data"}))

    def test_should_process_webhook(self):
        """Test webhook processing decision logic."""
        # Currently always processes
        self.assertTrue(self.webhook_service.should_process_webhook())
        self.assertTrue(self.webhook_service.should_process_webhook({"test": "data"}))


class TestEventDrivenApp(unittest.TestCase):
    """Test event-driven FastAPI application."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()

        # Set environment variables for testing
        os.environ["DATA_FOLDER"] = self.temp_dir
        os.environ["TEMP_FILE_DIRECTORY"] = self.temp_dir

        # Create event-driven processor
        self.processor = EventDrivenMatchProcessor()
        self.client = TestClient(self.processor.app)

    def tearDown(self):
        """Clean up test environment."""
        # Clean up environment variables
        if "DATA_FOLDER" in os.environ:
            del os.environ["DATA_FOLDER"]
        if "TEMP_FILE_DIRECTORY" in os.environ:
            del os.environ["TEMP_FILE_DIRECTORY"]

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["service_name"], "match-list-processor")
        self.assertEqual(data["version"], "2.0.0")
        self.assertEqual(data["mode"], "event-driven")
        self.assertEqual(data["status"], "running")

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["service_name"], "match-list-processor")
        self.assertIn("status", data)
        self.assertEqual(data["mode"], "event-driven")

    def test_simple_health_endpoint(self):
        """Test simple health check endpoint."""
        response = self.client.get("/health/simple")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_status_endpoint(self):
        """Test processing status endpoint."""
        response = self.client.get("/status")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("processing_count", data)
        self.assertIn("service_status", data)
        self.assertIn("currently_processing", data)

    def test_detailed_status_endpoint(self):
        """Test detailed status endpoint."""
        response = self.client.get("/status/detailed")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("configuration", data)
        self.assertIn("processing_history", data)

    def test_metrics_endpoint(self):
        """Test metrics endpoint."""
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("total_processing_count", data)
        self.assertIn("average_duration", data)
        self.assertIn("success_rate", data)

    @patch("src.app_event_driven.EventDrivenMatchProcessor._process_matches_background")
    def test_process_webhook_endpoint(self, mock_process):
        """Test webhook processing endpoint."""
        # Mock the background processing
        mock_process.return_value = None

        response = self.client.post("/process")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("message", data)

    @patch("src.app_event_driven.EventDrivenMatchProcessor._process_matches_background")
    def test_process_webhook_concurrent_requests(self, mock_process):
        """Test concurrent webhook processing requests."""

        # Mock the background processing to simulate a long-running process
        def slow_process():
            time.sleep(0.1)  # Simulate processing time

        mock_process.side_effect = slow_process

        # First request should succeed
        response1 = self.client.post("/process")
        self.assertEqual(response1.status_code, 200)

        # Second request while processing should return busy
        response2 = self.client.post("/process")
        self.assertEqual(response2.status_code, 429)

        data = response2.json()
        self.assertEqual(data["status"], "busy")


if __name__ == "__main__":
    unittest.main()
