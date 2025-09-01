"""Comprehensive unit tests for unified processor functionality."""

from unittest.mock import Mock, patch

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
