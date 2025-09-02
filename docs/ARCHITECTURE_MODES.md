# Match List Processor - Architecture Modes

## 🏗️ Overview

The match-list-processor supports **two architectural modes** to provide flexibility for different deployment scenarios:

1. **Internal Orchestration** (Default) - Single service with integrated change detection
2. **Event-Driven** (Alternative) - Webhook-triggered processing with external integrations

## 🎯 Quick Start

### Default Mode (Recommended)
```bash
# Simple, self-contained processing
PROCESSOR_MODE=unified
python -m src.main
```

### Event-Driven Mode
```bash
# Webhook-triggered processing
PROCESSOR_MODE=event-driven
python -m src.main

# Service runs on http://localhost:8000
# Trigger processing: curl -X POST http://localhost:8000/process
```

## 📊 Architecture Comparison

| Feature | Internal Orchestration | Event-Driven |
|---------|----------------------|---------------|
| **Configuration** | `PROCESSOR_MODE=unified` | `PROCESSOR_MODE=event-driven` |
| **Services Required** | 1 (self-contained) | 1 (webhook server) |
| **External Dependencies** | None | Optional |
| **Triggering Method** | Internal scheduling | External webhooks |
| **Scaling Approach** | Vertical | Horizontal |
| **Deployment Complexity** | Low | Medium |
| **Resource Usage** | Efficient | On-demand |
| **Monitoring** | Built-in | HTTP endpoints |
| **Best For** | Standard deployments | Complex integrations |

## 🔧 Configuration Examples

### Internal Orchestration (Default)
```bash
# Environment variables
PROCESSOR_MODE=unified
RUN_MODE=service
SERVICE_INTERVAL=3600  # Process every hour
DATA_FOLDER=/data
TEMP_FILE_DIRECTORY=/tmp

# Docker
docker run -e PROCESSOR_MODE=unified match-processor

# Kubernetes
env:
- name: PROCESSOR_MODE
  value: "unified"
- name: SERVICE_INTERVAL
  value: "3600"
```

### Event-Driven Architecture
```bash
# Environment variables
PROCESSOR_MODE=event-driven
HOST=0.0.0.0
PORT=8000
DATA_FOLDER=/data
TEMP_FILE_DIRECTORY=/tmp

# Docker
docker run -p 8000:8000 -e PROCESSOR_MODE=event-driven match-processor

# Kubernetes
env:
- name: PROCESSOR_MODE
  value: "event-driven"
- name: PORT
  value: "8000"
ports:
- containerPort: 8000
```

## 🚀 Usage Examples

### Internal Orchestration
```bash
# Start the service
PROCESSOR_MODE=unified python -m src.main

# Service runs continuously, processing at configured intervals
# No external interaction needed
# Logs show processing status and results
```

### Event-Driven
```bash
# Start the webhook server
PROCESSOR_MODE=event-driven python -m src.main

# Server runs on http://localhost:8000
# Available endpoints:
curl http://localhost:8000/                    # Service info
curl http://localhost:8000/health              # Health check
curl http://localhost:8000/status              # Processing status
curl http://localhost:8000/metrics             # Performance metrics
curl -X POST http://localhost:8000/process     # Trigger processing
```

## 🎯 When to Use Each Mode

### Use Internal Orchestration When:
- ✅ You want **simplicity** and minimal configuration
- ✅ You prefer **self-contained** services with no external dependencies
- ✅ You need **reliable scheduling** with configurable intervals
- ✅ You're doing **standard match processing** workflows
- ✅ You want **easier deployment** and maintenance
- ✅ You have **resource constraints** and want efficiency

### Use Event-Driven When:
- ✅ You need **external triggering** from other services
- ✅ You want **real-time processing** triggered by events
- ✅ You require **horizontal scaling** capabilities
- ✅ You need **detailed monitoring** and metrics
- ✅ You have **complex integration** requirements
- ✅ You want **separation of concerns** between services

## 🔄 Migration Between Modes

### From Any Mode to Internal Orchestration
```bash
# Simple change - no deployment changes needed
PROCESSOR_MODE=unified
RUN_MODE=service
SERVICE_INTERVAL=3600
```

### From Any Mode to Event-Driven
```bash
# Requires port exposure and webhook configuration
PROCESSOR_MODE=event-driven
HOST=0.0.0.0
PORT=8000

# Update deployment to expose port 8000
# Configure external webhook triggers if needed
```

## 📈 Performance Characteristics

### Internal Orchestration
- **Resource Usage**: Consistent, predictable
- **Processing Latency**: Based on interval (default 1 hour)
- **Scalability**: Vertical scaling only
- **Monitoring**: Log-based
- **Reliability**: High (no external dependencies)

### Event-Driven
- **Resource Usage**: On-demand, efficient when idle
- **Processing Latency**: Near real-time (webhook triggered)
- **Scalability**: Horizontal scaling supported
- **Monitoring**: HTTP endpoints with detailed metrics
- **Reliability**: High with proper webhook configuration

## 🛠️ Troubleshooting

### Internal Orchestration Issues
```bash
# Check service status
docker logs match-processor

# Verify configuration
echo $PROCESSOR_MODE  # Should be "unified"
echo $SERVICE_INTERVAL  # Processing interval

# Test processing manually
PROCESSOR_MODE=unified python -m src.main
```

### Event-Driven Issues
```bash
# Check service health
curl http://localhost:8000/health

# Verify webhook endpoint
curl -X POST http://localhost:8000/process

# Check processing status
curl http://localhost:8000/status

# View metrics
curl http://localhost:8000/metrics
```

## 📚 Additional Resources

- **[Event-Driven Architecture Guide](EVENT_DRIVEN_ARCHITECTURE.md)** - Detailed implementation guide
- **[Configuration Reference](../README.md)** - Complete configuration options
- **[API Documentation](../src/app_event_driven.py)** - Event-driven API endpoints
- **[Deployment Examples](../docker/)** - Docker and Kubernetes examples

## 🎉 Summary

Both architectural modes provide robust, production-ready match processing capabilities:

- **Choose Internal Orchestration** for simplicity and reliability
- **Choose Event-Driven** for flexibility and advanced integrations
- **Switch between modes** easily with configuration changes
- **Full backward compatibility** maintained across all modes
