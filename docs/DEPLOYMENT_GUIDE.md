# Deployment Guide - Consolidated Match List Processor

**Updated: 2025-08-31 - Phase 1B Configuration Consolidation**

This guide covers deployment of the consolidated match-list-processor service with enhanced change categorization capabilities.

## 🏗️ Architecture Overview

### Consolidated Service Design
- **Single unified service** with integrated change detection
- **No webhook dependencies** (removed in Phase 1B)
- **Enhanced change categorization** system
- **Simplified deployment** with external service dependencies

### Key Changes from Previous Versions
- ✅ **Webhook dependencies removed** - No external change detector service needed
- ✅ **Enhanced change categorization** - Granular change analysis and priority assessment
- ✅ **Unified processor** - Single service handles all processing
- ✅ **Simplified configuration** - Fewer moving parts and dependencies

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Access to external services (FOGIS API, Google Drive, etc.)
- Network connectivity to `fogis-network`

### Basic Deployment
```bash
# 1. Clone the repository
git clone <repository-url>
cd match-list-processor

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your specific configuration

# 3. Validate configuration
./scripts/validate_deployment.sh

# 4. Start the service
docker compose up -d

# 5. Check health
curl http://localhost:8000/health/simple
```

## ⚙️ Configuration

### Environment Variables

#### Core Processor Settings
```bash
# Processor mode (unified is the only supported mode)
PROCESSOR_MODE=unified

# Run mode: 'service' for persistent operation, 'oneshot' for single execution
RUN_MODE=service
```

#### Enhanced Change Categorization
```bash
# Enable enhanced change categorization system
ENABLE_CHANGE_CATEGORIZATION=true

# Priority for same-day changes (critical, high, medium, low)
CHANGE_PRIORITY_SAME_DAY=critical

# Enable detailed change logging
ENABLE_CHANGE_LOGGING=true
```

#### Data Storage
```bash
# Data folder for persistent storage
DATA_FOLDER=/data

# Previous matches file for change detection
PREVIOUS_MATCHES_FILE=previous_matches.json
```

#### External Services
```bash
# Required external service URLs
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
WHATSAPP_AVATAR_SERVICE_URL=http://whatsapp-avatar-service:5002
GOOGLE_DRIVE_SERVICE_URL=http://google-drive-service:5000
PHONEBOOK_SYNC_SERVICE_URL=http://fogis-calendar-phonebook-sync:5003
```

### Docker Compose Configuration

The `docker-compose.yml` includes:
- **Unified service definition** with all necessary environment variables
- **Health checks** for service monitoring
- **Volume mounts** for persistent data
- **Network configuration** for service communication
- **Dependencies** on external services

## 🔧 Advanced Configuration

### Change Categorization Settings

The enhanced change categorization system supports:

#### Change Categories
- `NEW_ASSIGNMENT` - New referee assignments
- `REFEREE_CHANGE` - Changes to existing assignments
- `TIME_CHANGE` - Match time modifications
- `DATE_CHANGE` - Match date modifications
- `VENUE_CHANGE` - Venue/location changes
- `TEAM_CHANGE` - Team information changes
- `CANCELLATION` - Match cancellations
- `POSTPONEMENT` - Match postponements
- `INTERRUPTION` - Match interruptions

#### Priority Levels
- `CRITICAL` - Same-day changes, cancellations
- `HIGH` - Referee changes, time changes
- `MEDIUM` - Venue changes, team changes
- `LOW` - Competition changes, minor updates

#### Stakeholder Types
- `REFEREES` - Affected referees
- `COORDINATORS` - Match coordinators
- `TEAMS` - Participating teams
- `ALL` - All stakeholders

### Logging Configuration
```bash
# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Log format
LOG_FORMAT=%(asctime)s - %(levelname)s - %(message)s
```

## 🏥 Health Monitoring

### Health Check Endpoints
- **Simple health**: `GET /health/simple`
- **Detailed health**: `GET /health/detailed`

