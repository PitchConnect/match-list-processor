"""Tests for data management functionality."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.core.data_manager import MatchDataManager


class TestMatchDataManager:
    """Test the MatchDataManager class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = MatchDataManager()
        assert manager.data_folder == "/data"
        assert manager.filename == "previous_matches.json"
        assert manager.file_path == "/data/previous_matches.json"

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        manager = MatchDataManager("/custom/data", "custom.json")
        assert manager.data_folder == "/custom/data"
        assert manager.filename == "custom.json"
        assert manager.file_path == "/custom/data/custom.json"

    def test_load_previous_matches_raw_json_success(self, temp_data_dir, sample_matches_list):
        """Test successful loading of previous matches."""
        # Create test file
        file_path = os.path.join(temp_data_dir, "test_matches.json")
        test_data = json.dumps(sample_matches_list, ensure_ascii=False)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(test_data)

        manager = MatchDataManager(temp_data_dir, "test_matches.json")
        result = manager.load_previous_matches_raw_json()

        assert result == test_data

    def test_load_previous_matches_raw_json_file_not_found(self, temp_data_dir):
        """Test loading when file doesn't exist."""
        manager = MatchDataManager(temp_data_dir, "nonexistent.json")
        result = manager.load_previous_matches_raw_json()

        assert result is None

    def test_load_previous_matches_raw_json_permission_error(self, temp_data_dir):
        """Test loading when file has permission issues."""
        # Create a file and make it unreadable
        file_path = os.path.join(temp_data_dir, "unreadable.json")
        with open(file_path, "w") as f:
            f.write('{"test": "data"}')
        os.chmod(file_path, 0o000)

        try:
            manager = MatchDataManager(temp_data_dir, "unreadable.json")
            result = manager.load_previous_matches_raw_json()
            assert result is None
        finally:
            # Restore permissions for cleanup
            os.chmod(file_path, 0o644)

    def test_parse_raw_json_to_list_success(self, sample_matches_list):
        """Test successful parsing of JSON string."""
        manager = MatchDataManager()
        raw_json = json.dumps(sample_matches_list, ensure_ascii=False)

        result = manager.parse_raw_json_to_list(raw_json)

        assert result == sample_matches_list
        assert len(result) == 2

    def test_parse_raw_json_to_list_empty_string(self):
        """Test parsing empty string."""
        manager = MatchDataManager()
        result = manager.parse_raw_json_to_list("")
        assert result == []

    def test_parse_raw_json_to_list_none(self):
        """Test parsing None."""
        manager = MatchDataManager()
        result = manager.parse_raw_json_to_list(None)
        assert result == []

    def test_parse_raw_json_to_list_invalid_json(self):
        """Test parsing invalid JSON."""
        manager = MatchDataManager()
        result = manager.parse_raw_json_to_list("invalid json {")
        assert result == []

    def test_save_current_matches_raw_json_success(self, temp_data_dir, sample_matches_list):
        """Test successful saving of matches."""
        manager = MatchDataManager(temp_data_dir, "output.json")
        raw_json = json.dumps(sample_matches_list, ensure_ascii=False)

        manager.save_current_matches_raw_json(raw_json)

        # Verify file was created and contains correct data
        assert os.path.exists(manager.file_path)
        with open(manager.file_path, "r", encoding="utf-8") as f:
            saved_data = f.read()
        assert saved_data == raw_json

    def test_save_current_matches_raw_json_creates_directory(self, temp_data_dir):
        """Test that saving creates the data directory if it doesn't exist."""
        nested_dir = os.path.join(temp_data_dir, "nested", "path")
        manager = MatchDataManager(nested_dir, "test.json")

        manager.save_current_matches_raw_json('{"test": "data"}')

        assert os.path.exists(nested_dir)
        assert os.path.exists(manager.file_path)

    def test_save_current_matches_raw_json_permission_error(self, temp_data_dir):
        """Test saving when directory is not writable."""
        # Make directory read-only
        os.chmod(temp_data_dir, 0o444)

        try:
            manager = MatchDataManager(temp_data_dir, "test.json")
            # This should not raise an exception, just log an error
            manager.save_current_matches_raw_json('{"test": "data"}')

            # File should not exist
            assert not os.path.exists(manager.file_path)
        finally:
            # Restore permissions for cleanup
            os.chmod(temp_data_dir, 0o755)
