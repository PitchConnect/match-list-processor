#!/usr/bin/env python3
"""
Configuration validation script for unified match processor.

This script validates the configuration files and environment variables
to ensure proper deployment and operation of the consolidated service.

Usage:
    python scripts/validate_config.py [--config-file CONFIG_FILE] [--env-file ENV_FILE]
"""

import argparse
import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import yaml


class ConfigValidator:
    """Validates configuration for unified match processor."""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_config_file(self, config_path: str) -> bool:
        """Validate YAML configuration file."""
        print(f"🔍 Validating configuration file: {config_path}")

        if not os.path.exists(config_path):
            self.errors.append(f"Configuration file not found: {config_path}")
            return False

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML syntax: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Failed to read config file: {e}")
            return False

        # Validate configuration structure
        self._validate_processor_config(config.get("processor", {}))
        self._validate_change_detection_config(config.get("change_detection", {}))
        self._validate_storage_config(config.get("storage", {}))
        self._validate_integrations_config(config.get("integrations", {}))
        self._validate_logging_config(config.get("logging", {}))

        return len(self.errors) == 0

    def validate_environment(self, env_file: Optional[str] = None) -> bool:
        """Validate environment variables."""
        print("🔍 Validating environment variables")

        # Load environment file if provided
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)

        # Required environment variables
        required_vars = [
            "PROCESSOR_MODE",
            "RUN_MODE",
            "DATA_FOLDER",
            "FOGIS_API_CLIENT_URL",
            "WHATSAPP_AVATAR_SERVICE_URL",
            "GOOGLE_DRIVE_SERVICE_URL",
            "PHONEBOOK_SYNC_SERVICE_URL",
        ]

        for var in required_vars:
            if not os.getenv(var):
                self.errors.append(f"Required environment variable not set: {var}")

        # Validate specific environment variables
        self._validate_processor_mode()
        self._validate_run_mode()
        self._validate_service_urls()
        self._validate_paths()

        return len(self.errors) == 0

    def validate_docker_compose(self, compose_path: str) -> bool:
        """Validate Docker Compose configuration."""
        print(f"🔍 Validating Docker Compose file: {compose_path}")

        if not os.path.exists(compose_path):
            self.errors.append(f"Docker Compose file not found: {compose_path}")
            return False

        try:
            with open(compose_path, "r") as f:
                compose = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid Docker Compose YAML: {e}")
            return False

        # Check for deprecated services
        services = compose.get("services", {})

        # Ensure no change detector service exists
        if "match-list-change-detector" in services:
            self.errors.append(
                "Deprecated service found: match-list-change-detector should be removed"
            )

        # Validate main service
        main_service = services.get("process-matches-service")
        if not main_service:
            self.errors.append("Main service 'process-matches-service' not found")
        else:
            self._validate_docker_service(main_service)

        return len(self.errors) == 0

    def _validate_processor_config(self, config: Dict[str, Any]):
        """Validate processor configuration."""
        mode = config.get("mode")
        if mode != "unified":
            self.errors.append(f"Invalid processor mode: {mode}. Must be 'unified'")

        run_mode = config.get("run_mode")
        if run_mode not in ["service", "oneshot"]:
            self.errors.append(f"Invalid run mode: {run_mode}. Must be 'service' or 'oneshot'")

        interval = config.get("interval")
        if interval and (not isinstance(interval, int) or interval < 60):
            self.warnings.append(
                f"Processing interval {interval} is very short. Consider >= 60 seconds"
            )

    def _validate_change_detection_config(self, config: Dict[str, Any]):
        """Validate change detection configuration."""
        if not config.get("enabled", True):
            self.warnings.append("Change detection is disabled")

        priority = config.get("same_day_priority")
        if priority not in ["critical", "high", "medium", "low"]:
            self.errors.append(f"Invalid same day priority: {priority}")

    def _validate_storage_config(self, config: Dict[str, Any]):
        """Validate storage configuration."""
        data_folder = config.get("data_folder")
        if not data_folder:
            self.errors.append("Data folder not specified")

        temp_directory = config.get("temp_directory")
        if not temp_directory:
            self.warnings.append("Temp directory not specified, using default")

    def _validate_integrations_config(self, config: Dict[str, Any]):
        """Validate external service integrations."""
        required_services = ["fogis_api", "whatsapp_avatar", "google_drive", "phonebook_sync"]

        for service in required_services:
            service_config = config.get(service, {})
            url = service_config.get("url")

            if not url:
                self.errors.append(f"URL not specified for service: {service}")
                continue

            # Validate URL format
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                self.errors.append(f"Invalid URL for service {service}: {url}")

            # Validate timeout
            timeout = service_config.get("timeout")
            if timeout and (not isinstance(timeout, int) or timeout < 1):
                self.warnings.append(f"Invalid timeout for service {service}: {timeout}")

    def _validate_logging_config(self, config: Dict[str, Any]):
        """Validate logging configuration."""
        level = config.get("level")
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            self.errors.append(f"Invalid log level: {level}")

    def _validate_processor_mode(self):
        """Validate processor mode environment variable."""
        mode = os.getenv("PROCESSOR_MODE")
        if mode and mode != "unified":
            self.errors.append(f"Invalid PROCESSOR_MODE: {mode}. Must be 'unified'")

    def _validate_run_mode(self):
        """Validate run mode environment variable."""
        run_mode = os.getenv("RUN_MODE")
        if run_mode and run_mode not in ["service", "oneshot"]:
            self.errors.append(f"Invalid RUN_MODE: {run_mode}. Must be 'service' or 'oneshot'")

    def _validate_service_urls(self):
        """Validate service URL environment variables."""
        url_vars = [
            "FOGIS_API_CLIENT_URL",
            "WHATSAPP_AVATAR_SERVICE_URL",
            "GOOGLE_DRIVE_SERVICE_URL",
            "PHONEBOOK_SYNC_SERVICE_URL",
        ]

        for var in url_vars:
            url = os.getenv(var)
            if url:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    self.errors.append(f"Invalid URL in {var}: {url}")

    def _validate_paths(self):
        """Validate path environment variables."""
        data_folder = os.getenv("DATA_FOLDER")
        if data_folder and not os.path.isabs(data_folder):
            self.warnings.append(f"DATA_FOLDER should be absolute path: {data_folder}")

    def _validate_docker_service(self, service: Dict[str, Any]):
        """Validate Docker service configuration."""
        # Check for required environment variables
        env_vars = service.get("environment", [])
        required_env = ["PROCESSOR_MODE", "RUN_MODE", "DATA_FOLDER"]

        env_dict = {}
        for env in env_vars:
            if "=" in env:
                key, value = env.split("=", 1)
                env_dict[key] = value

        for req_env in required_env:
            if req_env not in env_dict:
                self.warnings.append(
                    f"Required environment variable {req_env} not set in Docker service"
                )

        # Check health check
        if "healthcheck" not in service:
            self.warnings.append("Health check not configured for main service")

    def _load_env_file(self, env_file: str):
        """Load environment variables from file."""
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key] = value
        except Exception as e:
            self.warnings.append(f"Failed to load environment file {env_file}: {e}")

    def print_results(self):
        """Print validation results."""
        print("\n" + "=" * 60)
        print("🔍 CONFIGURATION VALIDATION RESULTS")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")

        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        elif not self.errors:
            print(f"\n✅ Validation passed with {len(self.warnings)} warnings")
        else:
            print(
                f"\n❌ Validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings"
            )

        print("=" * 60)

        return len(self.errors) == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Validate unified processor configuration")
    parser.add_argument(
        "--config-file", default="config/unified_processor.yml", help="Path to configuration file"
    )
    parser.add_argument("--env-file", help="Path to environment file")
    parser.add_argument(
        "--docker-compose", default="docker-compose.yml", help="Path to Docker Compose file"
    )

    args = parser.parse_args()

    validator = ConfigValidator()

    # Validate configuration file
    validator.validate_config_file(args.config_file)

    # Validate environment
    validator.validate_environment(args.env_file)

    # Validate Docker Compose
    validator.validate_docker_compose(args.docker_compose)

    # Print results
    success = validator.print_results()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
