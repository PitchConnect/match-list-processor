#!/usr/bin/env python3
"""
Production Deployment Validation Script
Validates production deployment of the unified match-list-processor service
Issue #54: Final Integration Testing and Production Deployment Validation
"""

import argparse
import json
import logging
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ProductionDeploymentValidator:
    """Validates production deployment of the unified service."""

    def __init__(self, service_url: str = "http://localhost:8000", timeout: int = 30):
        self.service_url = service_url
        self.timeout = timeout
        self.validation_results = []
        self.start_time = time.time()

        # Expected service dependencies
        self.expected_dependencies = [
            "fogis_api",
            "whatsapp_avatar",
            "google_drive",
            "phonebook_sync",
        ]

        # Performance thresholds
        self.performance_thresholds = {
            "health_check_response_time": 2.0,  # seconds
            "processing_cycle_time": 30.0,  # seconds
            "memory_usage_mb": 512,  # MB
            "cpu_usage_percent": 80,  # %
        }

    def validate_service_startup(self) -> Tuple[bool, str]:
        """Validate that the service starts up correctly."""
        logger.info("Validating service startup...")

        try:
            # Wait for service to be ready
            max_wait = 60  # seconds
            wait_interval = 2

            for attempt in range(max_wait // wait_interval):
                try:
                    response = requests.get(f"{self.service_url}/health/simple", timeout=5)
                    if response.status_code == 200:
                        startup_time = time.time() - self.start_time
                        return True, f"Service started successfully in {startup_time:.2f}s"
                except requests.exceptions.RequestException:
                    pass

                time.sleep(wait_interval)
                logger.info(
                    f"Waiting for service startup... (attempt {attempt + 1}/{max_wait // wait_interval})"
                )

            return False, f"Service failed to start within {max_wait}s"

        except Exception as e:
            return False, f"Service startup validation failed: {e}"

    def validate_health_endpoints(self) -> Tuple[bool, str]:
        """Validate health check endpoints."""
        logger.info("Validating health endpoints...")

        try:
            # Test simple health endpoint
            start_time = time.time()
            response = requests.get(f"{self.service_url}/health/simple", timeout=self.timeout)
            response_time = time.time() - start_time

            if response.status_code != 200:
                return False, f"Simple health check failed with status {response.status_code}"

            if response_time > self.performance_thresholds["health_check_response_time"]:
                return (
                    False,
                    f"Health check too slow: {response_time:.2f}s > {self.performance_thresholds['health_check_response_time']}s",
                )

            simple_data = response.json()
            if simple_data.get("status") != "healthy":
                return False, f"Simple health check reports unhealthy: {simple_data}"

            # Test detailed health endpoint
            response = requests.get(f"{self.service_url}/health", timeout=self.timeout)
            if response.status_code not in [200, 503]:  # 503 is acceptable if dependencies are down
                return False, f"Detailed health check failed with status {response.status_code}"

            detailed_data = response.json()
            if "dependencies" not in detailed_data:
                return False, "Detailed health check missing dependencies information"

            return True, f"Health endpoints validated (response time: {response_time:.2f}s)"

        except Exception as e:
            return False, f"Health endpoint validation failed: {e}"

    def validate_service_dependencies(self) -> Tuple[bool, str]:
        """Validate external service dependencies."""
        logger.info("Validating service dependencies...")

        try:
            response = requests.get(f"{self.service_url}/health", timeout=self.timeout)
            if response.status_code not in [200, 503]:
                return False, f"Cannot get dependency status: HTTP {response.status_code}"

            health_data = response.json()
            dependencies = health_data.get("dependencies", {})

            # Check that all expected dependencies are present
            missing_deps = []
            unhealthy_deps = []

            for dep in self.expected_dependencies:
                if dep not in dependencies:
                    missing_deps.append(dep)
                elif dependencies[dep] != "healthy":
                    unhealthy_deps.append(f"{dep}: {dependencies[dep]}")

            if missing_deps:
                return False, f"Missing dependencies: {', '.join(missing_deps)}"

            if unhealthy_deps:
                # This is a warning, not a failure - service can run with some deps down
                logger.warning(f"Unhealthy dependencies: {', '.join(unhealthy_deps)}")

            return True, f"Dependencies validated ({len(dependencies)} checked)"

        except Exception as e:
            return False, f"Dependency validation failed: {e}"

    def validate_docker_deployment(self) -> Tuple[bool, str]:
        """Validate Docker deployment configuration."""
        logger.info("Validating Docker deployment...")

        try:
            # Check if service container is running
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    "name=process-matches-service",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Docker ps command failed: {result.stderr}"

            if not result.stdout.strip():
                return False, "process-matches-service container not found"

            if "Up" not in result.stdout:
                return False, f"Container not running: {result.stdout.strip()}"

            # Check container health
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "process-matches-service",
                    "--format",
                    "{{.State.Health.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                health_status = result.stdout.strip()
                if health_status not in ["healthy", "none"]:  # "none" means no healthcheck defined
                    return False, f"Container health check failed: {health_status}"

            return True, "Docker deployment validated"

        except subprocess.TimeoutExpired:
            return False, "Docker command timed out"
        except Exception as e:
            return False, f"Docker deployment validation failed: {e}"

    def validate_network_connectivity(self) -> Tuple[bool, str]:
        """Validate network connectivity and port accessibility."""
        logger.info("Validating network connectivity...")

        try:
            # Test main service port
            response = requests.get(f"{self.service_url}/health/simple", timeout=5)
            if response.status_code != 200:
                return False, f"Service not accessible on {self.service_url}"

            # Test that service responds to different endpoints
            endpoints_to_test = ["/health/simple", "/health"]

            for endpoint in endpoints_to_test:
                try:
                    response = requests.get(f"{self.service_url}{endpoint}", timeout=5)
                    if response.status_code not in [200, 503]:
                        return False, f"Endpoint {endpoint} returned {response.status_code}"
                except requests.exceptions.RequestException as e:
                    return False, f"Endpoint {endpoint} not accessible: {e}"

            return True, "Network connectivity validated"

        except Exception as e:
            return False, f"Network connectivity validation failed: {e}"

    def validate_configuration(self) -> Tuple[bool, str]:
        """Validate service configuration."""
        logger.info("Validating service configuration...")

        try:
            # Get service status to check configuration
            response = requests.get(f"{self.service_url}/health", timeout=self.timeout)
            if response.status_code not in [200, 503]:
                return False, f"Cannot get service configuration: HTTP {response.status_code}"

            health_data = response.json()

            # Check required configuration fields
            required_fields = ["service_name", "status", "timestamp"]
            for field in required_fields:
                if field not in health_data:
                    return False, f"Missing required field in health response: {field}"

            # Validate service name
            if health_data.get("service_name") != "match-list-processor":
                return False, f"Unexpected service name: {health_data.get('service_name')}"

            return True, "Service configuration validated"

        except Exception as e:
            return False, f"Configuration validation failed: {e}"

    def validate_performance_baseline(self) -> Tuple[bool, str]:
        """Validate performance meets baseline requirements."""
        logger.info("Validating performance baseline...")

        try:
            # Test health endpoint response time
            start_time = time.time()
            response = requests.get(f"{self.service_url}/health/simple", timeout=self.timeout)
            response_time = time.time() - start_time

            if response.status_code != 200:
                return False, f"Health check failed for performance test: {response.status_code}"

            if response_time > self.performance_thresholds["health_check_response_time"]:
                return (
                    False,
                    f"Health check too slow: {response_time:.2f}s > {self.performance_thresholds['health_check_response_time']}s",
                )

            # Test multiple requests to check consistency
            response_times = []
            for i in range(5):
                start_time = time.time()
                response = requests.get(f"{self.service_url}/health/simple", timeout=self.timeout)
                response_times.append(time.time() - start_time)

                if response.status_code != 200:
                    return False, f"Health check failed on request {i+1}: {response.status_code}"

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            if max_response_time > self.performance_thresholds["health_check_response_time"] * 2:
                return (
                    False,
                    f"Inconsistent performance: max response time {max_response_time:.2f}s",
                )

            return (
                True,
                f"Performance baseline validated (avg: {avg_response_time:.2f}s, max: {max_response_time:.2f}s)",
            )

        except Exception as e:
            return False, f"Performance validation failed: {e}"

    def validate_data_persistence(self) -> Tuple[bool, str]:
        """Validate data persistence and volume mounts."""
        logger.info("Validating data persistence...")

        try:
            # Check if data volume exists
            result = subprocess.run(
                ["docker", "volume", "inspect", "process-matches-data"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, "process-matches-data volume not found"

            # Check if volume is mounted in container
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "process-matches-service",
                    "--format",
                    "{{range .Mounts}}{{.Source}}:{{.Destination}} {{end}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Cannot inspect container mounts: {result.stderr}"

            if "process-matches-data" not in result.stdout:
                return False, "Data volume not mounted in container"

            return True, "Data persistence validated"

        except Exception as e:
            return False, f"Data persistence validation failed: {e}"

    def run_all_validations(self) -> Dict[str, Any]:
        """Run all production deployment validations."""
        validations = [
            ("Service Startup", self.validate_service_startup),
            ("Health Endpoints", self.validate_health_endpoints),
            ("Service Dependencies", self.validate_service_dependencies),
            ("Docker Deployment", self.validate_docker_deployment),
            ("Network Connectivity", self.validate_network_connectivity),
            ("Configuration", self.validate_configuration),
            ("Performance Baseline", self.validate_performance_baseline),
            ("Data Persistence", self.validate_data_persistence),
        ]

        results = {
            "timestamp": datetime.now().isoformat(),
            "service_url": self.service_url,
            "validations": {},
            "overall_success": True,
            "summary": {"total": len(validations), "passed": 0, "failed": 0},
        }

        logger.info("Running production deployment validations...")

        for name, validation_func in validations:
            logger.info(f"Running {name} validation...")

            try:
                success, message = validation_func()
                results["validations"][name] = {"success": success, "message": message}

                if success:
                    results["summary"]["passed"] += 1
                    logger.info(f"✅ {name}: {message}")
                else:
                    results["summary"]["failed"] += 1
                    results["overall_success"] = False
                    logger.error(f"❌ {name}: {message}")

            except Exception as e:
                results["validations"][name] = {
                    "success": False,
                    "message": f"Validation error: {e}",
                }
                results["summary"]["failed"] += 1
                results["overall_success"] = False
                logger.error(f"❌ {name}: Validation error: {e}")

        return results

    def save_validation_report(self, results: Dict[str, Any], output_file: str) -> None:
        """Save validation results to a report file."""
        try:
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(f"Validation report saved to {output_file}")

        except Exception as e:
            logger.warning(f"Could not save validation report: {e}")


def main():
    parser = argparse.ArgumentParser(description="Validate production deployment")
    parser.add_argument(
        "--service-url", default="http://localhost:8000", help="Service URL for validation"
    )
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create validator
    validator = ProductionDeploymentValidator(args.service_url, args.timeout)

    # Run validations
    results = validator.run_all_validations()

    # Save report if requested
    if args.output:
        validator.save_validation_report(results, args.output)

    # Print summary
    print("\n" + "=" * 60)
    print("PRODUCTION DEPLOYMENT VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Service URL: {results['service_url']}")
    print(f"Total validations: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Overall success: {'✅ YES' if results['overall_success'] else '❌ NO'}")

    if not results["overall_success"]:
        print("\nFailed validations:")
        for name, result in results["validations"].items():
            if not result["success"]:
                print(f"  - {name}: {result['message']}")

    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
