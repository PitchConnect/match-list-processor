# Migration Guide: Consolidated Service Architecture

This guide helps you migrate from the old architecture (with separate change detector service) to the new consolidated service architecture.

## 📋 Overview

The match-list-processor has been consolidated into a single unified service that includes:
- ✅ Integrated change detection (no external webhook dependency)
- ✅ Enhanced change categorization system
- ✅ Simplified deployment and configuration
- ✅ Improved performance and reliability

## 🔄 Migration Steps

### Step 1: Backup Current Configuration

```bash
# Backup your current configuration
cp docker-compose.yml docker-compose.yml.backup
cp .env .env.backup

# Backup data volumes
docker-compose down
docker run --rm -v process-matches-data:/data -v $(pwd)/backup:/backup alpine tar czf /backup/data-backup.tar.gz -C /data .
```

### Step 2: Update Docker Compose Configuration

The new `docker-compose.yml` removes the `match-list-change-detector` service:

```yaml
# REMOVED: This service is no longer needed
# match-list-change-detector:
#   image: ghcr.io/pitchconnect/match-list-change-detector:latest
#   ...

# UPDATED: Main service now includes change detection
services:
  process-matches-service:
    # ... existing configuration
    environment:
      - PROCESSOR_MODE=unified  # NEW: Unified processing mode
      - ENABLE_CHANGE_CATEGORIZATION=true  # NEW: Enhanced features
      # REMOVED: All webhook-related variables
```

### Step 3: Update Environment Variables

**Remove these deprecated variables:**
```bash
# OLD - Remove these from your .env file
WEBHOOK_URL=http://match-list-processor:8000/process
WEBHOOK_TIMEOUT=60
WEBHOOK_RETRY_COUNT=3
WEBHOOK_RETRY_DELAY=5
CHANGE_DETECTOR_ENABLED=true
```

**Add these new variables:**
```bash
# NEW - Add these to your .env file
PROCESSOR_MODE=unified
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical
ENABLE_CHANGE_LOGGING=true
```

### Step 4: Validate Configuration

Use the validation script to ensure your configuration is correct:

```bash
# Validate configuration
python3 scripts/validate_config.py --env-file .env

# Expected output: ✅ All validations passed!
```

### Step 5: Deploy Updated Service

```bash
# Pull latest images
docker-compose pull

# Deploy with new configuration
docker-compose up -d

# Verify services are running
docker-compose ps
docker-compose logs process-matches-service
```

### Step 6: Verify Migration Success

```bash
# Check health status
curl http://localhost:8000/health/simple

# Check logs for successful startup
docker-compose logs process-matches-service | grep "Unified processor started"

# Verify change detection is working
docker-compose logs process-matches-service | grep "Change detection enabled"
```

## 🔧 Configuration Changes

### Docker Compose Changes

| Component | Old Architecture | New Architecture |
|-----------|------------------|------------------|
| **Services** | 2 services (processor + detector) | 1 unified service |
| **Networking** | Webhook communication | Direct integration |
| **Dependencies** | Complex service dependencies | Simplified dependencies |
| **Health Checks** | Multiple health endpoints | Single health endpoint |

### Environment Variable Changes

| Variable | Status | Notes |
|----------|--------|-------|
| `WEBHOOK_URL` | ❌ Removed | No longer needed |
| `WEBHOOK_TIMEOUT` | ❌ Removed | No longer needed |
| `WEBHOOK_RETRY_COUNT` | ❌ Removed | No longer needed |
| `WEBHOOK_RETRY_DELAY` | ❌ Removed | No longer needed |
| `CHANGE_DETECTOR_ENABLED` | ❌ Removed | Always enabled in unified mode |
| `PROCESSOR_MODE` | ✅ New | Must be set to "unified" |
| `ENABLE_CHANGE_CATEGORIZATION` | ✅ New | Enables enhanced features |
| `CHANGE_PRIORITY_SAME_DAY` | ✅ New | Configures priority levels |

## 🚨 Breaking Changes

### 1. Service Architecture
- **Old**: Separate change detector service with webhook communication
- **New**: Integrated change detection within main service

### 2. Configuration Format
- **Old**: Webhook-based configuration
- **New**: Direct integration configuration

### 3. Health Checks
- **Old**: Multiple health endpoints across services
- **New**: Single unified health endpoint

### 4. Data Flow
- **Old**: API → Change Detector → Webhook → Processor
- **New**: API → Unified Processor (with integrated change detection)

## 🔍 Troubleshooting

### Common Migration Issues

#### Issue: Service fails to start
```bash
# Check logs
docker-compose logs process-matches-service

# Common causes:
# 1. Old environment variables still present
# 2. Missing required environment variables
# 3. Invalid configuration values
```

#### Issue: Change detection not working
```bash
# Verify configuration
grep -E "(PROCESSOR_MODE|ENABLE_CHANGE)" .env

# Should show:
# PROCESSOR_MODE=unified
# ENABLE_CHANGE_CATEGORIZATION=true
```

#### Issue: External services not accessible
```bash
# Test service connectivity
docker-compose exec process-matches-service curl -f http://fogis-api-client-service:8080/hello
docker-compose exec process-matches-service curl -f http://whatsapp-avatar-service:5002/health
```

### Rollback Procedure

If you need to rollback to the old architecture:

```bash
# Stop current services
docker-compose down

# Restore backup configuration
cp docker-compose.yml.backup docker-compose.yml
cp .env.backup .env

# Restore data if needed
docker run --rm -v process-matches-data:/data -v $(pwd)/backup:/backup alpine tar xzf /backup/data-backup.tar.gz -C /data

# Start with old configuration
docker-compose up -d
```

## ✅ Migration Checklist

- [ ] **Backup**: Current configuration and data backed up
- [ ] **Configuration**: Docker Compose updated to remove change detector service
- [ ] **Environment**: Old webhook variables removed, new unified variables added
- [ ] **Validation**: Configuration validated with validation script
- [ ] **Deployment**: New service deployed successfully
- [ ] **Health Check**: Service health endpoint responding
- [ ] **Functionality**: Change detection working correctly
- [ ] **Monitoring**: Logs showing successful operation
- [ ] **Cleanup**: Old service images and volumes cleaned up

## 📞 Support

If you encounter issues during migration:

1. **Check the logs**: `docker-compose logs process-matches-service`
2. **Validate configuration**: `python3 scripts/validate_config.py`
3. **Review this guide**: Ensure all steps were followed
4. **Check GitHub issues**: Look for similar migration issues
5. **Create an issue**: If problems persist, create a detailed issue report

## 🚀 Next Steps

After successful migration:

1. **Monitor Performance**: Watch for improved processing times
2. **Explore New Features**: Try the enhanced change categorization
3. **Prepare for Phase 2**: Get ready for the notification system
4. **Update Documentation**: Update any custom documentation or scripts

---

**Migration completed successfully?** 🎉 You're now running the consolidated service architecture and ready for Phase 2 development!
