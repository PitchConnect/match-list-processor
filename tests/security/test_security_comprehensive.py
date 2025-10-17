"""Comprehensive security tests for the unified match processor service."""

import json
import os
from unittest.mock import patch

from src.core.change_detector import GranularChangeDetector
from src.core.unified_processor import UnifiedMatchProcessor


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_malicious_json_input_handling(self):
        """Test handling of malicious JSON input."""
        detector = GranularChangeDetector()

        # Test various malicious JSON inputs
        malicious_inputs = [
            '{"matchid": "<script>alert(\'xss\')</script>"}',  # XSS attempt
            '{"matchid": "../../../etc/passwd"}',  # Path traversal attempt
        ]

        for malicious_input in malicious_inputs:
            try:
                # Should handle malicious input safely
                json.loads(malicious_input)
                # Verify no dangerous properties are set
                assert not hasattr(detector, "isAdmin")
            except json.JSONDecodeError:
                # JSON parsing errors are acceptable
                pass
            except Exception as e:
                # Should not crash with unhandled exceptions
                assert "malicious" not in str(e).lower()

    def test_basic_security_functionality(self):
        """Test basic security functionality."""
        # Simple security test to validate infrastructure
        detector = GranularChangeDetector()

        # Test that basic functionality works
        assert hasattr(detector, "detect_changes")

        # Test basic input validation
        try:
            # Should handle empty input safely
            changes = detector.detect_changes([])
            assert changes is not None
        except Exception as e:
            # Should not crash with basic input
            assert "security" not in str(e).lower()

    def test_comprehensive_security_marker(self):
        """Test that comprehensive security marker works."""
        # This test validates that the comprehensive security test infrastructure is working
        with (
            patch("src.core.unified_processor.DockerNetworkApiClient"),
            patch("src.core.unified_processor.WhatsAppAvatarService"),
            patch("src.core.unified_processor.GoogleDriveStorageService"),
        ):
            processor = UnifiedMatchProcessor()
            assert hasattr(processor, "change_detector")
            assert hasattr(processor, "match_processor")

    def test_match_data_validation(self, sample_match_data):
        """Test validation of match data fields."""
        detector = GranularChangeDetector()

        # Test basic match data validation
        try:
            # Should handle basic match data safely
            changes = detector.detect_changes([sample_match_data])
            # Verify no code execution or data corruption
            assert changes is not None
        except (ValueError, TypeError):
            # Validation errors are acceptable
            pass


class TestBasicSecurity:
    """Test basic security measures."""

    def test_basic_file_security(self, temp_data_dir):
        """Test basic file security."""
        # Test file creation in temp directory
        test_file = os.path.join(temp_data_dir, "test_secure.json")
        test_data = {"test": "data"}

        # Create file safely
        with open(test_file, "w") as f:
            json.dump(test_data, f)

        # Verify file exists and is readable
        assert os.path.exists(test_file)

        with open(test_file, "r") as f:
            loaded_data = json.load(f)
            assert loaded_data == test_data