### Service Monitoring
```bash
# Check service status
docker compose ps

# View logs
docker compose logs process-matches-service

# Follow logs in real-time
docker compose logs -f process-matches-service
```

### Health Check Configuration
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/simple"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

## 🔄 Migration from Previous Versions

### From Webhook-Based Architecture
1. **Remove webhook configurations** - No longer needed
2. **Update environment variables** - Use new consolidated settings
3. **Restart services** - Deploy with new configuration
4. **Validate functionality** - Run deployment validation script

### Configuration Migration
```bash
# Old webhook variables (REMOVE THESE)
# WEBHOOK_URL=...
# WEBHOOK_SECRET=...

# New unified processor variables (ADD THESE)
PROCESSOR_MODE=unified
ENABLE_CHANGE_CATEGORIZATION=true
```

## 🧪 Testing and Validation

### Deployment Validation
```bash
# Run comprehensive validation
./scripts/validate_deployment.sh

# Test specific functionality
python3 -m pytest tests/test_change_categorization.py -v
python3 -m pytest tests/test_unified_processor.py -v
```

### Integration Testing
```bash
# Test with external services
docker compose up -d
curl http://localhost:8000/health/detailed

# Verify change categorization
# (Check logs for categorized changes)
docker compose logs process-matches-service | grep "ChangeCategory"
```

## 🚨 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check configuration syntax
docker compose config

# Check logs for errors
docker compose logs process-matches-service

# Validate environment variables
./scripts/validate_deployment.sh
```

#### External Service Dependencies
```bash
# Check external service connectivity
docker compose exec process-matches-service curl -f http://fogis-api-client-service:8080/hello

# Verify network configuration
docker network ls | grep fogis-network
```

#### Change Categorization Issues
```bash
# Check if enhanced features are enabled
docker compose exec process-matches-service python3 -c "from src.core.change_categorization import GranularChangeDetector; print('OK')"

# Verify configuration
grep ENABLE_CHANGE_CATEGORIZATION .env
```

### Performance Optimization

#### Resource Allocation
```yaml
# Add to docker-compose.yml if needed
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

#### Volume Optimization
```yaml
# Use named volumes for better performance
volumes:
  process-matches-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/data
```

## 📊 Monitoring and Metrics

### Key Metrics to Monitor
- **Service uptime** - Health check status
- **Change detection frequency** - Number of changes processed
- **Change categorization** - Distribution of change types and priorities
- **Processing time** - Time to process match lists
- **Error rates** - Failed processing attempts

### Log Analysis
```bash
# Monitor change categorization
docker compose logs process-matches-service | grep "MatchChangeDetail"

# Monitor processing cycles
docker compose logs process-matches-service | grep "Processing complete"

# Monitor errors
docker compose logs process-matches-service | grep "ERROR"
```

## 🔐 Security Considerations

### Network Security
- Services communicate within `fogis-network`
- External access only through defined ports
- Health checks use internal endpoints

### Data Security
- Persistent data stored in Docker volumes
- Environment variables for sensitive configuration
- No webhook endpoints exposed (removed in Phase 1B)

## 📈 Scaling and Performance

### Horizontal Scaling
The consolidated service is designed for single-instance deployment but can be scaled if needed:
```yaml
# Add to docker-compose.yml for scaling
deploy:
  replicas: 2
  update_config:
    parallelism: 1
    delay: 10s
```

### Performance Tuning
- **Memory allocation**: Adjust based on match list size
- **Processing frequency**: Configure based on update requirements
- **Change categorization**: Enable/disable based on needs

## 🎯 Production Deployment

### Production Checklist
- [ ] Environment variables configured
- [ ] External services accessible
- [ ] Health checks working
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Deployment validation passed

### Deployment Commands
```bash
# Production deployment
docker compose -f docker-compose.yml up -d

# Verify deployment
./scripts/validate_deployment.sh

# Monitor startup
docker compose logs -f process-matches-service
```

---

**For additional support or questions about deployment, please refer to the project documentation or contact the development team.**
