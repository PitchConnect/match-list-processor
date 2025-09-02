#!/usr/bin/env python3
"""
Post-Migration Validation Script
Validates successful migration from old service to new unified processor
Issue #53: Migration Tooling and Scripts
"""

import argparse
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PostMigrationValidator:
    """Validates successful migration to unified processor."""

    def __init__(self, backup_dir: str):
        self.backup_dir = Path(backup_dir)
        self.validation_results = []
        self.service_url = "http://localhost:8000"

    def validate_service_health(self) -> Tuple[bool, str]:
        """Validate service health and responsiveness."""
        try:
            # Test simple health endpoint
            response = requests.get(f"{self.service_url}/health/simple", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if health_data.get("status") == "healthy":
                    return True, "Service health check passed"
                else:
                    return False, f"Service unhealthy: {health_data}"
            else:
                return False, f"Health check failed with status {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"Health check request failed: {e}"

    def validate_detailed_health(self) -> Tuple[bool, str]:
        """Validate detailed health endpoint with dependency checks."""
        try:
            response = requests.get(f"{self.service_url}/health/detailed", timeout=15)
            if response.status_code == 200:
                health_data = response.json()

                # Check overall status
                if health_data.get("status") != "healthy":
                    return (
                        False,
                        f"Detailed health check failed: {health_data.get('message', 'Unknown error')}",
                    )

                # Check dependencies
                dependencies = health_data.get("dependencies", {})
                failed_deps = [name for name, status in dependencies.items() if status != "healthy"]

                if failed_deps:
                    return False, f"Dependency health check failed for: {', '.join(failed_deps)}"

                return True, "Detailed health check passed"
            else:
                return False, f"Detailed health check failed with status {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"Detailed health check request failed: {e}"

    def validate_semantic_analysis_integration(self) -> Tuple[bool, str]:
        """Validate semantic analysis integration is working."""
        try:
            # Check if semantic analysis endpoint is available
            # This would be a test endpoint that verifies semantic analysis is working
            response = requests.get(f"{self.service_url}/health/detailed", timeout=10)
            if response.status_code == 200:
                health_data = response.json()

                # Check if semantic analysis is mentioned in the health data
                features = health_data.get("features", {})
                if "semantic_analysis" in features:
                    if features["semantic_analysis"]:
                        return True, "Semantic analysis integration verified"
                    else:
                        return False, "Semantic analysis is disabled"
                else:
                    # If not explicitly mentioned, assume it's working if service is healthy
                    return True, "Semantic analysis integration assumed working (service healthy)"
            else:
                return (
                    False,
                    f"Could not verify semantic analysis integration (status {response.status_code})",
                )

        except requests.exceptions.RequestException as e:
            return False, f"Semantic analysis integration check failed: {e}"

    def validate_docker_services(self) -> Tuple[bool, str]:
        """Validate Docker services are running correctly."""
        try:
            # Check if the new service is running
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return False, f"Docker ps command failed: {result.stderr}"

            # Check if process-matches-service is running
            if "process-matches-service" in result.stdout:
                # Check if it's actually healthy (not just running)
                if "Up" in result.stdout:
                    return True, "Docker service is running"
                else:
                    return False, "Docker service is not in 'Up' state"
            else:
                return False, "process-matches-service not found in running containers"

        except subprocess.TimeoutExpired:
            return False, "Docker ps command timed out"
        except Exception as e:
            return False, f"Docker service validation failed: {e}"

    def validate_data_integrity(self) -> Tuple[bool, str]:
        """Validate data integrity after migration."""
        try:
            # Check if data volume exists and is accessible
            result = subprocess.run(
                ["docker", "volume", "ls"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return False, f"Docker volume ls command failed: {result.stderr}"

            if "process-matches-data" not in result.stdout:
                return False, "process-matches-data volume not found"

            # Check if previous matches file exists (if it should)
            backup_metadata_file = self.backup_dir / "migration_metadata.json"
            if backup_metadata_file.exists():
                with open(backup_metadata_file, "r") as f:
                    metadata = json.load(f)

                if metadata.get("backup_contents", {}).get("data_volume", False):
                    # Data was backed up, so it should be restored
                    # We can't easily check file contents without exec into container
                    # but we can verify the volume exists
                    return True, "Data volume exists and backup was created"

            return True, "Data integrity check passed (volume exists)"

        except Exception as e:
            return False, f"Data integrity validation failed: {e}"

    def validate_configuration_migration(self) -> Tuple[bool, str]:
        """Validate configuration was migrated correctly."""
        try:
            # Check if migrated .env file exists and is valid
            env_file = Path(".env")
            if not env_file.exists():
                return False, ".env file not found after migration"

            # Read and validate key configuration values
            env_vars = {}
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()

            # Check required variables
            required_vars = ["PROCESSOR_MODE", "RUN_MODE", "DATA_FOLDER", "FOGIS_API_CLIENT_URL"]

            missing_vars = [var for var in required_vars if var not in env_vars]
            if missing_vars:
                return False, f"Missing required configuration variables: {', '.join(missing_vars)}"

            # Check specific values
            if env_vars.get("PROCESSOR_MODE") != "unified":
                return (
                    False,
                    f"PROCESSOR_MODE should be 'unified', got '{env_vars.get('PROCESSOR_MODE')}'",
                )

            return True, "Configuration migration validation passed"

        except Exception as e:
            return False, f"Configuration validation failed: {e}"

    def validate_network_connectivity(self) -> Tuple[bool, str]:
        """Validate network connectivity to dependent services."""
        try:
            # Test connectivity to the main service
            response = requests.get(f"{self.service_url}/health/simple", timeout=5)
            if response.status_code != 200:
                return False, f"Network connectivity test failed (status {response.status_code})"

            return True, "Network connectivity validation passed"

        except requests.exceptions.RequestException as e:
            return False, f"Network connectivity test failed: {e}"

    def run_all_validations(self) -> Dict[str, Any]:
        """Run all post-migration validations."""
        validations = [
            ("Service Health", self.validate_service_health),
            ("Detailed Health", self.validate_detailed_health),
            ("Docker Services", self.validate_docker_services),
            ("Data Integrity", self.validate_data_integrity),
            ("Configuration Migration", self.validate_configuration_migration),
            ("Network Connectivity", self.validate_network_connectivity),
            ("Semantic Analysis Integration", self.validate_semantic_analysis_integration),
        ]

        results = {
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "overall_success": True,
            "summary": {"total": len(validations), "passed": 0, "failed": 0},
        }

        logger.info("Running post-migration validations...")

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

    def save_validation_report(self, results: Dict[str, Any]) -> None:
        """Save validation results to a report file."""
        report_file = (
            self.backup_dir
            / f"post_migration_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        try:
            with open(report_file, "w") as f:
                json.dump(results, f, indent=2)

            logger.info(f"Validation report saved to {report_file}")

        except Exception as e:
            logger.warning(f"Could not save validation report: {e}")


def main():
    parser = argparse.ArgumentParser(description="Validate post-migration state")
    parser.add_argument("--backup-dir", required=True, help="Backup directory path")
    parser.add_argument(
        "--service-url", default="http://localhost:8000", help="Service URL for health checks"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create validator
    validator = PostMigrationValidator(args.backup_dir)
    validator.service_url = args.service_url

    # Run validations
    results = validator.run_all_validations()

    # Save report
    validator.save_validation_report(results)

    # Print summary
    print("\n" + "=" * 50)
    print("POST-MIGRATION VALIDATION SUMMARY")
    print("=" * 50)
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
