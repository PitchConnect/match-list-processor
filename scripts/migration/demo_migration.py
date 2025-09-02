#!/usr/bin/env python3
"""
Migration Tools Demonstration Script
Demonstrates the migration tooling functionality with realistic examples
Issue #53: Migration Tooling and Scripts
"""

import tempfile
from pathlib import Path

# Import our migration modules
from migrate_config import ConfigurationMigrator
from validate_migrated_config import MigratedConfigValidator


def create_sample_old_config():
    """Create a sample old configuration file."""
    return """# Old match-list-change-detector configuration
# This represents the legacy service configuration

# Service configuration
CHANGE_DETECTOR_MODE=detector
DETECTOR_RUN_MODE=service
DETECTOR_SERVICE_INTERVAL=3600

# Data storage
CHANGE_DETECTOR_DATA_FOLDER=/app/data
DETECTOR_PREVIOUS_MATCHES_FILE=previous_matches.json
DETECTOR_TEMP_DIRECTORY=/tmp

# Service URLs
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
WHATSAPP_AVATAR_SERVICE_URL=http://whatsapp-avatar-service:5002
GOOGLE_DRIVE_SERVICE_URL=http://google-drive-service:5000
PHONEBOOK_SYNC_SERVICE_URL=http://fogis-calendar-phonebook-sync:5003

# Processing settings
MIN_REFEREES_FOR_WHATSAPP=2
GDRIVE_FOLDER_BASE=WhatsApp_Group_Assets

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(levelname)s - %(message)s

# Health check
HEALTH_SERVER_PORT=8000
HEALTH_SERVER_HOST=0.0.0.0

# Deprecated webhook settings (should be removed)
WEBHOOK_URL=http://deprecated.webhook.example.com
WEBHOOK_SECRET=deprecated_secret
WEBHOOK_ENABLED=false
CHANGE_DETECTOR_WEBHOOK_PORT=9000
DETECTOR_WEBHOOK_HOST=0.0.0.0

# Custom application settings
CUSTOM_SETTING_1=custom_value_1
CUSTOM_SETTING_2=custom_value_2
"""


def demonstrate_migration():
    """Demonstrate the complete migration process."""
    print("🔄 Migration Tools Demonstration")
    print("=" * 50)

    # Create temporary directory for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        print(f"📁 Working directory: {temp_dir}")
        print()

        # Step 1: Create old configuration
        print("📝 Step 1: Creating sample old configuration...")
        old_config_file = temp_path / "old.env"
        with open(old_config_file, "w") as f:
            f.write(create_sample_old_config())

        print(f"   Created: {old_config_file}")
        print(f"   Size: {old_config_file.stat().st_size} bytes")

        # Count variables in old config
        old_vars = {}
        with open(old_config_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    old_vars[key.strip()] = value.strip()

        print(f"   Variables: {len(old_vars)}")
        print()

        # Step 2: Perform migration
        print("🔄 Step 2: Performing configuration migration...")
        migrator = ConfigurationMigrator(str(temp_path))
        new_config_file = temp_path / "new.env"

        success = migrator.migrate(str(old_config_file), str(new_config_file))

        if success:
            print("   ✅ Migration completed successfully")
        else:
            print("   ❌ Migration failed")
            return False

        # Count variables in new config
        new_vars = {}
        with open(new_config_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    new_vars[key.strip()] = value.strip()

        print(f"   Variables: {len(old_vars)} -> {len(new_vars)}")
        print()

        # Step 3: Validate migrated configuration
        print("✅ Step 3: Validating migrated configuration...")
        validator = MigratedConfigValidator()
        success, errors, warnings = validator.validate_configuration(str(new_config_file))

        if success:
            print("   ✅ Validation passed")
        else:
            print("   ❌ Validation failed")

        print(f"   Errors: {len(errors)}")
        print(f"   Warnings: {len(warnings)}")

        if errors:
            print("   Errors found:")
            for error in errors:
                print(f"     - {error}")

        if warnings:
            print("   Warnings found:")
            for warning in warnings:
                print(f"     - {warning}")

        print()

        # Step 4: Show migration results
        print("📊 Step 4: Migration Results Summary")
        print("-" * 30)

        # Show key mappings
        print("🔄 Key Variable Mappings:")
        key_mappings = [
            ("CHANGE_DETECTOR_MODE", "PROCESSOR_MODE"),
            ("DETECTOR_RUN_MODE", "RUN_MODE"),
            ("DETECTOR_SERVICE_INTERVAL", "SERVICE_INTERVAL"),
            ("CHANGE_DETECTOR_DATA_FOLDER", "DATA_FOLDER"),
        ]

        for old_key, new_key in key_mappings:
            old_val = old_vars.get(old_key, "N/A")
            new_val = new_vars.get(new_key, "N/A")
            print(f"   {old_key} -> {new_key}")
            print(f"     {old_val} -> {new_val}")

        print()

        # Show new variables added
        print("➕ New Variables Added:")
        new_only_vars = [
            "ENABLE_CHANGE_CATEGORIZATION",
            "CHANGE_PRIORITY_SAME_DAY",
            "ENABLE_SEMANTIC_ANALYSIS",
            "FALLBACK_TO_LEGACY",
            "ENABLE_DELIVERY_MONITORING",
        ]

        for var in new_only_vars:
            if var in new_vars:
                print(f"   {var}={new_vars[var]}")

        print()

        # Show deprecated variables removed
        print("🗑️  Deprecated Variables Removed:")
        deprecated_vars = [
            "WEBHOOK_URL",
            "WEBHOOK_SECRET",
            "WEBHOOK_ENABLED",
            "CHANGE_DETECTOR_WEBHOOK_PORT",
            "DETECTOR_WEBHOOK_HOST",
        ]

        for var in deprecated_vars:
            if var in old_vars and var not in new_vars:
                print(f"   {var}={old_vars[var]} (removed)")

        print()

        # Step 5: Show file contents
        print("📄 Step 5: Configuration File Preview")
        print("-" * 30)

        print("📄 New Configuration File (first 20 lines):")
        with open(new_config_file, "r") as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:20], 1):
                print(f"   {i:2d}: {line.rstrip()}")

        if len(lines) > 20:
            print(f"   ... ({len(lines) - 20} more lines)")

        print()

        # Step 6: Show migration log
        print("📋 Step 6: Migration Log")
        print("-" * 30)

        log_files = list(temp_path.glob("migration_log_*.txt"))
        if log_files:
            log_file = log_files[0]
            print(f"📋 Migration Log ({log_file.name}):")
            with open(log_file, "r") as f:
                log_lines = f.readlines()
                for i, line in enumerate(log_lines[:15], 1):
                    print(f"   {i:2d}: {line.rstrip()}")

            if len(log_lines) > 15:
                print(f"   ... ({len(log_lines) - 15} more lines)")
        else:
            print("   No migration log found")

        print()

        # Final summary
        print("🎉 Migration Demonstration Complete!")
        print("=" * 50)
        print("✅ Configuration successfully migrated")
        print(f"✅ {len(old_vars)} variables processed")
        print(f"✅ {len(new_vars)} variables in final configuration")
        print(f"✅ {len(errors)} validation errors")
        print(f"✅ {len(warnings)} validation warnings")
        print()
        print("The migration tools are ready for production use!")

        return success and len(errors) == 0


if __name__ == "__main__":
    success = demonstrate_migration()
    exit(0 if success else 1)
