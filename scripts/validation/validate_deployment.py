#!/usr/bin/env python3
"""
Comprehensive Deployment Validation Script
Validates complete deployment of the unified match-list-processor service
Issue #54: Final Integration Testing and Production Deployment Validation
"""

import argparse
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Comprehensive deployment validator for the unified service."""

    def __init__(self, config_file: str = None):
        self.config = self._load_config(config_file)
        self.validation_results = []
        self.start_time = time.time()

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load validation configuration."""
        default_config = {
            "service_url": "http://localhost:8000",
            "timeout": 30,
            "retry_attempts": 3,
            "retry_delay": 5,
            "expected_services": [
                "process-matches-service",
                "whatsapp-avatar-service",
                "google-drive-service",
                "fogis-api-client-service",
                "fogis-sync",
            ],
            "expected_volumes": ["process-matches-data", "google-drive-service-data"],
            "expected_networks": ["fogis-network"],
            "health_endpoints": ["/health/simple", "/health"],
            "performance_thresholds": {
                "health_response_time": 2.0,
                "startup_time": 60.0,
                "memory_limit_mb": 512,
            },
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Could not load config file {config_file}: {e}")

        return default_config

    def validate_docker_environment(self) -> Tuple[bool, str]:
        """Validate Docker environment and prerequisites."""
        logger.info("Validating Docker environment...")

        try:
            # Check Docker is installed and running
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return False, "Docker is not installed or not accessible"

            # Check Docker daemon is running
            result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False, "Docker daemon is not running"

            # Check Docker Compose is available
            result = subprocess.run(
                ["docker-compose", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                # Try docker compose (newer syntax)
                result = subprocess.run(
                    ["docker", "compose", "version"], capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    return False, "Docker Compose is not installed"

            return True, "Docker environment validated"

        except subprocess.TimeoutExpired:
            return False, "Docker commands timed out"
        except Exception as e:
            return False, f"Docker environment validation failed: {e}"

    def validate_required_volumes(self) -> Tuple[bool, str]:
        """Validate required Docker volumes exist."""
        logger.info("Validating required volumes...")

        try:
            missing_volumes = []

            for volume in self.config["expected_volumes"]:
                result = subprocess.run(
                    ["docker", "volume", "inspect", volume],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    missing_volumes.append(volume)

            if missing_volumes:
                return False, f"Missing required volumes: {', '.join(missing_volumes)}"

            return (
                True,
                f"All required volumes exist ({len(self.config['expected_volumes'])} checked)",
            )

        except Exception as e:
            return False, f"Volume validation failed: {e}"

    def validate_required_networks(self) -> Tuple[bool, str]:
        """Validate required Docker networks exist."""
        logger.info("Validating required networks...")

        try:
            missing_networks = []

            for network in self.config["expected_networks"]:
                result = subprocess.run(
                    ["docker", "network", "inspect", network],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    missing_networks.append(network)

            if missing_networks:
                return False, f"Missing required networks: {', '.join(missing_networks)}"

            return (
                True,
                f"All required networks exist ({len(self.config['expected_networks'])} checked)",
            )

        except Exception as e:
            return False, f"Network validation failed: {e}"

    def validate_service_containers(self) -> Tuple[bool, str]:
        """Validate all required service containers are running."""
        logger.info("Validating service containers...")

        try:
            # Get running containers
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Could not list containers: {result.stderr}"

            running_containers = {}
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        name, status = parts[0], parts[1]
                        running_containers[name] = status

            # Check each expected service
            missing_services = []
            unhealthy_services = []

            for service in self.config["expected_services"]:
                if service not in running_containers:
                    missing_services.append(service)
                elif "Up" not in running_containers[service]:
                    unhealthy_services.append(f"{service}: {running_containers[service]}")

            if missing_services:
                return False, f"Missing services: {', '.join(missing_services)}"

            if unhealthy_services:
                return False, f"Unhealthy services: {', '.join(unhealthy_services)}"

            return True, f"All services running ({len(self.config['expected_services'])} checked)"

        except Exception as e:
            return False, f"Service container validation failed: {e}"

    def validate_service_health(self) -> Tuple[bool, str]:
        """Validate service health endpoints."""
        logger.info("Validating service health...")

        try:
            service_url = self.config["service_url"]
            timeout = self.config["timeout"]

            # Test each health endpoint
            for endpoint in self.config["health_endpoints"]:
                url = f"{service_url}{endpoint}"

                start_time = time.time()
                response = requests.get(url, timeout=timeout)
                response_time = time.time() - start_time

                if response.status_code not in [200, 503]:  # 503 acceptable for degraded state
                    return False, f"Health endpoint {endpoint} returned {response.status_code}"

                # Check response time
                threshold = self.config["performance_thresholds"]["health_response_time"]
                if response_time > threshold:
                    return (
                        False,
                        f"Health endpoint {endpoint} too slow: {response_time:.2f}s > {threshold}s",
                    )

                # Validate response format
                try:
                    health_data = response.json()
                    if "status" not in health_data:
                        return False, f"Health endpoint {endpoint} missing status field"
                except json.JSONDecodeError:
                    return False, f"Health endpoint {endpoint} returned invalid JSON"

            return (
                True,
                f"All health endpoints validated ({len(self.config['health_endpoints'])} checked)",
            )

        except requests.exceptions.RequestException as e:
            return False, f"Health endpoint validation failed: {e}"
        except Exception as e:
            return False, f"Service health validation failed: {e}"

    def validate_service_dependencies(self) -> Tuple[bool, str]:
        """Validate external service dependencies."""
        logger.info("Validating service dependencies...")

        try:
            service_url = self.config["service_url"]
            timeout = self.config["timeout"]

            # Get detailed health status
            response = requests.get(f"{service_url}/health", timeout=timeout)
            if response.status_code not in [200, 503]:
                return False, f"Cannot get dependency status: HTTP {response.status_code}"

            health_data = response.json()
            dependencies = health_data.get("dependencies", {})

            if not dependencies:
                return False, "No dependency information available"

            # Check dependency status
            unhealthy_deps = []
            for dep_name, dep_status in dependencies.items():
                if dep_status != "healthy":
                    unhealthy_deps.append(f"{dep_name}: {dep_status}")

            if unhealthy_deps:
                # This is a warning, not necessarily a failure
                logger.warning(f"Some dependencies are unhealthy: {', '.join(unhealthy_deps)}")

            return True, f"Dependencies checked ({len(dependencies)} dependencies)"

        except Exception as e:
            return False, f"Dependency validation failed: {e}"

    def validate_configuration_completeness(self) -> Tuple[bool, str]:
        """Validate configuration completeness."""
        logger.info("Validating configuration completeness...")

        try:
            # Check environment variables in main container
            result = subprocess.run(
                ["docker", "exec", "process-matches-service", "env"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Cannot read container environment: {result.stderr}"

            env_vars = {}
            for line in result.stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value

            # Check required environment variables
            required_vars = ["PROCESSOR_MODE", "RUN_MODE", "DATA_FOLDER", "FOGIS_API_CLIENT_URL"]

            missing_vars = []
            for var in required_vars:
                if var not in env_vars:
                    missing_vars.append(var)

            if missing_vars:
                return False, f"Missing required environment variables: {', '.join(missing_vars)}"

            # Validate specific values
            if env_vars.get("PROCESSOR_MODE") != "unified":
                return False, f"Invalid PROCESSOR_MODE: {env_vars.get('PROCESSOR_MODE')}"

            return True, f"Configuration validated ({len(env_vars)} environment variables)"

        except Exception as e:
            return False, f"Configuration validation failed: {e}"

    def validate_data_persistence(self) -> Tuple[bool, str]:
        """Validate data persistence and file access."""
        logger.info("Validating data persistence...")

        try:
            # Check if data directory is accessible in container
            result = subprocess.run(
                ["docker", "exec", "process-matches-service", "ls", "-la", "/data"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Cannot access data directory: {result.stderr}"

            # Check if we can write to data directory
            test_file = f"/data/deployment_test_{int(time.time())}.txt"
            result = subprocess.run(
                ["docker", "exec", "process-matches-service", "touch", test_file],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Cannot write to data directory: {result.stderr}"

            # Clean up test file
            subprocess.run(
                ["docker", "exec", "process-matches-service", "rm", "-f", test_file],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return True, "Data persistence validated"

        except Exception as e:
            return False, f"Data persistence validation failed: {e}"

    def validate_performance_baseline(self) -> Tuple[bool, str]:
        """Validate performance meets baseline requirements."""
        logger.info("Validating performance baseline...")

        try:
            service_url = self.config["service_url"]

            # Test response time consistency
            response_times = []
            for i in range(5):
                start_time = time.time()
                response = requests.get(f"{service_url}/health/simple", timeout=10)
                response_time = time.time() - start_time

                if response.status_code != 200:
                    return (
                        False,
                        f"Health check failed during performance test: {response.status_code}",
                    )

                response_times.append(response_time)

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)

            threshold = self.config["performance_thresholds"]["health_response_time"]
            if max_response_time > threshold:
                return False, f"Performance below baseline: {max_response_time:.2f}s > {threshold}s"

            return (
                True,
                f"Performance baseline met (avg: {avg_response_time:.2f}s, max: {max_response_time:.2f}s)",
            )

        except Exception as e:
            return False, f"Performance validation failed: {e}"

    def run_all_validations(self) -> Dict[str, Any]:
        """Run all deployment validations."""
        validations = [
            ("Docker Environment", self.validate_docker_environment),
            ("Required Volumes", self.validate_required_volumes),
            ("Required Networks", self.validate_required_networks),
            ("Service Containers", self.validate_service_containers),
            ("Service Health", self.validate_service_health),
            ("Service Dependencies", self.validate_service_dependencies),
            ("Configuration Completeness", self.validate_configuration_completeness),
            ("Data Persistence", self.validate_data_persistence),
            ("Performance Baseline", self.validate_performance_baseline),
        ]

        results = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "validations": {},
            "overall_success": True,
            "summary": {"total": len(validations), "passed": 0, "failed": 0},
        }

        logger.info("Running comprehensive deployment validations...")

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
    parser = argparse.ArgumentParser(
        description="Validate deployment of unified match-list-processor"
    )
    parser.add_argument("--config", help="Configuration file for validation parameters")
    parser.add_argument("--output", help="Output file for validation report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create validator
    validator = DeploymentValidator(args.config)

    # Run validations
    results = validator.run_all_validations()

    # Save report if requested
    if args.output:
        validator.save_validation_report(results, args.output)

    # Print summary
    print("\n" + "=" * 70)
    print("DEPLOYMENT VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total validations: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Overall success: {'✅ YES' if results['overall_success'] else '❌ NO'}")

    if not results["overall_success"]:
        print("\nFailed validations:")
        for name, result in results["validations"].items():
            if not result["success"]:
                print(f"  - {name}: {result['message']}")
    else:
        print("\n🎉 All validations passed! Deployment is ready for production.")

    return 0 if results["overall_success"] else 1


if __name__ == "__main__":
    exit(main())
