"""Pytest configuration and shared fixtures for comprehensive test suite."""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch

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


# =============================================================================
# COMPREHENSIVE TEST FIXTURES FOR ENHANCED TEST SUITE
# =============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_external_services():
    """Mock all external service dependencies."""
    with (
        patch("src.services.api_client.APIClient") as mock_api,
        patch("src.services.calendar_sync.CalendarSyncService") as mock_calendar,
        patch("src.services.asset_generator.AssetGenerator") as mock_assets,
        patch("src.services.storage_service.StorageService") as mock_storage,
    ):

        # Configure API client mock
        mock_api.return_value.fetch_matches = AsyncMock(return_value=[])
        mock_api.return_value.is_healthy = AsyncMock(return_value=True)

        # Configure calendar sync mock
        mock_calendar.return_value.sync_matches = AsyncMock(return_value=True)
        mock_calendar.return_value.is_healthy = AsyncMock(return_value=True)

        # Configure asset generator mock
        mock_assets.return_value.generate_assets = AsyncMock(return_value=True)
        mock_assets.return_value.is_healthy = AsyncMock(return_value=True)

        # Configure storage service mock
        mock_storage.return_value.upload_files = AsyncMock(return_value=True)
        mock_storage.return_value.is_healthy = AsyncMock(return_value=True)

        yield {
            "api_client": mock_api.return_value,
            "calendar_sync": mock_calendar.return_value,
            "asset_generator": mock_assets.return_value,
            "storage_service": mock_storage.return_value,
        }


@pytest.fixture
def large_match_dataset():
    """Generate large dataset for performance testing."""
    matches = []
    for i in range(1000):
        match = {
            "matchid": i + 1000000,
            "lag1namn": f"Team A {i}",
            "lag2namn": f"Team B {i}",
            "lag1lagid": 10000 + i,
            "lag2lagid": 20000 + i,
            "speldatum": "2025-09-01",
            "avsparkstid": "15:00",
            "tid": "2025-09-01T15:00:00",
            "tavlingnamn": f"Competition {i % 10}",
            "anlaggningnamn": f"Venue {i % 50}",
            "domaruppdraglista": [
                {
                    "domarid": 1000 + (i * 2),
                    "personnamn": f"Referee {i * 2}",
                    "domarrollnamn": "Huvuddomare",
                }
            ],
        }
        matches.append(match)
    return matches


@pytest.fixture
def change_scenarios():
    """Provide various change scenarios for testing."""
    base_match = {
        "matchid": 6169105,
        "lag1namn": "IK Kongahälla",
        "lag2namn": "Motala AIF FK",
        "speldatum": "2025-06-14",
        "avsparkstid": "15:00",
        "anlaggningnamn": "Kongevi 1 Konstgräs",
        "domaruppdraglista": [
            {
                "domarid": 1001,
                "personnamn": "John Doe",
                "domarrollnamn": "Huvuddomare",
            }
        ],
    }

    return {
        "no_change": (base_match, base_match),
        "time_change": (
            base_match,
            {**base_match, "avsparkstid": "16:00", "tid": "2025-06-14T16:00:00"},
        ),
        "venue_change": (base_match, {**base_match, "anlaggningnamn": "New Venue"}),
        "referee_change": (
            base_match,
            {
                **base_match,
                "domaruppdraglista": [
                    {
                        "domarid": 1002,
                        "personnamn": "Jane Smith",
                        "domarrollnamn": "Huvuddomare",
                    }
                ],
            },
        ),
        "new_assignment": ({**base_match, "domaruppdraglista": []}, base_match),
        "cancellation": (base_match, {**base_match, "status": "cancelled"}),
    }


@pytest.fixture
def mock_configuration():
    """Mock configuration for testing."""
    return {
        "processor_mode": "unified",
        "run_mode": "service",
        "enable_change_categorization": True,
        "change_priority_same_day": "critical",
        "data_folder": "/tmp/test_data",
        "previous_matches_file": "test_previous_matches.json",
        "min_referees_for_whatsapp": 2,
        "log_level": "DEBUG",
    }


@pytest.fixture
def mock_health_responses():
    """Mock health check responses for external services."""
    return {
        "fogis-api-client": {
            "status": "healthy",
            "response_time": 45,
            "url": "http://fogis-api-client-service:8080",
        },
        "whatsapp-avatar-service": {
            "status": "healthy",
            "response_time": 23,
            "url": "http://whatsapp-avatar-service:5002",
        },
        "google-drive-service": {
            "status": "healthy",
            "response_time": 67,
            "url": "http://google-drive-service:5000",
        },
        "phonebook-sync-service": {
            "status": "healthy",
            "response_time": 34,
            "url": "http://fogis-calendar-phonebook-sync:5003",
        },
    }


