# Health Check Documentation

## Overview

The match-list-processor service includes a comprehensive health check system that monitors the service status and its dependencies. The health check endpoints are essential for monitoring, orchestration, and automated recovery in production environments.

## Health Check Endpoints

### Base URL
When running locally: `http://localhost:8000`
When running in Docker: `http://container-name:8000`

### Available Endpoints

#### 1. Root Endpoint - `/`
Returns basic service information and available endpoints.

**Response:**
```json
{
  "service": "match-list-processor",
  "version": "1.0.0",
  "health_endpoint": "/health",
  "simple_health_endpoint": "/health/simple",
  "dependencies_endpoint": "/health/dependencies"
}
```

#### 2. Simple Health Check - `/health/simple`
Lightweight health check without dependency verification. Ideal for Docker health checks.

**Response:**
```json
{
  "service_name": "match-list-processor",
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

**Status Codes:**
- `200 OK`: Service is running

#### 3. Comprehensive Health Check - `/health`
Complete health check including dependency status verification.

**Response:**
```json
{
  "service_name": "match-list-processor",
  "version": "1.0.0",
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "timestamp": "2024-01-01T12:00:00.000Z",
  "dependencies": {
    "fogis-api-client": {
      "name": "fogis-api-client",
      "url": "http://fogis-api-client-service:8080/hello",
      "status": "healthy",
      "response_time_ms": 45.2,
      "error": null,
      "last_checked": "2024-01-01T12:00:00.000Z"
    },
    "whatsapp-avatar-service": {
      "name": "whatsapp-avatar-service",
      "url": "http://whatsapp-avatar-service:5002/health",
      "status": "unhealthy",
      "response_time_ms": 5000.0,
      "error": "Request timeout",
      "last_checked": "2024-01-01T12:00:00.000Z"
    }
  },
  "details": {
    "data_folder": "/data",
    "min_referees_for_whatsapp": 2,
    "log_level": "INFO",
    "python_version": "3.9+",
    "environment": "production"
  }
}
```

**Status Codes:**
- `200 OK`: Service is healthy or degraded but operational
- `503 Service Unavailable`: Service is unhealthy

**Status Values:**
- `healthy`: All dependencies are working
- `degraded`: Some dependencies are failing but service is still operational (≥50% healthy)
- `unhealthy`: Most dependencies are failing (<50% healthy)

#### 4. Dependencies Only - `/health/dependencies`
Check only the status of service dependencies.

**Response:**
```json
{
  "dependencies": {
    "fogis-api-client": {
      "name": "fogis-api-client",
      "url": "http://fogis-api-client-service:8080/hello",
      "status": "healthy",
      "response_time_ms": 45.2,
      "error": null,
      "last_checked": "2024-01-01T12:00:00.000Z"
    }
  }
}
```

**Status Codes:**
- `200 OK`: Dependencies checked (individual status in response)
- `500 Internal Server Error`: Dependencies check failed

## Monitored Dependencies

The health check system monitors the following service dependencies:

1. **fogis-api-client-service** (`http://fogis-api-client-service:8080/hello`)
   - Provides match data from Fogis API
   - Timeout: 5 seconds

2. **whatsapp-avatar-service** (`http://whatsapp-avatar-service:5002/health`)
   - Generates WhatsApp group avatars
   - Timeout: 5 seconds

3. **google-drive-service** (`http://google-drive-service:5000/health`)
   - Handles file uploads to Google Drive
   - Timeout: 5 seconds

4. **phonebook-sync-service** (`http://fogis-calendar-phonebook-sync:5003/health`)
   - Synchronizes contact information
   - Timeout: 5 seconds

## Docker Integration

### Dockerfile Health Check
The service includes a built-in Docker health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/simple || exit 1
```

### Docker Compose Configuration
```yaml
services:
  process-matches-service:
    # ... other configuration
    ports:
      - "8000:8000"  # Health check endpoint
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/simple"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### Health Check Parameters
- **Interval**: 30 seconds between checks
- **Timeout**: 10 seconds maximum response time
- **Start Period**: 30 seconds grace period during startup
- **Retries**: 3 consecutive failures before marking unhealthy

## Monitoring and Alerting

### Recommended Monitoring
1. **Basic Availability**: Monitor `/health/simple` for service availability
2. **Dependency Health**: Monitor `/health` for comprehensive status
3. **Response Time**: Track response times for performance monitoring
4. **Error Rates**: Monitor for 5xx responses indicating service issues

### Alert Conditions
- Service returns 503 status code
- Response time exceeds 5 seconds
- Multiple dependency failures (degraded status)
- Health check endpoint becomes unreachable

## Usage Examples

### cURL Commands
```bash
# Simple health check
curl -f http://localhost:8000/health/simple

# Comprehensive health check
curl -f http://localhost:8000/health

# Dependencies only
curl -f http://localhost:8000/health/dependencies

# Check with timeout
curl -f --max-time 5 http://localhost:8000/health/simple
```

### Python Example
```python
import requests

def check_service_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"Service status: {data['status']}")
            return data['status'] == 'healthy'
        else:
            print(f"Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Health check error: {e}")
        return False
```

### Kubernetes Probes
```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: match-list-processor
    livenessProbe:
      httpGet:
        path: /health/simple
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 30
      timeoutSeconds: 10
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 2
```

## Troubleshooting

### Common Issues

1. **Health endpoint not responding**
   - Check if service is running: `docker ps`
   - Verify port 8000 is exposed: `docker port container-name`
   - Check service logs: `docker logs container-name`

2. **Dependencies showing as unhealthy**
   - Verify dependent services are running
   - Check network connectivity between containers
   - Review service-specific health endpoints

3. **Slow response times**
   - Check system resources (CPU, memory)
   - Review dependency response times
   - Consider increasing timeout values

### Debug Commands
```bash
# Check if health server is running
curl -v http://localhost:8000/

# Test dependency connectivity
docker exec container-name curl -f http://dependency-service:port/health

# View detailed logs
docker logs -f container-name

# Check container health status
docker inspect container-name | grep -A 10 "Health"
```

## Configuration

Health check behavior can be configured through environment variables:

- `LOG_LEVEL`: Controls logging verbosity (default: INFO)
- Service URLs can be configured via their respective environment variables
- Timeout values are currently hardcoded to 5 seconds per dependency

For production deployments, ensure all dependent services have their health endpoints properly configured and accessible.
