# Migration Guide: Issue #84 - Remove HTTP /sync Endpoint Calls

## Overview

Issue #84 removes all HTTP-based synchronization calls to the `fogis-calendar-phonebook-sync` service. Calendar synchronization is now handled exclusively via Redis pub/sub messaging.

## Breaking Changes

### 1. Removed Components

- **File**: `src/services/phonebook_service.py` (deleted)
  - Class: `FogisPhonebookSyncService`

- **Interface**: `src/interfaces.py`
  - Class: `PhonebookSyncInterface` (removed)

- **Config**: `src/config.py`
  - Field: `phonebook_sync_service_url` (removed)

- **Methods Removed**:
  - `_trigger_calendar_sync()` from `src/app_persistent.py`
  - `_trigger_calendar_sync()` from `src/core/unified_processor.py`
  - `sync_contacts()` calls from all app initialization

- **Config File**: `config/unified_processor.yml`
  - Section: `phonebook_sync` (removed)

### 2. Modified Components

- **Health Service**: `src/services/health_service.py`
  - Removed `phonebook-sync-service` from dependency checks

- **Unified Processor**: `src/core/unified_processor.py`
  - `_trigger_downstream_services()` now documents Redis pub/sub usage
  - No longer makes HTTP calls to calendar sync service

## Test Updates Required

The following test files need to be updated to remove `FogisPhonebookSyncService` mocking:

### Critical Test Files (19 total)

1. `tests/test_app.py` - Remove phonebook_service mocking from fixtures
2. `tests/test_app_persistent.py` - Remove FogisPhonebookSyncService patches
3. `tests/test_config.py` - Remove phonebook_sync_service_url assertions ✅ (DONE)
4. `tests/test_event_driven.py` - Remove phonebook_service references
5. `tests/test_health_integration.py` - Remove phonebook_service mocking
6. `tests/test_health_server.py` - Update health check expectations
7. `tests/test_health_service.py` - Remove phonebook-sync-service checks
8. `tests/test_integration.py` - Remove phonebook_service from workflows
9. `tests/test_referee_redis_integration.py` - Remove FogisPhonebookSyncService patches
10. `tests/test_unified_integration.py` - Remove phonebook_service mocking
11. `tests/test_unified_processor.py` - Remove _trigger_calendar_sync tests
12. `tests/integration/test_comprehensive_integration.py` - Remove phonebook mocking
13. `tests/integration/test_event_driven_integration.py` - Remove phonebook references
14. `tests/integration/test_semantic_notification_integration.py` - Remove phonebook mocking
15. `tests/integration/test_service_consolidation_e2e.py` - Remove phonebook assertions
16. `tests/performance/test_performance_comprehensive.py` - Remove phonebook mocking
17. `tests/security/test_security_comprehensive.py` - Remove phonebook mocking
18. `tests/unit/test_simple_coverage_90.py` - Remove phonebook service tests
19. `tests/unit/test_unified_processor_comprehensive.py` - Remove phonebook mocking

### Test Update Pattern

**Before:**
```python
@pytest.fixture
def mock_services(self):
    return {
        "api_client": Mock(),
        "phonebook_service": Mock(),  # REMOVE THIS
        "data_manager": Mock(),
        ...
    }

@pytest.fixture
def app_instance(self, mock_services):
    with (
        patch("src.app_persistent.DockerNetworkApiClient", ...),
        patch("src.app_persistent.FogisPhonebookSyncService", ...),  # REMOVE THIS
        patch("src.app_persistent.MatchDataManager", ...),
    ):
        app = PersistentMatchListProcessorApp()
        return app
```

**After:**
```python
@pytest.fixture
def mock_services(self):
    return {
        "api_client": Mock(),
        # phonebook_service removed (Issue #84)
        "data_manager": Mock(),
        ...
    }

@pytest.fixture
def app_instance(self, mock_services):
    with (
        patch("src.app_persistent.DockerNetworkApiClient", ...),
        # FogisPhonebookSyncService patch removed (Issue #84)
        patch("src.app_persistent.MatchDataManager", ...),
    ):
        app = PersistentMatchListProcessorApp()
        return app
```

## Migration Steps for Downstream Services

### Calendar Sync Service

The calendar sync service must now subscribe to Redis to receive match updates:

1. **Subscribe to Redis Channel**: `match_updates`
2. **Listen for Messages**: Enhanced Schema v2.0 format (from Issue #83)
3. **Process Updates**: Extract match data from `payload.matches`
4. **Remove HTTP Endpoint**: The `/sync` endpoint is no longer called

### Example Redis Subscriber (Python)

```python
import redis
import json

r = redis.Redis(host='redis', port=6379, decode_responses=True)
pubsub = r.pubsub()
pubsub.subscribe('match_updates')

for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        matches = data['payload']['matches']
        # Process matches...
```

## Deployment Considerations

### Prerequisites

1. **Redis must be running** and accessible to both services
2. **Calendar sync service must be updated** to subscribe to Redis
3. **Environment variables**: Remove `CALENDAR_SYNC_URL` and `PHONEBOOK_SYNC_SERVICE_URL`

### Deployment Order

1. Deploy calendar sync service with Redis subscription support
2. Verify calendar sync service is receiving Redis messages
3. Deploy match-list-processor with Issue #84 changes
4. Monitor logs to ensure no HTTP sync errors

### Rollback Plan

If issues occur:
1. Revert match-list-processor to previous version
2. Calendar sync service will continue working via Redis
3. HTTP endpoint can be re-enabled if needed

## Benefits

- ✅ **Decoupling**: Services no longer tightly coupled via HTTP
- ✅ **Resilience**: No synchronous dependencies between services
- ✅ **Scalability**: Event-driven architecture scales better
- ✅ **Performance**: Eliminates HTTP request overhead
- ✅ **Reliability**: Redis pub/sub is more reliable than HTTP polling

## Testing

### Manual Testing

1. Start Redis: `docker-compose up redis`
2. Start calendar sync service with Redis subscriber
3. Start match-list-processor
4. Trigger match processing
5. Verify calendar sync service receives updates via Redis
6. Check logs for any HTTP sync errors (should be none)

### Automated Testing

Run the test suite after updating test files:
```bash
pytest tests/ -v
```

Expected: All tests pass after removing phonebook_service mocking

## Support

For questions or issues:
- Create a GitHub issue
- Reference Issue #84
- Tag @maintainers

## Timeline

- **Issue Created**: 2025-10-16
- **Implementation**: 2025-10-16
- **Test Updates**: TBD (requires review)
- **Deployment**: After test updates complete