@pytest.fixture
def performance_metrics():
    """Performance benchmarks for testing."""
    return {
        "max_processing_time": 30.0,  # seconds
        "max_change_detection_time": 1.0,  # seconds for 1000 matches
        "max_memory_increase": 100 * 1024 * 1024,  # 100MB
        "min_coverage_threshold": 90.0,  # percentage
        "max_test_execution_time": 180.0,  # seconds for full suite
    }


# =============================================================================
# NOTIFICATION SYSTEM FIXTURES
# =============================================================================


@pytest.fixture
def mock_notification_config():
    """Mock notification configuration for testing."""
    return {
        "enabled": True,
        "email": {
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "smtp_username": "test@example.com",
            "smtp_password": "password",
            "email_from": "fogis@example.com",
            "use_tls": True,
        },
        "discord": {
            "webhook_url": "https://discord.com/api/webhooks/test",
            "enabled": True,
        },
        "webhook": {
            "url": "https://api.example.com/webhook",
            "enabled": True,
            "headers": {"Authorization": "Bearer test-token"},
        },
        "delivery": {
            "max_retries": 3,
            "retry_delay": 5,
            "timeout": 30,
        },
        "analytics": {
            "enabled": True,
            "retention_days": 30,
        },
    }


@pytest.fixture
def mock_stakeholder():
    """Mock stakeholder for testing."""

    return {
        "stakeholder_id": "referee_12345",
        "name": "Bartek Svaberg",
        "role": "referee",
        "fogis_person_id": "12345",
        "contact_info": [
            {
                "channel": "email",
                "address": "bartek.svaberg@gmail.com",
                "verified": True,
                "active": True,
            }
        ],
        "preferences": {
            "enabled_channels": ["email"],
            "enabled_change_types": ["new_assignment", "referee_change"],
            "minimum_priority": "medium",
            "quiet_hours": {"start": "22:00", "end": "08:00"},
        },
        "created_at": "2025-09-01T12:00:00Z",
        "updated_at": "2025-09-01T12:00:00Z",
    }


@pytest.fixture
def multiple_stakeholders():
    """Multiple stakeholders for testing."""

    return [
        {
            "stakeholder_id": "referee_12345",
            "name": "Bartek Svaberg",
            "role": "referee",
            "fogis_person_id": "12345",
            "contact_info": [
                {
                    "channel": "email",
                    "address": "bartek.svaberg@gmail.com",
                    "verified": True,
                    "active": True,
                }
            ],
            "preferences": {
                "enabled_channels": ["email"],
                "enabled_change_types": ["new_assignment", "referee_change"],
                "minimum_priority": "medium",
            },
        },
        {
            "stakeholder_id": "referee_67890",
            "name": "Anna Andersson",
            "role": "referee",
            "fogis_person_id": "67890",
            "contact_info": [
                {
                    "channel": "email",
                    "address": "anna.andersson@example.com",
                    "verified": True,
                    "active": True,
                }
            ],
            "preferences": {
                "enabled_channels": ["email", "discord"],
                "enabled_change_types": ["new_assignment", "time_change", "venue_change"],
                "minimum_priority": "low",
            },
        },
    ]


@pytest.fixture
def mock_notification_service():
    """Mock notification service for testing."""
    mock_service = Mock()
    mock_service.enabled = True
    mock_service.process_changes = AsyncMock(
        return_value={
            "enabled": True,
            "notifications_sent": 1,
            "delivery_results": {"email": {"status": "sent", "recipients": 1}},
        }
    )
    mock_service.get_health_status = Mock(
        return_value={
            "status": "healthy",
            "enabled": True,
            "stakeholders_count": 5,
            "last_notification": "2025-09-01T12:00:00Z",
        }
    )
    return mock_service


@pytest.fixture
def sample_notification_data():
    """Sample notification data for testing."""
    from datetime import datetime, timezone

    return {
        "notification_id": "test-notification-123",
        "timestamp": datetime.now(timezone.utc),
        "change_category": "new_assignment",
        "priority": "high",
        "change_summary": "New referee assignment",
        "field_changes": [
            {
                "field": "domaruppdraglista",
                "old_value": [],
                "new_value": [{"personnamn": "John Doe", "domarrollnamn": "Huvuddomare"}],
                "description": "Referee assigned to match",
            }
        ],
        "match_context": {
            "matchid": 6169105,
            "lag1namn": "Team A",
            "lag2namn": "Team B",
            "speldatum": "2025-09-01",
            "avsparkstid": "15:00",
        },
        "affected_stakeholders": ["referee_12345"],
    }
