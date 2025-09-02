# Event-Driven Architecture Guide

## Overview

The Event-Driven Architecture provides an **alternative architectural approach** for the match-list-processor, offering webhook-triggered persistent service capabilities alongside the default internal orchestration mode. This gives operational teams flexibility to choose the best approach for their deployment scenario.

## 🏗️ Architectural Decision Context

Following architectural analysis, the match-list-processor now supports **two complementary approaches**:

### **Architectural Decision Summary**
- **Primary Architecture**: Internal Orchestration (unified mode) - **RECOMMENDED**
- **Alternative Architecture**: Event-Driven (webhook mode) - **AVAILABLE**
- **Rationale**: Provides operational flexibility while maintaining simplicity as default

## 🏗️ Architectural Modes

### 1. **Internal Orchestration Mode** (Default - Recommended)
- **Configuration**: `PROCESSOR_MODE=unified`
- **Purpose**: Single-service architecture with integrated change detection
- **Benefits**: Minimal services, no external dependencies, simplified deployment
- **Use Case**: Standard deployments where simplicity is preferred
- **Status**: ✅ **Already implemented and production-ready**

### 2. **Event-Driven Mode** (Alternative - This Implementation)
- **Configuration**: `PROCESSOR_MODE=event-driven`
- **Purpose**: Webhook-triggered processing with external change detection
- **Benefits**: Separation of concerns, multiple trigger sources, horizontal scaling
- **Use Case**: Complex deployments requiring external triggering or multiple processors
- **Status**: ✅ **Newly implemented in this PR**

## 🎯 When to Use Each Mode

### Use **Internal Orchestration** (unified) when:
- ✅ You want **simplicity** and minimal service count
- ✅ You prefer **self-contained** processing with no external dependencies
- ✅ You need **reliable scheduling** with configurable intervals
- ✅ You want **easier deployment** and maintenance
- ✅ You're doing **standard match processing** workflows

### Use **Event-Driven** (webhook) when:
- ✅ You need **external triggering** from other services
- ✅ You want **separation of concerns** between change detection and processing
- ✅ You require **multiple processors** listening to the same change detector
- ✅ You need **horizontal scaling** capabilities
- ✅ You have **complex integration** requirements with external systems

## Architecture Components

### 1. Event-Driven Application (`app_event_driven.py`)

The main FastAPI application that provides:
- **Persistent Service**: Runs continuously, waiting for webhook triggers
- **Background Processing**: Non-blocking webhook processing
- **Health Monitoring**: Comprehensive health checks and status reporting
- **Metrics Collection**: Real-time processing metrics and performance tracking

### 2. Webhook Processing Service (`webhook_service.py`)

Core service that handles:
- **Smart Processing**: Only processes when changes are detected
- **Processing History**: Maintains history of processing cycles
- **Performance Metrics**: Tracks processing duration, success rates, and change detection rates
- **Error Handling**: Graceful error handling with detailed logging

### 3. Enhanced Main Entry Point (`main.py`)

Updated entry point that supports:
- **Multiple Modes**: Event-driven, unified, legacy, and service modes
- **Environment Configuration**: Automatic mode selection based on environment variables
- **Fallback Logic**: Graceful fallback between different processor modes

## API Endpoints

### Core Endpoints

#### `GET /`
Service information and current status
```json
{
  "service_name": "match-list-processor",
  "version": "2.0.0",
  "mode": "event-driven",
  "status": "running",
  "processing": false,
  "processing_count": 42,
  "last_processing_time": 1693123456.789
}
```

#### `POST /process`
Trigger webhook processing
```json
{
  "status": "success",
  "message": "Match processing triggered",
  "processing_count": 43
}
```

#### `GET /health`
Enhanced health check with dependency status
```json
{
  "service_name": "match-list-processor",
  "status": "healthy",
  "mode": "event-driven",
  "processing": false,
  "dependencies": {
    "api_client": "healthy",
    "storage_service": "healthy"
  },
  "timestamp": 1693123456.789
}
```

