"""Tests for the smart entry point module."""

import os
import sys
from unittest.mock import patch

import pytest

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.main import main  # noqa: E402


class TestMainEntryPoint:
    """Test cases for the smart entry point functionality."""

    @patch("src.main.logger")
    @patch("src.app.main")
    def test_default_mode_oneshot(self, mock_oneshot_main, mock_logger):
        """Test that default mode uses oneshot application."""
        # Remove RUN_MODE from environment
        with patch.dict(os.environ, {}, clear=True):
            main()

        mock_logger.info.assert_any_call("Match List Processor starting in oneshot mode...")
        mock_logger.info.assert_any_call("Using oneshot mode (src.app)")
        mock_oneshot_main.assert_called_once()

    @patch("src.main.logger")
    @patch("src.app_persistent.main")
    def test_service_mode(self, mock_persistent_main, mock_logger):
        """Test that service mode uses persistent application."""
        with patch.dict(os.environ, {"RUN_MODE": "service"}):
            main()

        mock_logger.info.assert_any_call("Match List Processor starting in service mode...")
        mock_logger.info.assert_any_call("Using persistent service mode (src.app_persistent)")
        mock_persistent_main.assert_called_once()

    @patch("src.main.logger")
    @patch("src.app.main")
    def test_explicit_oneshot_mode(self, mock_oneshot_main, mock_logger):
        """Test that explicit oneshot mode works correctly."""
        with patch.dict(os.environ, {"RUN_MODE": "oneshot"}):
            main()

        mock_logger.info.assert_any_call("Match List Processor starting in oneshot mode...")
        mock_logger.info.assert_any_call("Using oneshot mode (src.app)")
        mock_oneshot_main.assert_called_once()

    @patch("src.main.logger")
    @patch("src.app.main")
    def test_unknown_mode_defaults_to_oneshot(self, mock_oneshot_main, mock_logger):
        """Test that unknown RUN_MODE defaults to oneshot."""
        with patch.dict(os.environ, {"RUN_MODE": "unknown"}):
            main()

        mock_logger.warning.assert_any_call(
            "Unknown RUN_MODE 'unknown', defaulting to oneshot mode"
        )
        mock_oneshot_main.assert_called_once()

    @patch("src.main.logger")
    @patch("src.app.main", side_effect=ImportError("Test import error"))
    def test_oneshot_import_error_exits(self, mock_oneshot_main, mock_logger):
        """Test that import error in oneshot mode causes exit."""
        with patch.dict(os.environ, {"RUN_MODE": "oneshot"}):
            with pytest.raises(SystemExit):
                main()

        mock_logger.error.assert_any_call("Failed to import oneshot module: Test import error")

    @patch("src.main.logger")
    @patch("src.app_persistent.main", side_effect=ImportError("Test persistent import error"))
    @patch("src.app.main")
    def test_persistent_import_error_falls_back_to_oneshot(
        self, mock_oneshot_main, mock_persistent_main, mock_logger
    ):
        """Test that import error in persistent mode falls back to oneshot."""
        with patch.dict(os.environ, {"RUN_MODE": "service"}):
            main()

        mock_logger.error.assert_any_call(
            "Failed to import persistent service module: Test persistent import error"
        )
        mock_logger.error.assert_any_call("Falling back to oneshot mode")
        mock_oneshot_main.assert_called_once()

    @patch("src.main.logger")
    @patch("src.app.main")
    def test_case_insensitive_mode(self, mock_oneshot_main, mock_logger):
        """Test that RUN_MODE is case insensitive."""
        with patch.dict(os.environ, {"RUN_MODE": "SERVICE"}):
            # Mock the persistent import to test the case conversion
            with patch("src.app_persistent.main") as mock_persistent_main:
                main()

            mock_logger.info.assert_any_call("Match List Processor starting in service mode...")
            mock_persistent_main.assert_called_once()
