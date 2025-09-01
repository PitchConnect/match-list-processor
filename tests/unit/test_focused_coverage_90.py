"""Focused tests to increase coverage from 74% to 90% by targeting working app modules."""

import os
import signal
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
class TestAppPersistentFocusedCoverage:
    """Focused tests targeting app_persistent.py working paths."""

    def test_app_persistent_service_mode_execution(self):
        """Test service mode execution to cover service loop lines."""
        with (
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.create_health_server") as mock_health_server,
            patch("src.app_persistent.time.sleep"),
            patch.dict(os.environ, {"RUN_MODE": "service", "SERVICE_INTERVAL": "1"}),
        ):
            from src.app_persistent import PersistentMatchListProcessorApp

            # Mock health server
            mock_server = Mock()
            mock_server.is_running.return_value = True
            mock_health_server.return_value = mock_server

            app = PersistentMatchListProcessorApp()

            # Mock _process_matches to avoid actual processing and stop after one iteration
            call_count = 0

            def mock_process_matches():
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    app.running = False  # Stop after first iteration

            with patch.object(app, "_process_matches", side_effect=mock_process_matches):
                app._run_as_service()

                # Verify service loop was executed
                assert call_count == 1

    def test_app_persistent_oneshot_mode_execution(self):
        """Test oneshot mode execution to cover oneshot path."""
        with (
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.create_health_server") as mock_health_server,
            patch.dict(os.environ, {"RUN_MODE": "oneshot"}),
        ):
            from src.app_persistent import PersistentMatchListProcessorApp

            # Mock health server
            mock_server = Mock()
            mock_server.is_running.return_value = True
            mock_health_server.return_value = mock_server

            app = PersistentMatchListProcessorApp()

            # Mock _process_matches to avoid actual processing
            with patch.object(app, "_process_matches") as mock_process:
                app._run_once()

                # Verify oneshot processing was called
                mock_process.assert_called_once()

    def test_app_persistent_health_server_failure(self):
        """Test health server failure path."""
        with (
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.create_health_server") as mock_health_server,
            patch("src.app_persistent.time.sleep"),
            patch("src.app_persistent.logger") as mock_logger,
        ):
            from src.app_persistent import PersistentMatchListProcessorApp

            # Mock health server that fails to start
            mock_server = Mock()
            mock_server.is_running.return_value = False
            mock_health_server.return_value = mock_server

            app = PersistentMatchListProcessorApp()

            # Mock _run_once to avoid actual processing
            with patch.object(app, "_run_once"):
                app.run()

                # Verify warning was logged for health server failure
                mock_logger.warning.assert_called()

    def test_app_persistent_process_matches_successful_path(self):
        """Test successful process_matches execution to cover main processing lines."""
        with (
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.create_health_server"),
        ):
            from src.app_persistent import PersistentMatchListProcessorApp

            app = PersistentMatchListProcessorApp()

            # Mock successful phonebook sync
            app.phonebook_service.sync_contacts.return_value = True

            # Mock successful data loading and processing
            with (
                patch.object(
                    app, "_load_previous_matches", return_value={"123": {"matchid": "123"}}
                ),
                patch.object(
                    app, "_fetch_current_matches", return_value={"123": {"matchid": "123"}}
                ),
                patch.object(app, "_process_match_changes") as mock_process_changes,
                patch.object(app, "_save_current_matches") as mock_save,
            ):
                app._process_matches()

                # Verify all processing steps were called
                mock_process_changes.assert_called_once()
                mock_save.assert_called_once()

    def test_app_persistent_service_mode_with_sleep_interruption(self):
        """Test service mode sleep interruption to cover sleep loop lines."""
        with (
            patch("src.app_persistent.MatchDataManager"),
            patch("src.app_persistent.DockerNetworkApiClient"),
            patch("src.app_persistent.WhatsAppAvatarService"),
            patch("src.app_persistent.GoogleDriveStorageService"),
            patch("src.app_persistent.FogisPhonebookSyncService"),
            patch("src.app_persistent.MatchProcessor"),
            patch("src.app_persistent.create_health_server"),
            patch("src.app_persistent.time.sleep"),
            patch.dict(os.environ, {"SERVICE_INTERVAL": "5"}),
        ):
            from src.app_persistent import PersistentMatchListProcessorApp

            app = PersistentMatchListProcessorApp()

            # Mock _process_matches and set up interruption
            call_count = 0

            def mock_process_matches():
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    # Simulate interruption during sleep
                    app.running = False

            with patch.object(app, "_process_matches", side_effect=mock_process_matches):
                app._run_as_service()

                # Verify processing was called and interrupted
                assert call_count == 1


@pytest.mark.unit
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