### Status and Monitoring Endpoints

#### `GET /status`
Current processing status and recent history
```json
{
  "processing_count": 42,
  "last_processing_time": 1693123456.789,
  "last_changes_detected": true,
  "processing_history": [...],
  "service_status": "ready",
  "currently_processing": false
}
```

#### `GET /status/detailed`
Detailed status with full history and configuration
```json
{
  "processing_count": 42,
  "processing_history": [...],
  "configuration": {
    "data_folder": "/data",
    "api_base_url": "http://api:8000"
  },
  "currently_processing": false
}
```

#### `GET /metrics`
Processing performance metrics
```json
{
  "total_processing_count": 42,
  "average_duration": 2.345,
  "success_rate": 0.976,
  "changes_detection_rate": 0.238,
  "currently_processing": false
}
```

## 🔧 Configuration Comparison

### Quick Configuration Reference

| Aspect | Internal Orchestration | Event-Driven |
|--------|----------------------|---------------|
| **Mode** | `PROCESSOR_MODE=unified` | `PROCESSOR_MODE=event-driven` |
| **Services** | 1 (self-contained) | 1 (webhook server) |
| **Dependencies** | None | Optional external change detector |
| **Triggering** | Internal scheduling | External webhooks |
| **Scaling** | Vertical | Horizontal |
| **Complexity** | Low | Medium |
| **Use Case** | Standard deployments | Complex integrations |

### Detailed Configuration

#### Internal Orchestration (Default - Recommended)
```bash
# Single service with integrated change detection
PROCESSOR_MODE=unified      # Default - recommended for most deployments
RUN_MODE=service           # Persistent service mode
SERVICE_INTERVAL=3600      # Processing interval in seconds (1 hour)

# Data configuration (same for both modes)
DATA_FOLDER=/data
TEMP_FILE_DIRECTORY=/tmp
```

#### Event-Driven Architecture (Alternative)
```bash
# Webhook-triggered processing
PROCESSOR_MODE=event-driven # Alternative - for complex deployments
HOST=0.0.0.0               # Server host
PORT=8000                  # Server port

# Data configuration (same for both modes)
DATA_FOLDER=/data
TEMP_FILE_DIRECTORY=/tmp
```

### Environment Variables

#### Service Configuration
```bash
# Server configuration
HOST=0.0.0.0               # Server host (default: 0.0.0.0)
PORT=8000                  # Server port (default: 8000)

# Data configuration
DATA_FOLDER=/data          # Data storage directory
TEMP_FILE_DIRECTORY=/tmp   # Temporary files directory
API_BASE_URL=http://api:8000  # API base URL
```

## Deployment

### Docker Deployment

#### Dockerfile Configuration
```dockerfile
# Use event-driven mode
ENV PROCESSOR_MODE=event-driven
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose port
EXPOSE 8000

# Start event-driven service
CMD ["python", "-m", "src.main"]
```

#### Docker Compose
```yaml
services:
  match-processor:
    build: .
    environment:
      - PROCESSOR_MODE=event-driven
      - HOST=0.0.0.0
      - PORT=8000
      - DATA_FOLDER=/data
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/simple"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: match-processor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: match-processor
  template:
    metadata:
      labels:
        app: match-processor
    spec:
      containers:
      - name: match-processor
        image: match-processor:latest
        env:
        - name: PROCESSOR_MODE
          value: "event-driven"
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/simple
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

## Usage Examples

### Triggering Processing

#### Using curl
```bash
# Trigger processing
curl -X POST http://localhost:8000/process

# Check status
curl http://localhost:8000/status

# Get metrics
curl http://localhost:8000/metrics
```

#### Using Python requests
```python
import requests

# Trigger processing
response = requests.post("http://localhost:8000/process")
print(response.json())

