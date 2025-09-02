#!/usr/bin/env python3
"""
Configuration Migration Utility
Migrates configuration from old service format to new unified processor format
Issue #53: Migration Tooling and Scripts
"""

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ConfigurationMigrator:
    """Migrates configuration from old service to new unified processor."""

    def __init__(self, backup_dir: str):
        self.backup_dir = Path(backup_dir)
        self.migration_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Environment variable mapping from old to new format
        self.env_mapping = {
            # Service configuration
            "CHANGE_DETECTOR_MODE": "PROCESSOR_MODE",
            "DETECTOR_RUN_MODE": "RUN_MODE",
            "DETECTOR_SERVICE_INTERVAL": "SERVICE_INTERVAL",
            # Data storage
            "CHANGE_DETECTOR_DATA_FOLDER": "DATA_FOLDER",
            "DETECTOR_PREVIOUS_MATCHES_FILE": "PREVIOUS_MATCHES_FILE",
            "DETECTOR_TEMP_DIRECTORY": "TEMP_FILE_DIRECTORY",
            # Service URLs (these should remain the same but validate)
            "FOGIS_API_CLIENT_URL": "FOGIS_API_CLIENT_URL",
            "WHATSAPP_AVATAR_SERVICE_URL": "WHATSAPP_AVATAR_SERVICE_URL",
            "GOOGLE_DRIVE_SERVICE_URL": "GOOGLE_DRIVE_SERVICE_URL",
            "PHONEBOOK_SYNC_SERVICE_URL": "PHONEBOOK_SYNC_SERVICE_URL",
            # Processing settings
            "MIN_REFEREES_FOR_WHATSAPP": "MIN_REFEREES_FOR_WHATSAPP",
            "GDRIVE_FOLDER_BASE": "GDRIVE_FOLDER_BASE",
            # Logging
            "LOG_LEVEL": "LOG_LEVEL",
            "LOG_FORMAT": "LOG_FORMAT",
            # Health check
            "HEALTH_SERVER_PORT": "HEALTH_SERVER_PORT",
            "HEALTH_SERVER_HOST": "HEALTH_SERVER_HOST",
        }

        # Default values for new unified processor
        self.default_values = {
            "PROCESSOR_MODE": "unified",
            "RUN_MODE": "service",
            "SERVICE_INTERVAL": "3600",
            "ENABLE_CHANGE_CATEGORIZATION": "true",
            "CHANGE_PRIORITY_SAME_DAY": "critical",
            "ENABLE_SEMANTIC_ANALYSIS": "true",
            "FALLBACK_TO_LEGACY": "true",
            "ENABLE_DELIVERY_MONITORING": "true",
            "TZ": "Europe/Stockholm",
        }

        # Values to remove (no longer needed)
        self.deprecated_values = {
            "WEBHOOK_URL",
            "WEBHOOK_SECRET",
            "WEBHOOK_ENABLED",
            "CHANGE_DETECTOR_WEBHOOK_PORT",
            "DETECTOR_WEBHOOK_HOST",
        }

    def load_env_file(self, env_file_path: str) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}

        if not os.path.exists(env_file_path):
            logger.warning(f"Environment file not found: {env_file_path}")
            return env_vars

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
                        logger.warning(f"Invalid line {line_num} in {env_file_path}: {line}")

        except Exception as e:
            logger.error(f"Error reading {env_file_path}: {e}")
            raise

        logger.info(f"Loaded {len(env_vars)} environment variables from {env_file_path}")
        return env_vars

    def migrate_environment_variables(self, old_env: Dict[str, str]) -> Dict[str, str]:
        """Convert old environment variables to new format."""
        new_env = {}
        migration_log = []

        # Apply mappings
        for old_key, new_key in self.env_mapping.items():
            if old_key in old_env:
                new_env[new_key] = old_env[old_key]
                migration_log.append(f"Mapped {old_key} -> {new_key}: {old_env[old_key]}")

        # Copy unchanged variables
        for key, value in old_env.items():
            if key not in self.env_mapping and key not in self.deprecated_values:
                new_env[key] = value
                migration_log.append(f"Preserved {key}: {value}")

        # Add default values for new features (these override any existing values)
        for key, value in self.default_values.items():
            if key not in new_env or key == "PROCESSOR_MODE":  # Always override PROCESSOR_MODE
                new_env[key] = value
                migration_log.append(f"Added default {key}: {value}")

        # Log deprecated values
        for key in self.deprecated_values:
            if key in old_env:
                migration_log.append(f"Deprecated {key}: {old_env[key]} (removed)")

        # Save migration log
        self._save_migration_log(migration_log)

        logger.info(f"Migrated {len(old_env)} -> {len(new_env)} environment variables")
        return new_env

    def validate_configuration(self, config: Dict[str, str]) -> List[str]:
        """Validate migrated configuration for completeness."""
        warnings = []

        # Required variables
        required_vars = [
            "PROCESSOR_MODE",
            "RUN_MODE",
            "DATA_FOLDER",
            "FOGIS_API_CLIENT_URL",
        ]

        for var in required_vars:
            if var not in config:
                warnings.append(f"Missing required variable: {var}")

        # Validate specific values
        if config.get("PROCESSOR_MODE") != "unified":
            warnings.append("PROCESSOR_MODE should be 'unified' for the new service")

        if config.get("RUN_MODE") not in ["service", "oneshot"]:
            warnings.append("RUN_MODE should be 'service' or 'oneshot'")

        # Validate URLs
        url_vars = [
            "FOGIS_API_CLIENT_URL",
            "WHATSAPP_AVATAR_SERVICE_URL",
            "GOOGLE_DRIVE_SERVICE_URL",
            "PHONEBOOK_SYNC_SERVICE_URL",
        ]

        for var in url_vars:
            if var in config and not config[var].startswith(("http://", "https://")):
                warnings.append(f"{var} should be a valid URL")

        # Validate numeric values
        numeric_vars = {
            "SERVICE_INTERVAL": (60, 86400),  # 1 minute to 1 day
            "MIN_REFEREES_FOR_WHATSAPP": (1, 10),
        }

        for var, (min_val, max_val) in numeric_vars.items():
            if var in config:
                try:
                    value = int(config[var])
                    if not (min_val <= value <= max_val):
                        warnings.append(f"{var} should be between {min_val} and {max_val}")
                except ValueError:
                    warnings.append(f"{var} should be a numeric value")

        return warnings

    def save_env_file(self, env_vars: Dict[str, str], output_path: str) -> None:
        """Save environment variables to .env file."""
        try:
            with open(output_path, "w") as f:
                f.write("# Migrated configuration for unified match-list-processor\n")
                f.write(f"# Generated on: {datetime.now().isoformat()}\n")
                f.write("# Migration tool version: 1.0\n\n")

                # Group variables by category
                categories = {
                    "Service Configuration": [
                        "PROCESSOR_MODE",
                        "RUN_MODE",
                        "SERVICE_INTERVAL",
                        "TZ",
                    ],
                    "Change Detection": [
                        "ENABLE_CHANGE_CATEGORIZATION",
                        "CHANGE_PRIORITY_SAME_DAY",
                        "ENABLE_SEMANTIC_ANALYSIS",
                        "FALLBACK_TO_LEGACY",
                    ],
                    "Data Storage": ["DATA_FOLDER", "PREVIOUS_MATCHES_FILE", "TEMP_FILE_DIRECTORY"],
                    "Service URLs": [
                        "FOGIS_API_CLIENT_URL",
                        "WHATSAPP_AVATAR_SERVICE_URL",
                        "GOOGLE_DRIVE_SERVICE_URL",
                        "PHONEBOOK_SYNC_SERVICE_URL",
                    ],
                    "Processing Settings": ["MIN_REFEREES_FOR_WHATSAPP", "GDRIVE_FOLDER_BASE"],
                    "Logging": ["LOG_LEVEL", "LOG_FORMAT"],
                    "Monitoring": [
                        "ENABLE_DELIVERY_MONITORING",
                        "HEALTH_SERVER_PORT",
                        "HEALTH_SERVER_HOST",
                    ],
                }

                # Write categorized variables
                for category, vars_in_category in categories.items():
                    f.write(f"# {category}\n")
                    for var in vars_in_category:
                        if var in env_vars:
                            f.write(f"{var}={env_vars[var]}\n")
                    f.write("\n")

                # Write remaining variables
                written_vars = set()
                for vars_in_category in categories.values():
                    written_vars.update(vars_in_category)

                remaining_vars = {k: v for k, v in env_vars.items() if k not in written_vars}
                if remaining_vars:
                    f.write("# Other Configuration\n")
                    for key, value in sorted(remaining_vars.items()):
                        f.write(f"{key}={value}\n")
                    f.write("\n")

        except Exception as e:
            logger.error(f"Error writing {output_path}: {e}")
            raise

        logger.info(f"Saved migrated configuration to {output_path}")

    def _save_migration_log(self, migration_log: List[str]) -> None:
        """Save migration log for audit purposes."""
        log_file = self.backup_dir / f"migration_log_{self.migration_timestamp}.txt"

        try:
            with open(log_file, "w") as f:
                f.write("Configuration Migration Log\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("Tool Version: 1.0\n")
                f.write("=" * 50 + "\n\n")

                for entry in migration_log:
                    f.write(f"{entry}\n")

        except Exception as e:
            logger.warning(f"Could not save migration log: {e}")

    def migrate(self, input_file: str, output_file: str) -> bool:
        """Perform complete configuration migration."""
        try:
            logger.info(f"Starting configuration migration from {input_file} to {output_file}")

            # Load old configuration
            old_env = self.load_env_file(input_file)

            # Migrate to new format
            new_env = self.migrate_environment_variables(old_env)

            # Validate migrated configuration
            warnings = self.validate_configuration(new_env)
            if warnings:
                logger.warning("Configuration validation warnings:")
                for warning in warnings:
                    logger.warning(f"  - {warning}")

            # Save migrated configuration
            self.save_env_file(new_env, output_file)

            logger.info("Configuration migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Configuration migration failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Migrate configuration for service consolidation")
    parser.add_argument("--input", required=True, help="Input .env file path")
    parser.add_argument("--output", required=True, help="Output .env file path")
    parser.add_argument("--backup-dir", required=True, help="Backup directory path")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create backup directory if it doesn't exist
    os.makedirs(args.backup_dir, exist_ok=True)

    # Perform migration
    migrator = ConfigurationMigrator(args.backup_dir)
    success = migrator.migrate(args.input, args.output)

    if success:
        print("✅ Configuration migration completed successfully")
        return 0
    else:
        print("❌ Configuration migration failed")
        return 1


if __name__ == "__main__":
    exit(main())
