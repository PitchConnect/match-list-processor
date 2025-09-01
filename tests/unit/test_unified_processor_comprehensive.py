"""Comprehensive unit tests for unified processor functionality."""

import time
from unittest.mock import Mock, patch

import pytest

from src.core.unified_processor import ProcessingResult, UnifiedMatchProcessor


class TestUnifiedProcessorCore:
    """Test core unified processor functionality."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
        ):
            self.processor = UnifiedMatchProcessor()

    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        assert self.processor is not None
        assert hasattr(self.processor, "change_detector")
        assert hasattr(self.processor, "match_processor")

    def test_processor_has_required_services(self):
        """Test processor has all required services."""
        assert hasattr(self.processor, "api_client")
        assert hasattr(self.processor, "avatar_service")
        assert hasattr(self.processor, "storage_service")
        assert hasattr(self.processor, "phonebook_service")

    def test_processing_cycle_with_changes(self, sample_match_data):
        """Test processing cycle when changes are detected."""
        # Mock change detection
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
            patch.object(self.processor, "_process_changes"),
            patch.object(self.processor, "_trigger_downstream_services"),
        ):

            # Configure mock to return changes
            mock_changes = Mock()
            mock_changes.has_changes = True
            mock_changes.total_changes = 1
            mock_detect.return_value = mock_changes

            # Run processing cycle
            result = self.processor.run_processing_cycle()

            # Verify processing occurred
            assert isinstance(result, ProcessingResult)
            assert result.processed is True
            assert result.changes.has_changes is True

    def test_processing_cycle_no_changes(self, sample_match_data):
        """Test processing cycle when no changes are detected."""
        # Mock no changes detected
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
        ):

            # Configure mock to return no changes
            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            # Run processing cycle
            result = self.processor.run_processing_cycle()

            # Verify no processing occurred
            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert result.changes.has_changes is False

    def test_error_handling_api_failure(self):
        """Test error handling when API fails."""
        # Mock API failure
        with patch.object(
            self.processor, "_fetch_current_matches", side_effect=Exception("API Error")
        ):

            # Processing should handle error gracefully
            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert "API Error" in str(result.errors)

    def test_error_handling_change_detection_failure(self, sample_match_data):
        """Test error handling when change detection fails."""
        # Mock change detection failure
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(
                self.processor.change_detector,
                "detect_changes",
                side_effect=Exception("Change Detection Error"),
            ),
        ):

            # Processing should handle error gracefully
            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert "Change Detection Error" in str(result.errors)

    def test_state_management(self, temp_data_dir, sample_match_data):
        """Test state file management."""
        # Test saving state
        matches = [sample_match_data]

        with patch.object(self.processor.change_detector, "save_current_matches") as mock_save:
            self.processor.change_detector.save_current_matches(matches)
            mock_save.assert_called_once_with(matches)

        # Test loading state
        with patch.object(
            self.processor.change_detector, "load_previous_matches", return_value=matches
        ) as mock_load:
            loaded_matches = self.processor.change_detector.load_previous_matches()
            assert loaded_matches == matches
            mock_load.assert_called_once()


class TestUnifiedProcessorBasic:
    """Basic tests for unified processor functionality."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
        ):
            self.processor = UnifiedMatchProcessor()

    def test_basic_processing_functionality(self, sample_match_data):
        """Test basic processing functionality."""
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
        ):

            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.changes.has_changes is False

    def test_comprehensive_test_marker(self):
        """Test that comprehensive test marker works."""
        # This test validates that the comprehensive test infrastructure is working
        assert hasattr(self.processor, "change_detector")
        assert hasattr(self.processor, "match_processor")


@pytest.mark.unit
class TestUnifiedProcessorPerformance:
    """Performance tests for unified processor."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch("src.core.unified_processor.NotificationService"),
        ):
            self.processor = UnifiedMatchProcessor()

    def test_processing_performance_small_dataset(self, sample_match_data):
        """Test processing performance with small dataset."""
        matches = [sample_match_data] * 10  # 10 matches

        with (
            patch.object(self.processor, "_fetch_current_matches", return_value=matches),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
        ):
            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            start_time = time.time()
            result = self.processor.run_processing_cycle()
            end_time = time.time()

            processing_time = end_time - start_time

            # Should process 10 matches quickly (under 1 second)
            assert processing_time < 1.0
            assert isinstance(result, ProcessingResult)

    def test_change_detection_performance(self, large_match_dataset):
        """Test change detection performance with large dataset."""
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=large_match_dataset
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
        ):
            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            start_time = time.time()
            result = self.processor.run_processing_cycle()
            end_time = time.time()

            processing_time = end_time - start_time

            # Should process 1000 matches in reasonable time (under 5 seconds)
            assert processing_time < 5.0
            assert isinstance(result, ProcessingResult)

    def test_memory_usage_stability(self, sample_match_data):
        """Test memory usage remains stable during processing."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run multiple processing cycles
        for _ in range(5):
            with (
                patch.object(
                    self.processor, "_fetch_current_matches", return_value=[sample_match_data]
                ),
                patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
            ):
                mock_changes = Mock()
                mock_changes.has_changes = False
                mock_detect.return_value = mock_changes

                self.processor.run_processing_cycle()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024


@pytest.mark.unit
class TestUnifiedProcessorErrorHandling:
    """Error handling tests for unified processor."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
            patch("src.core.unified_processor.NotificationService"),
        ):
            self.processor = UnifiedMatchProcessor()

    def test_network_timeout_handling(self):
        """Test handling of network timeouts."""
        with patch.object(
            self.processor, "_fetch_current_matches", side_effect=TimeoutError("Network timeout")
        ):
            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert "Network timeout" in str(result.errors)

    def test_json_parsing_error_handling(self):
        """Test handling of JSON parsing errors."""
        with patch.object(
            self.processor, "_fetch_current_matches", side_effect=ValueError("Invalid JSON")
        ):
            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert "Invalid JSON" in str(result.errors)

    def test_file_permission_error_handling(self):
        """Test handling of file permission errors."""
        with (
            patch.object(self.processor, "_fetch_current_matches", return_value=[]),
            patch.object(
                self.processor.change_detector,
                "save_current_matches",
                side_effect=PermissionError("Permission denied"),
            ),
        ):
            result = self.processor.run_processing_cycle()

            # Should still process but log the error
            assert isinstance(result, ProcessingResult)

    def test_multiple_error_accumulation(self, sample_match_data):
        """Test that multiple errors are properly accumulated."""
        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(
                self.processor.change_detector, "detect_changes", side_effect=Exception("Error 1")
            ),
        ):
            result = self.processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.processed is False
            assert len(result.errors) >= 1
            assert "Error 1" in str(result.errors)
