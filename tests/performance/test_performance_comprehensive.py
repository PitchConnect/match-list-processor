"""Comprehensive performance tests for the unified match processor service."""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import psutil
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
            patch("src.core.unified_processor.FogisPhonebookSyncService"),
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

        start_time = time.time()
        changes = detector.detect_changes(matches)
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
        changes = detector.detect_changes([sample_match_data])
        end_time = time.time()

        processing_time = end_time - start_time

        # Should be very fast for basic test
        assert processing_time < 0.5  # 500ms

        print(f"Basic change detection: {processing_time:.3f}s")
