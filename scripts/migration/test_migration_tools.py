#!/usr/bin/env python3
"""
Test Suite for Migration Tools
Tests the migration tooling functionality
Issue #53: Migration Tooling and Scripts
"""

import os
import sys
import tempfile
import unittest

# Import our migration modules
sys.path.append(os.path.dirname(__file__))

from migrate_config import ConfigurationMigrator  # noqa: E402
from validate_migrated_config import MigratedConfigValidator  # noqa: E402


class TestConfigurationMigrator(unittest.TestCase):
    """Test the configuration migration utility."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.migrator = ConfigurationMigrator(self.temp_dir)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_env_file(self):
        """Test loading environment file."""
        # Create test .env file
        env_content = """
# Test environment file
CHANGE_DETECTOR_MODE=detector
DETECTOR_RUN_MODE=service
FOGIS_API_CLIENT_URL=http://localhost:8080
LOG_LEVEL=INFO
"""
        env_file = os.path.join(self.temp_dir, "test.env")
        with open(env_file, "w") as f:
            f.write(env_content)

        # Load and verify
        env_vars = self.migrator.load_env_file(env_file)

        self.assertEqual(env_vars["CHANGE_DETECTOR_MODE"], "detector")
        self.assertEqual(env_vars["DETECTOR_RUN_MODE"], "service")
        self.assertEqual(env_vars["FOGIS_API_CLIENT_URL"], "http://localhost:8080")
        self.assertEqual(env_vars["LOG_LEVEL"], "INFO")

    def test_migrate_environment_variables(self):
        """Test environment variable migration."""
        old_env = {
            "CHANGE_DETECTOR_MODE": "detector",
            "DETECTOR_RUN_MODE": "service",
            "DETECTOR_SERVICE_INTERVAL": "3600",
            "FOGIS_API_CLIENT_URL": "http://localhost:8080",
            "WEBHOOK_URL": "http://deprecated.webhook",  # Should be removed
            "CUSTOM_VAR": "custom_value",  # Should be preserved
        }

        new_env = self.migrator.migrate_environment_variables(old_env)

        # Check mappings
        self.assertEqual(new_env["PROCESSOR_MODE"], "unified")  # Default override
        self.assertEqual(new_env["RUN_MODE"], "service")
        self.assertEqual(new_env["SERVICE_INTERVAL"], "3600")
        self.assertEqual(new_env["FOGIS_API_CLIENT_URL"], "http://localhost:8080")

        # Check new defaults
        self.assertEqual(new_env["ENABLE_SEMANTIC_ANALYSIS"], "true")
        self.assertEqual(new_env["FALLBACK_TO_LEGACY"], "true")

        # Check preserved variables
        self.assertEqual(new_env["CUSTOM_VAR"], "custom_value")

        # Check deprecated variables are removed
        self.assertNotIn("WEBHOOK_URL", new_env)

    def test_validate_configuration(self):
        """Test configuration validation."""
        # Valid configuration
        valid_config = {
            "PROCESSOR_MODE": "unified",
            "RUN_MODE": "service",
            "DATA_FOLDER": "/data",
            "FOGIS_API_CLIENT_URL": "http://localhost:8080",
        }

        warnings = self.migrator.validate_configuration(valid_config)
        self.assertEqual(len(warnings), 0)

        # Invalid configuration
        invalid_config = {
            "PROCESSOR_MODE": "invalid",
            "RUN_MODE": "invalid",
            "FOGIS_API_CLIENT_URL": "not-a-url",
        }

        warnings = self.migrator.validate_configuration(invalid_config)
        self.assertGreater(len(warnings), 0)

    def test_save_env_file(self):
        """Test saving environment file."""
        env_vars = {
            "PROCESSOR_MODE": "unified",
            "RUN_MODE": "service",
            "DATA_FOLDER": "/data",
            "FOGIS_API_CLIENT_URL": "http://localhost:8080",
            "ENABLE_SEMANTIC_ANALYSIS": "true",
        }

        output_file = os.path.join(self.temp_dir, "output.env")
        self.migrator.save_env_file(env_vars, output_file)

        # Verify file was created and contains expected content
        self.assertTrue(os.path.exists(output_file))

        with open(output_file, "r") as f:
            content = f.read()
            self.assertIn("PROCESSOR_MODE=unified", content)
            self.assertIn("RUN_MODE=service", content)
            self.assertIn("# Service Configuration", content)  # Category header


class TestMigratedConfigValidator(unittest.TestCase):
    """Test the migrated configuration validator."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = MigratedConfigValidator()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_required_variables(self):
        """Test required variable validation."""
        # Valid configuration
        valid_env = {
            "PROCESSOR_MODE": "unified",
            "RUN_MODE": "service",
            "DATA_FOLDER": "/data",
            "FOGIS_API_CLIENT_URL": "http://localhost:8080",
        }

        self.validator.validate_required_variables(valid_env)
        self.assertEqual(len(self.validator.validation_errors), 0)

        # Invalid configuration
        self.validator.validation_errors = []
        invalid_env = {
            "PROCESSOR_MODE": "invalid",
            "RUN_MODE": "service",
            # Missing required variables
        }

        self.validator.validate_required_variables(invalid_env)
        self.assertGreater(len(self.validator.validation_errors), 0)

    def test_validate_urls(self):
        """Test URL validation."""
        env_vars = {
            "FOGIS_API_CLIENT_URL": "http://localhost:8080",
            "WHATSAPP_AVATAR_SERVICE_URL": "https://example.com:5002",
            "INVALID_URL": "not-a-url",
        }

        self.validator.validate_urls(env_vars)

        # Should have error for invalid URL
        errors = [e for e in self.validator.validation_errors if "not-a-url" in e]
        self.assertGreater(len(errors), 0)

    def test_validate_boolean_values(self):
        """Test boolean value validation."""
        env_vars = {
            "ENABLE_SEMANTIC_ANALYSIS": "true",
            "FALLBACK_TO_LEGACY": "false",
            "INVALID_BOOLEAN": "maybe",
        }

        self.validator.validate_boolean_values(env_vars)

        # Should have error for invalid boolean
        errors = [e for e in self.validator.validation_errors if "INVALID_BOOLEAN" in e]
        self.assertGreater(len(errors), 0)

    def test_complete_validation(self):
        """Test complete configuration validation."""
        # Create test configuration file
        config_content = """
PROCESSOR_MODE=unified
RUN_MODE=service
DATA_FOLDER=/data
FOGIS_API_CLIENT_URL=http://localhost:8080
ENABLE_SEMANTIC_ANALYSIS=true
FALLBACK_TO_LEGACY=true
LOG_LEVEL=INFO
"""
        config_file = os.path.join(self.temp_dir, "test.env")
        with open(config_file, "w") as f:
            f.write(config_content)

        success, errors, warnings = self.validator.validate_configuration(config_file)

        self.assertTrue(success)
        self.assertEqual(len(errors), 0)


