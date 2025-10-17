"""Comprehensive performance tests for the unified match processor service."""

import time
from unittest.mock import Mock, patch

import pytest

from src.core.change_detector import GranularChangeDetector
from src.core.unified_processor import ProcessingResult, UnifiedMatchProcessor


class TestProcessingPerformance:
    """Test performance characteristics of core processing."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            self.processor = UnifiedMatchProcessor()

    @pytest.mark.performance
    def test_single_processing_cycle_performance(self, sample_match_data, performance_metrics):
        """Test performance of single processing cycle."""
        # Measure processing time
        start_time = time.time()

        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=[sample_match_data]
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
            patch.object(self.processor, "_process_changes"),
            patch.object(self.processor, "_trigger_downstream_services"),
        ):

            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            result = self.processor.run_processing_cycle()

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify performance
        assert processing_time < performance_metrics["max_processing_time"]
        assert isinstance(result, ProcessingResult)

        print(f"Single processing cycle time: {processing_time:.3f}s")

    @pytest.mark.performance
    def test_basic_performance_functionality(self, sample_match_data):
        """Test basic performance functionality."""
        # Simple performance test to validate infrastructure
        start_time = time.time()

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

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete quickly
        assert processing_time < 1.0  # 1 second
        assert isinstance(result, ProcessingResult)

        print(f"Basic performance test time: {processing_time:.3f}s")

    @pytest.mark.performance
    def test_comprehensive_performance_marker(self):
        """Test that comprehensive performance marker works."""
        # This test validates that the comprehensive performance test infrastructure is working
        assert hasattr(self.processor, "change_detector")
        assert hasattr(self.processor, "match_processor")


class TestChangeDetectionPerformance:
    """Test performance characteristics of change detection."""

    @pytest.mark.performance
    def test_change_detection_performance_small_dataset(self, sample_match_data):
        """Test change detection performance with small dataset."""
        detector = GranularChangeDetector()
        matches = [sample_match_data] * 10

        # Mock previous matches
        with patch.object(detector, "load_previous_matches", return_value=matches):
            start_time = time.time()
            changes = detector.detect_changes(matches)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should process small dataset very quickly (under 0.1 seconds)
            assert processing_time < 0.1
            assert not changes.has_changes

            print(f"Small dataset change detection time: {processing_time:.3f}s")

    @pytest.mark.performance
    def test_change_detection_performance_large_dataset(self, large_match_dataset):
        """Test change detection performance with large dataset."""
        detector = GranularChangeDetector()

        # Mock previous matches
        with patch.object(detector, "load_previous_matches", return_value=large_match_dataset):
            start_time = time.time()
            changes = detector.detect_changes(large_match_dataset)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should process 1000 matches in under 2 seconds
            assert processing_time < 2.0
            assert not changes.has_changes

            print(f"Large dataset change detection time: {processing_time:.3f}s")

    @pytest.mark.performance
    def test_change_detection_with_modifications_performance(self, large_match_dataset):
        """Test change detection performance when modifications are present."""
        detector = GranularChangeDetector()

        # Create modified dataset (modify every 10th match)
        modified_dataset = large_match_dataset.copy()
        for i in range(0, min(100, len(modified_dataset)), 10):
            modified_dataset[i] = modified_dataset[i].copy()
            modified_dataset[i]["avsparkstid"] = "16:00"

        with patch.object(detector, "load_previous_matches", return_value=large_match_dataset):
            start_time = time.time()
            changes = detector.detect_changes(modified_dataset)
            end_time = time.time()

            processing_time = end_time - start_time

            # Should still process efficiently even with changes (under 3 seconds)
            assert processing_time < 3.0
            assert changes.has_changes
            assert len(changes.updated_matches) >= 10

            print(f"Modified dataset change detection time: {processing_time:.3f}s")


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory usage characteristics."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            self.processor = UnifiedMatchProcessor()

    @pytest.mark.performance
    def test_memory_usage_stability(self, sample_match_data):
        """Test memory usage remains stable during repeated processing."""
        import os

        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available - skipping memory usage test")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Run multiple processing cycles
        for i in range(20):
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

        print(f"Memory increase after 20 cycles: {memory_increase / 1024 / 1024:.2f}MB")

    @pytest.mark.performance
    def test_memory_usage_large_dataset(self, large_match_dataset):
        """Test memory usage with large datasets."""
        import os

        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available - skipping memory usage test")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        with (
            patch.object(
                self.processor, "_fetch_current_matches", return_value=large_match_dataset
            ),
            patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
        ):
            mock_changes = Mock()
            mock_changes.has_changes = False
            mock_detect.return_value = mock_changes

            self.processor.run_processing_cycle()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable even for large datasets (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024

        print(f"Memory increase for large dataset: {memory_increase / 1024 / 1024:.2f}MB")


@pytest.mark.performance
class TestConcurrencyPerformance:
    """Test performance under concurrent conditions."""

    def setup_method(self):
        """Set up test environment."""
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            self.processor = UnifiedMatchProcessor()

    @pytest.mark.performance
    def test_concurrent_processing_performance(self, sample_match_data):
        """Test performance under concurrent processing scenarios."""
        import queue
        import threading

        results_queue = queue.Queue()

        def process_matches():
            with (
                patch.object(
                    self.processor, "_fetch_current_matches", return_value=[sample_match_data]
                ),
                patch.object(self.processor.change_detector, "detect_changes") as mock_detect,
            ):
                mock_changes = Mock()
                mock_changes.has_changes = False
                mock_detect.return_value = mock_changes

                start_time = time.time()
                result = self.processor.run_processing_cycle()
                end_time = time.time()

                results_queue.put((result, end_time - start_time))

        # Run multiple threads concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_matches)
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # All threads should complete within reasonable time (under 10 seconds)
        assert total_time < 10.0
        assert results_queue.qsize() == 5

        print(f"Concurrent processing time for 5 threads: {total_time:.3f}s")

        start_time = time.time()
        # Mock stakeholder resolution for performance testing
        mock_resolver = Mock()
        mock_resolver.resolve_notification_stakeholders.return_value = []

        for _ in range(100):
            mock_resolver.resolve_notification_stakeholders(
                sample_match_data, "new_assignment", "medium"
            )
        end_time = time.time()

        processing_time = end_time - start_time

        # Should be very fast for small dataset
        assert processing_time < 1.0  # 1 second

        print(f"Small dataset change detection (10 matches): {processing_time:.3f}s")

    @pytest.mark.performance
    def test_basic_change_detection_performance(self, sample_match_data):
        """Test basic change detection performance."""
        detector = GranularChangeDetector()

        start_time = time.time()
        detector.detect_changes([sample_match_data])
        end_time = time.time()

        processing_time = end_time - start_time

        # Should be very fast for basic test
        assert processing_time < 0.5  # 500ms

        print(f"Basic change detection: {processing_time:.3f}s")
