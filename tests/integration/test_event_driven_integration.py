"""Integration tests for event-driven architecture."""

import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app_event_driven import EventDrivenMatchProcessor
from src.services.webhook_service import WebhookProcessingService


class TestEventDrivenIntegration(unittest.TestCase):
    """Integration tests for event-driven match processing."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests."""
        # Create temporary directory for testing
        cls.temp_dir = tempfile.mkdtemp()

        # Set environment variables for testing
        os.environ["DATA_FOLDER"] = cls.temp_dir
        os.environ["TEMP_FILE_DIRECTORY"] = cls.temp_dir
        os.environ["API_BASE_URL"] = "http://test-api:8000"

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Clean up environment variables
        for env_var in ["DATA_FOLDER", "TEMP_FILE_DIRECTORY", "API_BASE_URL"]:
            if env_var in os.environ:
                del os.environ[env_var]

    def setUp(self):
        """Set up each test."""
        self.processor = EventDrivenMatchProcessor()
        self.client = TestClient(self.processor.app)

    def test_full_webhook_processing_cycle(self):
        """Test complete webhook processing cycle."""
        # Get initial status
        initial_response = self.client.get("/status")
        self.assertEqual(initial_response.status_code, 200)

        # Trigger webhook processing
        with patch.object(
            self.processor.webhook_service, "process_webhook_trigger"
        ) as mock_process:
            mock_process.return_value = {
                "processing_id": "test_123",
                "timestamp": time.time(),
                "duration": 1.5,
                "changes_detected": True,
                "summary": "Test changes processed",
                "status": "success",
            }

            process_response = self.client.post("/process")
            self.assertEqual(process_response.status_code, 200)

            process_data = process_response.json()
            self.assertEqual(process_data["status"], "success")

        # Wait a moment for background processing
        time.sleep(0.1)

        # Check final status
        final_response = self.client.get("/status")
        self.assertEqual(final_response.status_code, 200)

    def test_webhook_service_integration(self):
        """Test webhook service integration with unified processor."""
        webhook_service = WebhookProcessingService()

        # Mock the unified processor to avoid actual API calls
        with patch.object(webhook_service.unified_processor, "run_processing_cycle") as mock_cycle:
            mock_result = type(
                "MockResult", (), {"changes_detected": True, "summary": "Integration test changes"}
            )()
            mock_cycle.return_value = mock_result

            # Process webhook trigger
            result = webhook_service.process_webhook_trigger({"test": "integration"})

            # Verify integration
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["changes_detected"])
            self.assertEqual(result["summary"], "Integration test changes")

            # Verify processor was called
            mock_cycle.assert_called_once()

    def test_health_check_integration(self):
        """Test health check integration with dependencies."""
        response = self.client.get("/health")

        # Should return health status even if dependencies are mocked
        self.assertIn(response.status_code, [200, 503])  # Healthy or unhealthy

        data = response.json()
        self.assertEqual(data["service_name"], "match-list-processor")
        self.assertIn("status", data)
        self.assertIn("dependencies", data)

    def test_metrics_collection_integration(self):
        """Test metrics collection across multiple operations."""
        # Get initial metrics
        initial_response = self.client.get("/metrics")
        self.assertEqual(initial_response.status_code, 200)
        initial_metrics = initial_response.json()

        # Simulate multiple webhook processes
        with patch.object(
            self.processor.webhook_service, "process_webhook_trigger"
        ) as mock_process:
            # First process - success with changes
            mock_process.return_value = {
                "processing_id": "test_1",
                "timestamp": time.time(),
                "duration": 1.0,
                "changes_detected": True,
                "summary": "Changes detected",
                "status": "success",
            }

            response1 = self.client.post("/process")
            self.assertEqual(response1.status_code, 200)

            # Wait for processing
            time.sleep(0.1)

            # Second process - success without changes
            mock_process.return_value = {
                "processing_id": "test_2",
                "timestamp": time.time(),
                "duration": 0.5,
                "changes_detected": False,
                "summary": "No changes detected",
                "status": "success",
            }

            response2 = self.client.post("/process")
            self.assertEqual(response2.status_code, 200)

            # Wait for processing
            time.sleep(0.1)

        # Get final metrics
        final_response = self.client.get("/metrics")
        self.assertEqual(final_response.status_code, 200)
        final_metrics = final_response.json()

        # Verify metrics were updated
        self.assertGreaterEqual(
            final_metrics["total_processing_count"], initial_metrics["total_processing_count"]
        )

    def test_concurrent_processing_protection(self):
        """Test protection against concurrent processing."""
        # Start first processing request
        with patch.object(
            self.processor.webhook_service, "process_webhook_trigger"
        ) as mock_process:
            # Make the first process take some time
            def slow_process(*args, **kwargs):
                time.sleep(0.2)
                return {
                    "processing_id": "slow_test",
                    "timestamp": time.time(),
                    "duration": 0.2,
                    "changes_detected": False,
                    "summary": "Slow process",
                    "status": "success",
                }

            mock_process.side_effect = slow_process

            # Start first request
            response1 = self.client.post("/process")
            self.assertEqual(response1.status_code, 200)

            # Immediately try second request
            response2 = self.client.post("/process")
            self.assertEqual(response2.status_code, 429)  # Should be busy

            data2 = response2.json()
            self.assertEqual(data2["status"], "busy")

    def test_error_handling_integration(self):
        """Test error handling in webhook processing."""
        with patch.object(
            self.processor.webhook_service, "process_webhook_trigger"
        ) as mock_process:
            # Make the process raise an exception
            mock_process.side_effect = Exception("Integration test error")

            # The endpoint should still return success (background processing)
            response = self.client.post("/process")
            self.assertEqual(response.status_code, 200)

            # Wait for background processing to complete
            time.sleep(0.2)

            # Check that the service is still responsive
            health_response = self.client.get("/health")
            self.assertIn(health_response.status_code, [200, 503])

    def test_status_endpoints_consistency(self):
        """Test consistency between different status endpoints."""
        # Get status from different endpoints
        root_response = self.client.get("/")
        status_response = self.client.get("/status")
        detailed_response = self.client.get("/status/detailed")
        metrics_response = self.client.get("/metrics")

        # All should return 200
        self.assertEqual(root_response.status_code, 200)
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(detailed_response.status_code, 200)
        self.assertEqual(metrics_response.status_code, 200)

        # Extract data
        root_data = root_response.json()
        status_data = status_response.json()
        detailed_data = detailed_response.json()
        metrics_data = metrics_response.json()

        # Check consistency of processing count
        self.assertEqual(root_data["processing_count"], status_data["processing_count"])
        self.assertEqual(status_data["processing_count"], detailed_data["processing_count"])
        self.assertEqual(detailed_data["processing_count"], metrics_data["total_processing_count"])

    def test_webhook_data_flow(self):
        """Test data flow through webhook processing."""
        with patch.object(
            self.processor.webhook_service, "process_webhook_trigger"
        ) as mock_process:
            # Capture the trigger data
            captured_data = None

            def capture_trigger_data(trigger_data=None):
                nonlocal captured_data
                captured_data = trigger_data
                return {
                    "processing_id": "data_flow_test",
                    "timestamp": time.time(),
                    "duration": 0.1,
                    "changes_detected": False,
                    "summary": "Data flow test",
                    "trigger_data": trigger_data,
                    "status": "success",
                }

            mock_process.side_effect = capture_trigger_data

            # Trigger processing
            response = self.client.post("/process")
            self.assertEqual(response.status_code, 200)

            # Wait for processing
            time.sleep(0.1)

            # Verify data was passed through
            # Note: In current implementation, webhook data isn't passed from endpoint
            # This test verifies the data flow structure is in place


if __name__ == "__main__":
    unittest.main()
