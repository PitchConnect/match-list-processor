"""Comprehensive integration tests for the unified match processor service."""

from unittest.mock import Mock, patch

import pytest

from src.core.unified_processor import ProcessingResult, UnifiedMatchProcessor


class TestServiceIntegration:
    """Test integration between core service components."""

    @pytest.fixture
    def integration_processor(self, temp_data_dir):
        """Create processor for integration testing."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            return UnifiedMatchProcessor()

    @pytest.mark.integration
    def test_end_to_end_processing_flow(self, integration_processor, sample_match_data):
        """Test complete end-to-end processing flow."""
        # Setup: Create previous matches file
        current_matches = [sample_match_data]

        with (
            patch.object(
                integration_processor, "_fetch_current_matches", return_value=current_matches
            ),
            patch.object(integration_processor.change_detector, "detect_changes") as mock_detect,
            patch.object(integration_processor, "_process_changes") as mock_process,
            patch.object(integration_processor, "_trigger_downstream_services"),
            patch.object(
                integration_processor.change_detector, "save_current_matches"
            ) as mock_save,
        ):

            # Configure mock to return changes
            mock_changes = Mock()
            mock_changes.has_changes = True
            mock_changes.total_changes = 1
            mock_detect.return_value = mock_changes

            # Execute processing cycle
            result = integration_processor.run_processing_cycle()

            # Verify complete flow
            assert isinstance(result, ProcessingResult)
            assert result.processed is True
            assert result.changes.has_changes is True
            mock_process.assert_called_once()
            mock_save.assert_called_once_with(current_matches)

    @pytest.mark.integration
    def test_change_detection_integration(self, integration_processor, change_scenarios):
        """Test integration of change detection with processing."""
        for scenario_name, (_prev_match, curr_match) in change_scenarios.items():
            with (
                patch.object(
                    integration_processor, "_fetch_current_matches", return_value=[curr_match]
                ),
                patch.object(
                    integration_processor.change_detector, "detect_changes"
                ) as mock_detect,
                patch.object(integration_processor, "_process_changes"),
                patch.object(integration_processor, "_trigger_downstream_services"),
            ):

                # Configure mock based on scenario
                mock_changes = Mock()
                if scenario_name == "no_change":
                    mock_changes.has_changes = False
                else:
                    mock_changes.has_changes = True
                    mock_changes.total_changes = 1
                mock_detect.return_value = mock_changes

                result = integration_processor.run_processing_cycle()

                assert isinstance(result, ProcessingResult)
                if scenario_name == "no_change":
                    assert result.changes.has_changes is False
                    assert result.processed is False
                else:
                    assert result.changes.has_changes is True
                    assert result.processed is True

    @pytest.mark.integration
    def test_basic_integration_functionality(self, integration_processor, sample_match_data):
        """Test basic integration functionality."""
        # Test that the processor can handle basic operations
        with (
            patch.object(
                integration_processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(integration_processor.change_detector, "detect_changes") as mock_detect,
        ):

            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            result = integration_processor.run_processing_cycle()

            assert isinstance(result, ProcessingResult)
            assert result.changes.has_changes is False

    @pytest.mark.integration
    def test_comprehensive_integration_marker(self, integration_processor):
        """Test that comprehensive integration marker works."""
        # This test validates that the comprehensive integration test infrastructure is working
        assert hasattr(integration_processor, "change_detector")
        assert hasattr(integration_processor, "match_processor")
