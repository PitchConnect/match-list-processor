# API Documentation - FOGIS Match List Processor

**Version: 2.0.0 (Phase 1B Consolidated Service)**
**Updated: 2025-08-31**

## Overview

The FOGIS Match List Processor provides a unified API for match processing, change detection, and health monitoring. This documentation covers all available endpoints and their usage.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the service operates without authentication for internal network usage. All endpoints are accessible within the `fogis-network` Docker network.

## Health Check Endpoints

### Simple Health Check

**Endpoint:** `GET /health/simple`

**Description:** Lightweight health check for load balancers and basic monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-31T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8000/health/simple
```

### Detailed Health Check

**Endpoint:** `GET /health/detailed`

**Description:** Comprehensive health information including service status, dependencies, and system information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-31T10:30:00Z",
  "service": {
    "name": "match-list-processor",
    "version": "2.0.0",
    "mode": "unified",
    "uptime": "2h 15m 30s"
  },
  "dependencies": {
    "fogis-api-client": {
      "status": "healthy",
      "url": "http://fogis-api-client-service:8080",
      "response_time": "45ms"
    },
    "whatsapp-avatar-service": {
      "status": "healthy",
      "url": "http://whatsapp-avatar-service:5002",
      "response_time": "23ms"
    },
    "google-drive-service": {
      "status": "healthy",
      "url": "http://google-drive-service:5000",
      "response_time": "67ms"
    },
    "phonebook-sync-service": {
      "status": "healthy",
      "url": "http://fogis-calendar-phonebook-sync:5003",
      "response_time": "34ms"
    }
  },
  "features": {
    "change_categorization": true,
    "unified_processor": true,
    "webhook_dependencies": false
  },
  "system": {
    "memory_usage": "245MB",
    "cpu_usage": "12%",
    "disk_usage": "1.2GB"
  }
}
```

**Status Codes:**
- `200 OK` - Service is healthy or degraded
- `503 Service Unavailable` - Service is unhealthy

**Example:**
```bash
curl http://localhost:8000/health/detailed
```

## Service Information

### Root Endpoint

**Endpoint:** `GET /`

**Description:** Basic service information and available endpoints.

**Response:**
```json
{
  "service": "FOGIS Match List Processor",
  "version": "2.0.0",
  "architecture": "unified",
  "phase": "1B",
  "description": "Consolidated service for match processing with enhanced change detection",
  "endpoints": {
    "health": {
      "simple": "/health/simple",
      "detailed": "/health/detailed"
    },
    "processing": {
      "manual_trigger": "/process"
    }
  },
  "features": [
    "Unified processor architecture",
    "Enhanced change categorization (11 types)",
    "Priority-based change assessment",
    "Stakeholder impact analysis",
    "WhatsApp asset generation",
    "Google Drive integration",
    "Calendar sync integration"
  ],
  "documentation": "/docs"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

## Processing Endpoints

### Manual Processing Trigger

**Endpoint:** `POST /process`

**Description:** Manually trigger a processing cycle for testing or immediate execution.

**Request Body:** (Optional)
```json
{
  "force": false,
  "dry_run": false
}
```

**Parameters:**
- `force` (boolean): Force processing even if no changes detected
- `dry_run` (boolean): Perform processing without making changes

**Response:**
```json
{
  "status": "success",
  "message": "Processing completed successfully",
  "processing_id": "proc_20250831_103000",
  "timestamp": "2025-08-31T10:30:00Z",
  "results": {
    "matches_processed": 45,
    "changes_detected": 3,
    "categorized_changes": [
      {
        "match_id": "123456",
        "category": "REFEREE_CHANGE",
        "priority": "HIGH",
        "affected_stakeholders": ["REFEREES", "COORDINATORS"],
        "description": "Referee changed from John Doe to Jane Smith"
      }
    ],
    "assets_generated": 2,
    "notifications_sent": 3
  }
}
```

**Status Codes:**
- `200 OK` - Processing completed successfully
- `202 Accepted` - Processing started (async)
- `400 Bad Request` - Invalid request parameters
- `500 Internal Server Error` - Processing failed

**Example:**
```bash
# Basic processing trigger
curl -X POST http://localhost:8000/process

# Force processing with dry run
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"force": true, "dry_run": true}'
```

## Change Detection API

### Change Categories

The service categorizes changes into the following types:

| Category | Description | Priority | Stakeholders |
|----------|-------------|----------|--------------|
| `NEW_ASSIGNMENT` | New referee assignments | HIGH | Referees, Coordinators |
| `REFEREE_CHANGE` | Changes to existing assignments | HIGH | Referees, Coordinators |
| `TIME_CHANGE` | Match time modifications | HIGH | All |
| `DATE_CHANGE` | Match date modifications | HIGH | All |
| `VENUE_CHANGE` | Venue/location changes | MEDIUM | All |
| `TEAM_CHANGE` | Team information changes | MEDIUM | Teams, Coordinators |
| `CANCELLATION` | Match cancellations | CRITICAL | All |
| `POSTPONEMENT` | Match postponements | MEDIUM | All |
| `INTERRUPTION` | Match interruptions | MEDIUM | All |
| `STATUS_CHANGE` | General status modifications | MEDIUM | All |
| `COMPETITION_CHANGE` | Competition-level changes | LOW | Coordinators |

### Priority Levels

- **CRITICAL**: Same-day changes, cancellations
- **HIGH**: Referee changes, time/date changes
- **MEDIUM**: Venue changes, team changes, postponements
- **LOW**: Competition changes, minor updates

### Stakeholder Types

- **REFEREES**: Affected referees
- **COORDINATORS**: Match coordinators
- **TEAMS**: Participating teams
- **ALL**: All stakeholders

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "PROCESSING_ERROR",
    "message": "Failed to process match list",
    "details": "Connection timeout to FOGIS API",
    "timestamp": "2025-08-31T10:30:00Z",
    "request_id": "req_20250831_103000"
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_REQUEST` | Invalid request parameters | 400 |
| `PROCESSING_ERROR` | Error during match processing | 500 |
| `DEPENDENCY_ERROR` | External service unavailable | 503 |
| `CONFIGURATION_ERROR` | Service misconfiguration | 500 |
| `TIMEOUT_ERROR` | Request timeout | 504 |

## Rate Limiting

Currently, no rate limiting is implemented as the service operates within a controlled internal network environment.

## Monitoring and Metrics

### Health Check Monitoring

- **Simple health checks** should be called every 30 seconds
- **Detailed health checks** should be called every 5 minutes
- **Dependency timeouts** are set to 10 seconds

### Log Monitoring

Key log patterns to monitor:

```bash
# Processing cycles
grep "Processing complete" logs/

# Change detection
grep "ChangeCategory" logs/

# Errors
grep "ERROR" logs/

# Health check failures
grep "Health check failed" logs/
```

## Integration Examples

### Docker Compose Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/simple"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health/simple
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3
```

### Kubernetes Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health/detailed
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

## API Versioning

The API follows semantic versioning:

- **Major version** (v2.x.x): Breaking changes, architectural updates
- **Minor version** (vX.1.x): New features, backward compatible
- **Patch version** (vX.X.1): Bug fixes, security updates

Current version: **v2.0.0** (Phase 1B Consolidated Service)

## Support

For API support and questions:

1. Check the [troubleshooting guide](DEPLOYMENT_GUIDE.md#troubleshooting)
2. Review [GitHub issues](https://github.com/PitchConnect/match-list-processor/issues)
3. Create a new issue with API-specific details

---

**API Documentation for FOGIS Match List Processor v2.0.0**
*Phase 1B Consolidated Service with Enhanced Change Detection*
