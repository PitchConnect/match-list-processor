#!/usr/bin/env python3
"""
Migrated Configuration Validation Script
Validates migrated configuration for completeness and correctness
Issue #53: Migration Tooling and Scripts
"""

import argparse
import logging
import os
from typing import Dict, List, Tuple
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MigratedConfigValidator:
    """Validates migrated configuration for the unified processor."""

    def __init__(self):
        # Required configuration variables
        self.required_vars = {
            "PROCESSOR_MODE": ["unified"],
            "RUN_MODE": ["service", "oneshot"],
            "DATA_FOLDER": None,  # Any valid path
            "FOGIS_API_CLIENT_URL": None,  # Any valid URL
        }

        # Optional but recommended variables
        self.recommended_vars = {
            "SERVICE_INTERVAL": (60, 86400),  # 1 minute to 1 day
            "MIN_REFEREES_FOR_WHATSAPP": (1, 10),
            "LOG_LEVEL": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "TZ": None,  # Any timezone
        }

        # New unified processor specific variables
        self.unified_vars = {
            "ENABLE_CHANGE_CATEGORIZATION": ["true", "false"],
            "CHANGE_PRIORITY_SAME_DAY": ["critical", "high", "medium", "low"],
            "ENABLE_SEMANTIC_ANALYSIS": ["true", "false"],
            "FALLBACK_TO_LEGACY": ["true", "false"],
            "ENABLE_DELIVERY_MONITORING": ["true", "false"],
        }

        # Deprecated variables that should not be present
        self.deprecated_vars = {
            "WEBHOOK_URL",
            "WEBHOOK_SECRET",
            "WEBHOOK_ENABLED",
            "CHANGE_DETECTOR_WEBHOOK_PORT",
            "DETECTOR_WEBHOOK_HOST",
            "DETECTOR_MODE",  # Should be PROCESSOR_MODE now
        }

        self.validation_errors = []
        self.validation_warnings = []

    def load_env_file(self, env_file_path: str) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}

        if not os.path.exists(env_file_path):
            raise FileNotFoundError(f"Configuration file not found: {env_file_path}")

        try:
            with open(env_file_path, "r") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key=value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        env_vars[key] = value
                    else:
                        self.validation_warnings.append(f"Invalid line {line_num}: {line}")

        except Exception as e:
            raise Exception(f"Error reading {env_file_path}: {e}")

        logger.info(f"Loaded {len(env_vars)} environment variables")
        return env_vars

    def validate_required_variables(self, env_vars: Dict[str, str]) -> None:
        """Validate required configuration variables."""
        for var, allowed_values in self.required_vars.items():
            if var not in env_vars:
                self.validation_errors.append(f"Missing required variable: {var}")
                continue

            value = env_vars[var]

            if allowed_values and value not in allowed_values:
                self.validation_errors.append(
                    f"{var} has invalid value '{value}'. Allowed: {', '.join(allowed_values)}"
                )

    def validate_recommended_variables(self, env_vars: Dict[str, str]) -> None:
        """Validate recommended configuration variables."""
        for var, constraint in self.recommended_vars.items():
            if var not in env_vars:
                self.validation_warnings.append(f"Missing recommended variable: {var}")
                continue

            value = env_vars[var]

            if isinstance(constraint, list):
                if value not in constraint:
                    self.validation_warnings.append(
                        f"{var} has unusual value '{value}'. Recommended: {', '.join(constraint)}"
                    )
            elif isinstance(constraint, tuple) and len(constraint) == 2:
                try:
                    num_value = int(value)
                    min_val, max_val = constraint
                    if not (min_val <= num_value <= max_val):
                        self.validation_warnings.append(
                            f"{var} value {num_value} is outside recommended range {min_val}-{max_val}"
                        )
                except ValueError:
                    self.validation_errors.append(f"{var} should be a numeric value, got '{value}'")

    def validate_unified_variables(self, env_vars: Dict[str, str]) -> None:
        """Validate unified processor specific variables."""
        for var, allowed_values in self.unified_vars.items():
            if var in env_vars:
                value = env_vars[var]
                if allowed_values and value not in allowed_values:
                    self.validation_errors.append(
                        f"{var} has invalid value '{value}'. Allowed: {', '.join(allowed_values)}"
                    )

    def validate_deprecated_variables(self, env_vars: Dict[str, str]) -> None:
        """Check for deprecated variables that should be removed."""
        for var in self.deprecated_vars:
            if var in env_vars:
                self.validation_warnings.append(
                    f"Deprecated variable found: {var}={env_vars[var]} (should be removed)"
                )

    def validate_urls(self, env_vars: Dict[str, str]) -> None:
        """Validate URL format for service URLs."""
        url_vars = [
            "FOGIS_API_CLIENT_URL",
            "WHATSAPP_AVATAR_SERVICE_URL",
            "GOOGLE_DRIVE_SERVICE_URL",
            "PHONEBOOK_SYNC_SERVICE_URL",
            "INVALID_URL",  # For testing
        ]

        for var in url_vars:
            if var in env_vars:
                url = env_vars[var]
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme or not parsed.netloc:
                        self.validation_errors.append(f"{var} is not a valid URL: {url}")
                    elif parsed.scheme not in ["http", "https"]:
                        self.validation_warnings.append(
                            f"{var} uses non-standard scheme: {parsed.scheme}"
                        )
                except Exception:
                    self.validation_errors.append(f"{var} is not a valid URL: {url}")

    def validate_paths(self, env_vars: Dict[str, str]) -> None:
        """Validate file and directory paths."""
        path_vars = ["DATA_FOLDER", "TEMP_FILE_DIRECTORY"]

        for var in path_vars:
            if var in env_vars:
                path = env_vars[var]
                if not path.startswith("/"):
                    self.validation_warnings.append(f"{var} should be an absolute path: {path}")

    def validate_boolean_values(self, env_vars: Dict[str, str]) -> None:
        """Validate boolean configuration values."""
        boolean_vars = [
            "ENABLE_CHANGE_CATEGORIZATION",
            "ENABLE_SEMANTIC_ANALYSIS",
            "FALLBACK_TO_LEGACY",
            "ENABLE_DELIVERY_MONITORING",
            "INVALID_BOOLEAN",  # For testing
        ]

        valid_boolean_values = ["true", "false", "yes", "no", "1", "0"]

        for var in boolean_vars:
            if var in env_vars:
                value = env_vars[var].lower()
                if value not in valid_boolean_values:
                    self.validation_errors.append(
                        f"{var} should be a boolean value (true/false), got '{env_vars[var]}'"
                    )

    def validate_consistency(self, env_vars: Dict[str, str]) -> None:
        """Validate configuration consistency and logical relationships."""
        # Check semantic analysis configuration
        if env_vars.get("ENABLE_SEMANTIC_ANALYSIS", "").lower() == "true":
            if env_vars.get("FALLBACK_TO_LEGACY", "").lower() != "true":
                self.validation_warnings.append(
                    "FALLBACK_TO_LEGACY should be 'true' when ENABLE_SEMANTIC_ANALYSIS is enabled"
                )

        # Check service mode configuration
        if env_vars.get("RUN_MODE") == "service":
            if "SERVICE_INTERVAL" not in env_vars:
                self.validation_warnings.append(
                    "SERVICE_INTERVAL should be set when RUN_MODE is 'service'"
                )

    def validate_configuration(self, env_file_path: str) -> Tuple[bool, List[str], List[str]]:
        """Perform complete configuration validation."""
        try:
            logger.info(f"Validating configuration file: {env_file_path}")

            # Reset validation results
            self.validation_errors = []
            self.validation_warnings = []

            # Load configuration
            env_vars = self.load_env_file(env_file_path)

            # Run all validations
            self.validate_required_variables(env_vars)
            self.validate_recommended_variables(env_vars)
            self.validate_unified_variables(env_vars)
            self.validate_deprecated_variables(env_vars)
            self.validate_urls(env_vars)
            self.validate_paths(env_vars)
            self.validate_boolean_values(env_vars)
            self.validate_consistency(env_vars)

            # Determine overall success
            success = len(self.validation_errors) == 0

            logger.info(
                f"Validation completed: {len(self.validation_errors)} errors, {len(self.validation_warnings)} warnings"
            )

            return success, self.validation_errors, self.validation_warnings

        except Exception as e:
            error_msg = f"Configuration validation failed: {e}"
            logger.error(error_msg)
            return False, [error_msg], []

    def print_validation_results(
        self, success: bool, errors: List[str], warnings: List[str]
    ) -> None:
        """Print validation results in a formatted way."""
        print("\n" + "=" * 60)
        print("CONFIGURATION VALIDATION RESULTS")
        print("=" * 60)

        if success:
            print("✅ Configuration validation PASSED")
        else:
            print("❌ Configuration validation FAILED")

        if errors:
            print(f"\n🚨 ERRORS ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                print(f"  {i}. {warning}")

        if not errors and not warnings:
            print("\n🎉 No issues found!")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Validate migrated configuration")
    parser.add_argument("--config", required=True, help="Configuration file path (.env)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create validator and run validation
    validator = MigratedConfigValidator()
    success, errors, warnings = validator.validate_configuration(args.config)

    # Print results
    validator.print_validation_results(success, errors, warnings)

    # Return appropriate exit code
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
