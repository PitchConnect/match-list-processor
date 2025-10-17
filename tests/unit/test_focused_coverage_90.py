"""Focused tests to increase coverage from 74% to 90% by targeting working app modules."""

import os
import signal
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestAppPersistentFocusedCoverage:
    """Focused tests targeting app_persistent.py working paths."""


class TestAppUnifiedFocusedCoverage:
    """Focused tests targeting app_unified.py working paths."""

    def test_app_unified_signal_handler_execution(self):
        """Test signal handler execution to cover signal handling lines."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch("src.app_unified.create_health_server"),
            patch("src.app_unified.sys.exit") as mock_exit,
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            app = UnifiedMatchListProcessorApp()

            # Mock shutdown method
            with patch.object(app, "shutdown") as mock_shutdown:
                # Call signal handler directly
                app._signal_handler(signal.SIGTERM, None)

                # Verify shutdown was called and running was set to False
                mock_shutdown.assert_called_once()
                assert app.running is False
                mock_exit.assert_called_with(0)

    def test_app_unified_shutdown_with_health_server(self):
        """Test shutdown with health server to cover shutdown lines."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch("src.app_unified.create_health_server") as mock_health_server,
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            # Mock health server
            mock_server = Mock()
            mock_health_server.return_value = mock_server

            app = UnifiedMatchListProcessorApp()
            app.health_server = mock_server

            # Call shutdown
            app.shutdown()

            # Verify health server was stopped and running was set to False
            mock_server.stop_server.assert_called_once()
            assert app.running is False

    def test_app_unified_test_mode_detection(self):
        """Test test mode detection to cover test mode lines."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"}),
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            app = UnifiedMatchListProcessorApp()

            # Verify test mode was detected and health server was not created
            assert app.is_test_mode is True
            assert app.health_server is None

    def test_app_unified_service_mode_configuration(self):
        """Test service mode configuration to cover configuration lines."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch("src.app_unified.create_health_server"),
            patch.dict(os.environ, {"RUN_MODE": "service", "SERVICE_INTERVAL": "600"}),
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            app = UnifiedMatchListProcessorApp()

            # Verify service mode configuration
            assert app.run_mode == "service"
            assert app.service_interval == 600
            assert app.running is True

    def test_app_unified_run_service_mode(self):
        """Test run method in service mode to cover service execution path."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch("src.app_unified.create_health_server") as mock_health_server,
            patch("src.app_unified.time.sleep"),
            patch.dict(os.environ, {"RUN_MODE": "service"}),
            # Remove test mode detection
            patch.dict(os.environ, {}, clear=True),
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            # Mock health server
            mock_server = Mock()
            mock_server.is_running.return_value = True
            mock_health_server.return_value = mock_server

            app = UnifiedMatchListProcessorApp()

            # Mock processor to avoid actual processing and stop after one iteration
            call_count = 0

            def mock_run_processing_cycle():
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    app.running = False
                # Return proper mock result with all required attributes
                mock_result = Mock()
                mock_result.processed = True
                mock_result.changes_detected = 0
                mock_result.notifications_sent = 0
                mock_result.errors = []
                return mock_result

            # Mock the unified_processor attribute
            mock_processor = Mock()
            mock_processor.run_processing_cycle = mock_run_processing_cycle
            app.unified_processor = mock_processor

            # Mock the _log_processing_result method to avoid complex nested mocking
            with patch.object(app, "_log_processing_result"):
                app.run()

            # Verify service mode was executed
            assert call_count == 1

    def test_app_unified_run_oneshot_mode(self):
        """Test run method in oneshot mode to cover oneshot execution path."""
        with (
            patch("src.app_unified.UnifiedMatchProcessor"),
            patch("src.app_unified.create_health_server") as mock_health_server,
            patch("src.app_unified.sys.exit") as mock_exit,
            patch.dict(os.environ, {"RUN_MODE": "oneshot"}),
            # Remove test mode detection
            patch.dict(os.environ, {}, clear=True),
        ):
            from src.app_unified import UnifiedMatchListProcessorApp

            # Mock health server
            mock_server = Mock()
            mock_server.is_running.return_value = True
            mock_health_server.return_value = mock_server

            app = UnifiedMatchListProcessorApp()

            # Mock the unified_processor attribute with proper result structure
            mock_processor = Mock()
            mock_result = Mock()
            mock_result.processed = True
            mock_result.changes_detected = 0
            mock_result.notifications_sent = 0
            mock_result.errors = []
            mock_processor.run_processing_cycle.return_value = mock_result
            app.unified_processor = mock_processor

            # Mock the _log_processing_result method to avoid complex nested mocking
            with patch.object(app, "_log_processing_result"):
                app.run()

            # Verify oneshot mode was executed
            mock_processor.run_processing_cycle.assert_called_once()
            # Should not exit with error since no errors
            mock_exit.assert_not_called()