class TestMigrationIntegration(unittest.TestCase):
    """Test integration between migration components."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_end_to_end_migration(self):
        """Test complete migration process."""
        # Create old configuration
        old_config_content = """
CHANGE_DETECTOR_MODE=detector
DETECTOR_RUN_MODE=service
DETECTOR_SERVICE_INTERVAL=3600
CHANGE_DETECTOR_DATA_FOLDER=/data
FOGIS_API_CLIENT_URL=http://localhost:8080
WEBHOOK_URL=http://deprecated.webhook
LOG_LEVEL=INFO
"""
        old_config_file = os.path.join(self.temp_dir, "old.env")
        with open(old_config_file, "w") as f:
            f.write(old_config_content)

        # Migrate configuration
        migrator = ConfigurationMigrator(self.temp_dir)
        new_config_file = os.path.join(self.temp_dir, "new.env")

        success = migrator.migrate(old_config_file, new_config_file)
        self.assertTrue(success)

        # Validate migrated configuration
        validator = MigratedConfigValidator()
        success, errors, warnings = validator.validate_configuration(new_config_file)

        self.assertTrue(success)
        self.assertEqual(len(errors), 0)

        # Verify specific migrations
        migrated_env = migrator.load_env_file(new_config_file)
        self.assertEqual(migrated_env["PROCESSOR_MODE"], "unified")
        self.assertEqual(migrated_env["RUN_MODE"], "service")
        self.assertEqual(migrated_env["SERVICE_INTERVAL"], "3600")
        self.assertNotIn("WEBHOOK_URL", migrated_env)
        self.assertIn("ENABLE_SEMANTIC_ANALYSIS", migrated_env)


def run_migration_tool_tests():
    """Run all migration tool tests."""
    print("🧪 Running Migration Tool Tests")
    print("=" * 40)

    # Create test suite
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTests(loader.loadTestsFromTestCase(TestConfigurationMigrator))
    test_suite.addTests(loader.loadTestsFromTestCase(TestMigratedConfigValidator))
    test_suite.addTests(loader.loadTestsFromTestCase(TestMigrationIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 40)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    success = len(result.failures) == 0 and len(result.errors) == 0
    print(f"\nOverall: {'✅ PASSED' if success else '❌ FAILED'}")

    return success


if __name__ == "__main__":
    success = run_migration_tool_tests()
    exit(0 if success else 1)
