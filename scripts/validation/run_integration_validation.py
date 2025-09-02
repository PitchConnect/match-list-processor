#!/usr/bin/env python3
"""
Comprehensive Integration and Validation Test Runner
Orchestrates all integration testing and deployment validation
Issue #54: Final Integration Testing and Production Deployment Validation
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IntegrationValidationRunner:
    """Orchestrates comprehensive integration testing and validation."""

    def __init__(self, project_root: str = None):
        self.project_root = (
            Path(project_root) if project_root else Path(__file__).parent.parent.parent
        )
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "test_suites": {},
            "overall_success": True,
            "summary": {
                "total_suites": 0,
                "passed_suites": 0,
                "failed_suites": 0,
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
            },
        }

    def run_command(
        self, command: List[str], cwd: str = None, timeout: int = 300
    ) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, and stderr."""
        try:
            if cwd is None:
                cwd = str(self.project_root)

            logger.info(f"Running command: {' '.join(command)}")

            result = subprocess.run(
                command, cwd=cwd, capture_output=True, text=True, timeout=timeout
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", f"Command failed: {e}"

    def run_integration_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """Run integration test suite."""
        logger.info("Running integration tests...")

        test_result = {
            "name": "Integration Tests",
            "success": False,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_time": 0,
            "output": "",
            "errors": [],
        }

        start_time = time.time()

        # Run integration tests with pytest
        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/",
                "-v",
                "--tb=short",
                "--no-header",
            ]
        )

        test_result["execution_time"] = time.time() - start_time
        test_result["success"] = success
        test_result["output"] = stdout

        if stderr:
            test_result["errors"].append(stderr)

        # Parse pytest output for test counts
        if stdout:
            lines = stdout.split("\n")
            for line in lines:
                if "passed" in line or "failed" in line:
                    # Try to extract test counts from pytest summary
                    if "passed" in line and "failed" not in line:
                        try:
                            passed = int(line.split()[0])
                            test_result["tests_passed"] = passed
                            test_result["tests_run"] = passed
                        except (ValueError, IndexError):
                            pass
                    elif "failed" in line:
                        try:
                            # Parse "X failed, Y passed" format
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part == "failed" and i > 0:
                                    test_result["tests_failed"] = int(parts[i - 1])
                                elif part == "passed" and i > 0:
                                    test_result["tests_passed"] = int(parts[i - 1])
                            test_result["tests_run"] = (
                                test_result["tests_failed"] + test_result["tests_passed"]
                            )
                        except (ValueError, IndexError):
                            pass

        return success, test_result

    def run_performance_tests(self) -> Tuple[bool, Dict[str, Any]]:
        """Run performance benchmark tests."""
        logger.info("Running performance benchmark tests...")

        test_result = {
            "name": "Performance Benchmarks",
            "success": False,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "execution_time": 0,
            "output": "",
            "errors": [],
        }

        start_time = time.time()

        # Run performance tests
        success, stdout, stderr = self.run_command(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/performance/",
                "-v",
                "--tb=short",
                "--no-header",
            ]
        )

        test_result["execution_time"] = time.time() - start_time
        test_result["success"] = success
        test_result["output"] = stdout

        if stderr:
            test_result["errors"].append(stderr)

        # Parse test counts (similar to integration tests)
        if stdout:
            lines = stdout.split("\n")
            for line in lines:
                if "passed" in line or "failed" in line:
                    if "passed" in line and "failed" not in line:
                        try:
                            passed = int(line.split()[0])
                            test_result["tests_passed"] = passed
                            test_result["tests_run"] = passed
                        except (ValueError, IndexError):
                            pass

        return success, test_result

    def run_deployment_validation(self) -> Tuple[bool, Dict[str, Any]]:
        """Run deployment validation."""
        logger.info("Running deployment validation...")

        test_result = {
            "name": "Deployment Validation",
            "success": False,
            "validations_run": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "execution_time": 0,
            "output": "",
            "errors": [],
        }

        start_time = time.time()

        # Run deployment validation script
        validation_script = self.project_root / "scripts" / "validation" / "validate_deployment.py"

        success, stdout, stderr = self.run_command(
            [sys.executable, str(validation_script), "--verbose"]
        )

        test_result["execution_time"] = time.time() - start_time
        test_result["success"] = success
        test_result["output"] = stdout

        if stderr:
            test_result["errors"].append(stderr)

        # Parse validation output
        if stdout:
            lines = stdout.split("\n")
            for line in lines:
                if "Total validations:" in line:
                    try:
                        test_result["validations_run"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Passed:" in line:
                    try:
                        test_result["validations_passed"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Failed:" in line:
                    try:
                        test_result["validations_failed"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass

        return success, test_result

    def run_production_validation(self) -> Tuple[bool, Dict[str, Any]]:
        """Run production deployment validation."""
        logger.info("Running production deployment validation...")

        test_result = {
            "name": "Production Validation",
            "success": False,
            "validations_run": 0,
            "validations_passed": 0,
            "validations_failed": 0,
            "execution_time": 0,
            "output": "",
            "errors": [],
        }

        start_time = time.time()

        # Run production validation script
        validation_script = (
            self.project_root / "scripts" / "validation" / "production_deployment_validator.py"
        )

        success, stdout, stderr = self.run_command(
            [sys.executable, str(validation_script), "--verbose"]
        )

        test_result["execution_time"] = time.time() - start_time
        test_result["success"] = success
        test_result["output"] = stdout

        if stderr:
            test_result["errors"].append(stderr)

        # Parse validation output (similar to deployment validation)
        if stdout:
            lines = stdout.split("\n")
            for line in lines:
                if "Total validations:" in line:
                    try:
                        test_result["validations_run"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Passed:" in line:
                    try:
                        test_result["validations_passed"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Failed:" in line:
                    try:
                        test_result["validations_failed"] = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass

        return success, test_result

    def run_all_validations(self, skip_docker: bool = False) -> Dict[str, Any]:
        """Run all integration testing and validation suites."""
        logger.info("Starting comprehensive integration and validation testing...")

        # Test suites to run
        test_suites = [
            ("integration", self.run_integration_tests),
            ("performance", self.run_performance_tests),
        ]

        # Add deployment validations if Docker is available
        if not skip_docker:
            test_suites.extend(
                [
                    ("deployment", self.run_deployment_validation),
                    ("production", self.run_production_validation),
                ]
            )

        # Run each test suite
        for suite_name, suite_func in test_suites:
            logger.info(f"Running {suite_name} test suite...")

            try:
                success, result = suite_func()
                self.results["test_suites"][suite_name] = result

                # Update summary
                self.results["summary"]["total_suites"] += 1
                if success:
                    self.results["summary"]["passed_suites"] += 1
                    logger.info(f"✅ {suite_name} test suite passed")
                else:
                    self.results["summary"]["failed_suites"] += 1
                    self.results["overall_success"] = False
                    logger.error(f"❌ {suite_name} test suite failed")

                # Update test counts
                if "tests_run" in result:
                    self.results["summary"]["total_tests"] += result["tests_run"]
                    self.results["summary"]["passed_tests"] += result["tests_passed"]
                    self.results["summary"]["failed_tests"] += result["tests_failed"]
                elif "validations_run" in result:
                    self.results["summary"]["total_tests"] += result["validations_run"]
                    self.results["summary"]["passed_tests"] += result["validations_passed"]
                    self.results["summary"]["failed_tests"] += result["validations_failed"]

            except Exception as e:
                logger.error(f"❌ {suite_name} test suite encountered an error: {e}")
                self.results["test_suites"][suite_name] = {
                    "name": suite_name,
                    "success": False,
                    "error": str(e),
                }
                self.results["summary"]["total_suites"] += 1
                self.results["summary"]["failed_suites"] += 1
                self.results["overall_success"] = False

        return self.results

    def save_results(self, output_file: str) -> None:
        """Save test results to a file."""
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2)
            logger.info(f"Test results saved to {output_file}")
        except Exception as e:
            logger.warning(f"Could not save test results: {e}")

    def print_summary(self) -> None:
        """Print a summary of test results."""
        print("\n" + "=" * 80)
        print("INTEGRATION AND VALIDATION TEST SUMMARY")
        print("=" * 80)
        print(f"Project Root: {self.results['project_root']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print()
        print(f"Test Suites: {self.results['summary']['total_suites']}")
        print(f"  Passed: {self.results['summary']['passed_suites']}")
        print(f"  Failed: {self.results['summary']['failed_suites']}")
        print()
        print(f"Total Tests/Validations: {self.results['summary']['total_tests']}")
        print(f"  Passed: {self.results['summary']['passed_tests']}")
        print(f"  Failed: {self.results['summary']['failed_tests']}")
        print()
        print(f"Overall Success: {'✅ YES' if self.results['overall_success'] else '❌ NO'}")

        if not self.results["overall_success"]:
            print("\nFailed Test Suites:")
            for suite_name, suite_result in self.results["test_suites"].items():
                if not suite_result.get("success", False):
                    print(f"  - {suite_name}: {suite_result.get('name', 'Unknown')}")
                    if "errors" in suite_result and suite_result["errors"]:
                        for error in suite_result["errors"]:
                            print(f"    Error: {error}")


def main():
    parser = argparse.ArgumentParser(
        description="Run comprehensive integration and validation tests"
    )
    parser.add_argument("--project-root", help="Project root directory")
    parser.add_argument("--output", help="Output file for test results")
    parser.add_argument(
        "--skip-docker", action="store_true", help="Skip Docker-dependent validations"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create test runner
    runner = IntegrationValidationRunner(args.project_root)

    # Run all validations
    results = runner.run_all_validations(args.skip_docker)

    # Save results if requested
    if args.output:
        runner.save_results(args.output)

    # Print summary
    runner.print_summary()

    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
