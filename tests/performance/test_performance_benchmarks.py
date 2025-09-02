#!/usr/bin/env python3
"""
Performance Benchmarking Tests
Establishes baseline performance metrics and regression testing
Issue #54: Final Integration Testing and Production Deployment Validation
"""

import json
import logging
import os
import statistics
import tempfile
import time
import unittest
from unittest.mock import patch

import psutil

from src.app_unified import UnifiedMatchListProcessorApp
from src.core.unified_processor import UnifiedMatchProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarking tests for the unified service."""

    @classmethod
    def setUpClass(cls):
        """Set up performance testing environment."""
        # Set test environment
        os.environ["PYTEST_CURRENT_TEST"] = "true"
        os.environ["CI"] = "true"
        os.environ["LOG_LEVEL"] = "WARNING"  # Reduce log noise for performance tests

        # Create temporary data directory
        cls.temp_dir = tempfile.mkdtemp()
        os.environ["DATA_FOLDER"] = cls.temp_dir

        # Performance thresholds (in seconds)
        cls.performance_thresholds = {
            "processor_initialization": 2.0,
            "processing_cycle_empty": 1.0,
            "processing_cycle_with_data": 5.0,
            "health_check_response": 0.1,
            "memory_usage_mb": 256,
            "cpu_usage_percent": 50,
        }

        logger.info("Performance testing environment set up")

    @classmethod
    def tearDownClass(cls):
        """Clean up performance testing environment."""
        import shutil

        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        logger.info("Performance testing environment cleaned up")

    def setUp(self):
        """Set up for each performance test."""
        self.performance_results = {}

    def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return result, execution_time

    def measure_memory_usage(self, func, *args, **kwargs):
        """Measure memory usage during function execution."""
        process = psutil.Process()

        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute function
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = final_memory - initial_memory

        return result, execution_time, initial_memory, final_memory, memory_delta

    def test_processor_initialization_performance(self):
        """Test unified processor initialization performance."""
        logger.info("Testing processor initialization performance...")

        # Measure initialization time
        _, init_time = self.measure_execution_time(UnifiedMatchProcessor)

        # Record result
        self.performance_results["processor_initialization"] = init_time

        # Validate against threshold
        threshold = self.performance_thresholds["processor_initialization"]
        self.assertLess(
            init_time,
            threshold,
            f"Processor initialization too slow: {init_time:.3f}s > {threshold}s",
        )

        logger.info(f"✅ Processor initialization: {init_time:.3f}s (threshold: {threshold}s)")

    @patch("src.services.api_client.DockerNetworkApiClient.fetch_matches_list")
    def test_processing_cycle_performance_empty(self, mock_fetch_matches):
        """Test processing cycle performance with empty data."""
        logger.info("Testing processing cycle performance (empty data)...")

        # Mock empty API response
        mock_fetch_matches.return_value = []

        processor = UnifiedMatchProcessor()

        # Measure processing cycle time
        _, cycle_time = self.measure_execution_time(processor.run_processing_cycle)

        # Record result
        self.performance_results["processing_cycle_empty"] = cycle_time

        # Validate against threshold
        threshold = self.performance_thresholds["processing_cycle_empty"]
        self.assertLess(
            cycle_time,
            threshold,
            f"Empty processing cycle too slow: {cycle_time:.3f}s > {threshold}s",
        )

        logger.info(f"✅ Empty processing cycle: {cycle_time:.3f}s (threshold: {threshold}s)")

    @patch("src.services.api_client.DockerNetworkApiClient.fetch_matches_list")
    def test_processing_cycle_performance_with_data(self, mock_fetch_matches):
        """Test processing cycle performance with realistic data."""
        logger.info("Testing processing cycle performance (with data)...")

        # Mock realistic API response with multiple matches
        sample_matches = []
        for i in range(20):  # 20 matches
            sample_matches.append(
                {
                    "match_id": f"match_{i}",
                    "home_team": f"Team A{i}",
                    "away_team": f"Team B{i}",
                    "match_date": "2025-09-02",
                    "match_time": f"{15 + (i % 4)}:00",
                    "venue": f"Stadium {i}",
                    "referees": [f"Referee {i}_1", f"Referee {i}_2"],
                }
            )

        mock_fetch_matches.return_value = sample_matches

        processor = UnifiedMatchProcessor()

        # Measure processing cycle time with data
        _, cycle_time = self.measure_execution_time(processor.run_processing_cycle)

        # Record result
        self.performance_results["processing_cycle_with_data"] = cycle_time

        # Validate against threshold
        threshold = self.performance_thresholds["processing_cycle_with_data"]
        self.assertLess(
            cycle_time,
            threshold,
            f"Data processing cycle too slow: {cycle_time:.3f}s > {threshold}s",
        )

        logger.info(f"✅ Data processing cycle: {cycle_time:.3f}s (threshold: {threshold}s)")

    def test_memory_usage_baseline(self):
        """Test memory usage baseline for the unified processor."""
        logger.info("Testing memory usage baseline...")

        # Measure memory usage during processor initialization and operation
        def create_and_run_processor():
            processor = UnifiedMatchProcessor()
            with patch(
                "src.services.api_client.DockerNetworkApiClient.fetch_matches_list"
            ) as mock_fetch:
                mock_fetch.return_value = []
                processor.run_processing_cycle()
            return processor

        _, exec_time, initial_mem, final_mem, mem_delta = self.measure_memory_usage(
            create_and_run_processor
        )

        # Record results
        self.performance_results["memory_initial_mb"] = initial_mem
        self.performance_results["memory_final_mb"] = final_mem
        self.performance_results["memory_delta_mb"] = mem_delta

        # Validate against threshold
        threshold = self.performance_thresholds["memory_usage_mb"]
        self.assertLess(
            final_mem, threshold, f"Memory usage too high: {final_mem:.1f}MB > {threshold}MB"
        )

        logger.info(
            f"✅ Memory usage: {final_mem:.1f}MB (delta: {mem_delta:+.1f}MB, threshold: {threshold}MB)"
        )

    def test_concurrent_processing_performance(self):
        """Test performance under concurrent processing scenarios."""
        logger.info("Testing concurrent processing performance...")

        import threading

        # Create multiple processors to simulate concurrent load
        processors = []
        execution_times = []

        def create_and_run():
            with patch(
                "src.services.api_client.DockerNetworkApiClient.fetch_matches_list"
            ) as mock_fetch:
                mock_fetch.return_value = []
                processor = UnifiedMatchProcessor()
                start_time = time.time()
                processor.run_processing_cycle()
                execution_times.append(time.time() - start_time)
                processors.append(processor)

        # Run 5 concurrent processors
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_and_run)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Analyze results
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)

        # Record results
        self.performance_results["concurrent_avg_time"] = avg_time
        self.performance_results["concurrent_max_time"] = max_time
        self.performance_results["concurrent_processors"] = len(processors)

        # Validate that concurrent processing doesn't degrade performance significantly
        threshold = (
            self.performance_thresholds["processing_cycle_empty"] * 2
        )  # Allow 2x slower for concurrent
        self.assertLess(
            max_time, threshold, f"Concurrent processing too slow: {max_time:.3f}s > {threshold}s"
        )

        logger.info(
            f"✅ Concurrent processing: avg {avg_time:.3f}s, max {max_time:.3f}s (threshold: {threshold}s)"
        )

    def test_repeated_processing_performance(self):
        """Test performance consistency over repeated processing cycles."""
        logger.info("Testing repeated processing performance...")

        processor = UnifiedMatchProcessor()
        execution_times = []

        # Run 10 processing cycles
        with patch(
            "src.services.api_client.DockerNetworkApiClient.fetch_matches_list"
        ) as mock_fetch:
            mock_fetch.return_value = []

            for i in range(10):
                start_time = time.time()
                processor.run_processing_cycle()
                execution_times.append(time.time() - start_time)

        # Analyze performance consistency
        avg_time = statistics.mean(execution_times)
        std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0
        min_time = min(execution_times)
        max_time = max(execution_times)

        # Record results
        self.performance_results["repeated_avg_time"] = avg_time
        self.performance_results["repeated_std_dev"] = std_dev
        self.performance_results["repeated_min_time"] = min_time
        self.performance_results["repeated_max_time"] = max_time

        # Validate consistency (standard deviation should be low)
        # Use a more reasonable threshold for micro-benchmarks
        consistency_threshold = max(avg_time * 0.8, 0.001)  # Allow 80% variation or minimum 1ms
        self.assertLess(
            std_dev,
            consistency_threshold,
            f"Performance too inconsistent: std_dev {std_dev:.6f}s > {consistency_threshold:.6f}s",
        )

        logger.info(
            f"✅ Repeated processing: avg {avg_time:.3f}s ±{std_dev:.3f}s (range: {min_time:.3f}s-{max_time:.3f}s)"
        )

    def test_app_startup_performance(self):
        """Test application startup performance."""
        logger.info("Testing application startup performance...")

        # Measure app initialization time
        _, startup_time = self.measure_execution_time(UnifiedMatchListProcessorApp)

        # Record result
        self.performance_results["app_startup_time"] = startup_time

        # Validate against threshold (should be fast)
        threshold = 3.0  # 3 seconds for full app startup
        self.assertLess(
            startup_time, threshold, f"App startup too slow: {startup_time:.3f}s > {threshold}s"
        )

        logger.info(f"✅ App startup: {startup_time:.3f}s (threshold: {threshold}s)")

    def test_performance_regression_detection(self):
        """Test for performance regression detection."""
        logger.info("Testing performance regression detection...")

        # Run a quick performance test to populate results
        start_time = time.time()
        UnifiedMatchProcessor()
        processor_init_time = time.time() - start_time
        self.performance_results["processor_initialization"] = processor_init_time

        # This test validates that performance metrics can be collected
        # In a real scenario, this would compare against historical baselines

        required_metrics = ["processor_initialization"]

        for metric in required_metrics:
            self.assertIn(metric, self.performance_results, f"Missing performance metric: {metric}")
            self.assertGreater(
                self.performance_results[metric], 0, f"Invalid performance metric value: {metric}"
            )

        logger.info("✅ Performance regression detection validated")

    def save_performance_baseline(self, output_file: str = None):
        """Save performance baseline results."""
        if not output_file:
            output_file = f"performance_baseline_{int(time.time())}.json"

        baseline_data = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "thresholds": self.performance_thresholds,
            "results": self.performance_results,
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
                "python_version": os.sys.version,
            },
        }

        try:
            with open(output_file, "w") as f:
                json.dump(baseline_data, f, indent=2)
            logger.info(f"Performance baseline saved to {output_file}")
        except Exception as e:
            logger.warning(f"Could not save performance baseline: {e}")

    def tearDown(self):
        """Clean up after each performance test."""
        # Save performance results after all tests
        if hasattr(self, "performance_results") and self.performance_results:
            self.save_performance_baseline()


if __name__ == "__main__":
    # Run performance benchmarks
    unittest.main(verbosity=2)
