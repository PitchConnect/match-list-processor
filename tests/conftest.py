"""Pytest configuration and shared fixtures."""

import json
import os
import tempfile
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from src.types import MatchDict, RefereeDict


@pytest.fixture
def sample_match_data() -> MatchDict:
    """Sample match data for testing."""
    return {
        "matchid": 6169105,
        "lag1namn": "IK Kongahälla",
        "lag2namn": "Motala AIF FK",
        "lag1lagid": 12345,
        "lag2lagid": 67890,
        "lag1foreningid": 111,
        "lag2foreningid": 222,
        "speldatum": "2025-06-14",
        "avsparkstid": "15:00",
        "tid": "2025-06-14T15:00:00",
        "tidsangivelse": "2025-06-14 15:00",
        "tavlingnamn": "Div 2 Norra Götaland, herr 2025",
        "anlaggningnamn": "Kongevi 1 Konstgräs",
        "anlaggningid": 333,
        "matchnr": "M001",
        "domaruppdraglista": [
            {
                "domarid": 1001,
                "personnamn": "John Doe",
                "namn": "John Doe",
                "domarrollnamn": "Huvuddomare",
            },
            {
                "domarid": 1002,
                "personnamn": "Jane Smith",
                "namn": "Jane Smith",
                "domarrollnamn": "Assisterande domare",
            },
        ],
    }


@pytest.fixture
def sample_referee_data() -> RefereeDict:
    """Sample referee data for testing."""
    return {
        "domarid": 1001,
        "personnamn": "John Doe",
        "namn": "John Doe",
        "domarrollnamn": "Huvuddomare",
    }


@pytest.fixture
def sample_matches_list(sample_match_data) -> list:
    """Sample list of matches for testing."""
    match2 = sample_match_data.copy()
    match2["matchid"] = 6169106
    match2["lag1namn"] = "Team A"
    match2["lag2namn"] = "Team B"
    return [sample_match_data, match2]


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_requests():
    """Mock requests module."""
    mock = Mock()
    mock.get.return_value.status_code = 200
    mock.get.return_value.json.return_value = []
    mock.post.return_value.status_code = 200
    mock.post.return_value.json.return_value = {
        "status": "success",
        "file_url": "http://example.com/file",
    }
    mock.post.return_value.headers = {"Content-Type": "image/png"}
    mock.post.return_value.content = b"fake_image_data"
    return mock


@pytest.fixture
def mock_api_client():
    """Mock API client."""
    mock = Mock()
    mock.fetch_matches_list.return_value = []
    return mock


@pytest.fixture
def mock_avatar_service():
    """Mock avatar service."""
    mock = Mock()
    mock.create_avatar.return_value = (b"fake_image_data", None)
    return mock


@pytest.fixture
def mock_storage_service():
    """Mock storage service."""
    mock = Mock()
    mock.upload_file.return_value = {
        "status": "success",
        "message": None,
        "file_url": "http://example.com/file",
    }
    return mock


@pytest.fixture
def mock_phonebook_service():
    """Mock phonebook service."""
    mock = Mock()
    mock.sync_contacts.return_value = True
    return mock


@pytest.fixture
def mock_description_generator():
    """Mock description generator function."""

    def generator(match_data):
        return f"Test description for {match_data['lag1namn']} vs {match_data['lag2namn']}"

    return generator


@pytest.fixture
def sample_json_file(temp_data_dir, sample_matches_list):
    """Create a sample JSON file with match data."""
    file_path = os.path.join(temp_data_dir, "test_matches.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(sample_matches_list, f, ensure_ascii=False)
    return file_path