# Monitor status
status = requests.get("http://localhost:8000/status")
print(f"Processing count: {status.json()['processing_count']}")
```

### Monitoring and Alerting

#### Health Check Script
```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8000/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "Service is healthy"
    exit 0
else
    echo "Service is unhealthy (HTTP $RESPONSE)"
    exit 1
fi
```

#### Prometheus Metrics (Future Enhancement)
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'match-processor'
    static_configs:
      - targets: ['match-processor:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## Benefits

### Resource Optimization
- **Eliminates Polling**: No unnecessary processing cycles
- **On-Demand Processing**: Only processes when triggered
- **Persistent Service**: Avoids startup overhead for each processing cycle

### Operational Excellence
- **Real-Time Monitoring**: Live status and metrics
- **Health Checks**: Comprehensive dependency monitoring
- **Error Tracking**: Detailed error logging and history
- **Performance Metrics**: Processing duration and success rates

### Scalability
- **Horizontal Scaling**: Multiple instances can handle different webhooks
- **Load Balancing**: Standard HTTP load balancing applies
- **Resource Efficiency**: Minimal resource usage when idle

## 🚀 Deployment Comparison

### Docker Deployment

#### Internal Orchestration (Recommended)
```dockerfile
# Dockerfile for unified mode
ENV PROCESSOR_MODE=unified
ENV RUN_MODE=service
ENV SERVICE_INTERVAL=3600

# No port exposure needed (internal processing)
CMD ["python", "-m", "src.main"]
```

#### Event-Driven Architecture
```dockerfile
# Dockerfile for event-driven mode
ENV PROCESSOR_MODE=event-driven
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose webhook port
EXPOSE 8000
CMD ["python", "-m", "src.main"]
```

### Kubernetes Deployment

#### Internal Orchestration
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: match-processor-unified
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: match-processor
        env:
        - name: PROCESSOR_MODE
          value: "unified"
        - name: SERVICE_INTERVAL
          value: "3600"
        # No service/ingress needed
```

#### Event-Driven Architecture
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: match-processor-events
spec:
  replicas: 2  # Can scale horizontally
  template:
    spec:
      containers:
      - name: match-processor
        env:
        - name: PROCESSOR_MODE
          value: "event-driven"
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: match-processor-service
spec:
  ports:
  - port: 8000
    targetPort: 8000
```

## 🔄 Migration Guide

### Choosing Your Architecture

#### Migrate to Internal Orchestration (Recommended)
```bash
# Simple migration - just change mode
PROCESSOR_MODE=unified
RUN_MODE=service
SERVICE_INTERVAL=3600  # Adjust as needed
```

#### Migrate to Event-Driven (Advanced)
```bash
# For complex deployments
PROCESSOR_MODE=event-driven
HOST=0.0.0.0
PORT=8000

# Update deployment to expose port 8000
# Configure external webhook triggers
# Set up load balancing if needed
```

### Backward Compatibility

Both architectures maintain full backward compatibility:
- ✅ All existing processing logic is preserved
- ✅ Configuration remains the same
- ✅ Data formats and outputs are unchanged
- ✅ Can switch between modes without data migration
- ✅ Fallback to previous modes if needed

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker logs match-processor

# Verify configuration
curl http://localhost:8000/health
```

#### Processing Not Triggered
```bash
# Check if service is processing
curl http://localhost:8000/status

# Verify webhook endpoint
curl -X POST http://localhost:8000/process
```

#### Performance Issues
```bash
# Check metrics
curl http://localhost:8000/metrics

# Monitor processing history
curl http://localhost:8000/status/detailed
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

## Future Enhancements

### Planned Features
- **Webhook Authentication**: Secure webhook endpoints
- **Processing Queues**: Queue multiple processing requests
- **Prometheus Metrics**: Native Prometheus metrics export
- **Webhook Filtering**: Smart filtering based on webhook content
- **Auto-scaling**: Kubernetes-based auto-scaling support
