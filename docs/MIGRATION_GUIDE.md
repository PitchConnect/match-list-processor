# Migration Guide - Phase 1B Consolidated Service

**From: Webhook-based Architecture → To: Unified Processor with Enhanced Change Detection**

**Migration Date: 2025-08-31**
**Target Version: v2.0.0 (Phase 1B)**

## Overview

This guide helps you migrate from the previous webhook-based architecture to the new Phase 1B consolidated service with enhanced change detection capabilities.

## 🎯 Migration Benefits

### What You'll Gain

- **🏗️ Simplified Architecture**: Single unified service instead of multiple microservices
- **🔍 Enhanced Change Detection**: 11 granular change categories with priority assessment
- **⚡ Improved Performance**: Eliminates webhook latency and network overhead
- **🛡️ Enhanced Reliability**: Removes dependency on external webhook triggers
- **📊 Better Monitoring**: Unified logging and comprehensive health checks
- **🚀 Easier Deployment**: Single service configuration and management

### What's Removed

- **Webhook endpoints** and external change detector dependencies
- **Complex service-to-service communication** for change detection
- **Multiple configuration files** for different services
- **Webhook-related environment variables** and configuration

## 📋 Pre-Migration Checklist

### ✅ Prerequisites

- [ ] **Backup current configuration** and data
- [ ] **Review current deployment** and document custom settings
- [ ] **Verify external service dependencies** (FOGIS API, Google Drive, etc.)
- [ ] **Plan maintenance window** for migration
- [ ] **Test migration in staging environment** (recommended)

### ✅ Required Information

Gather the following from your current deployment:

- Current environment variables and configuration
- External service URLs and credentials
- Data volume locations and backup procedures
- Custom deployment scripts or configurations
- Monitoring and alerting configurations

## 🔄 Migration Steps

### Step 1: Backup Current Deployment

```bash
# Backup current configuration
cp .env .env.backup
cp docker-compose.yml docker-compose.yml.backup

# Backup data volumes
docker run --rm -v process-matches-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/process-matches-data-backup.tar.gz -C /data .

# Export current container state (optional)
docker commit process-matches-service process-matches-service:pre-migration
```

### Step 2: Stop Current Services

```bash
# Stop current services gracefully
docker compose down

# Verify all services are stopped
docker ps | grep process-matches
```

### Step 3: Update Repository

```bash
# Pull latest Phase 1B code
git fetch origin
git checkout main
git pull origin main

# Verify you're on Phase 1B version
git log --oneline -5 | grep "Phase 1B"
```

### Step 4: Update Configuration

#### Environment Variables Migration

**Remove these webhook-related variables:**
```bash
# OLD - Remove these from .env
WEBHOOK_URL=...
WEBHOOK_SECRET=...
CHANGE_DETECTOR_URL=...
```

**Add these new unified processor variables:**
```bash
# NEW - Add these to .env
PROCESSOR_MODE=unified
RUN_MODE=service
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical
ENABLE_CHANGE_LOGGING=true
```

#### Complete Environment Configuration

Use the new `.env.example` as a template:

```bash
# Copy new environment template
cp .env.example .env.new

# Migrate your existing settings to .env.new
# Then replace the old file
mv .env.new .env
```

**Key configuration sections:**

```bash
# =============================================================================
# UNIFIED PROCESSOR CONFIGURATION
# =============================================================================
PROCESSOR_MODE=unified
RUN_MODE=service

# =============================================================================
# ENHANCED CHANGE CATEGORIZATION
# =============================================================================
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical
ENABLE_CHANGE_LOGGING=true

# =============================================================================
# EXTERNAL SERVICE URLS (Update with your values)
# =============================================================================
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
WHATSAPP_AVATAR_SERVICE_URL=http://whatsapp-avatar-service:5002
GOOGLE_DRIVE_SERVICE_URL=http://google-drive-service:5000
PHONEBOOK_SYNC_SERVICE_URL=http://fogis-calendar-phonebook-sync:5003
```

### Step 5: Validate Configuration

```bash
# Run deployment validation
./scripts/validate_deployment.sh

# Expected output:
# ✅ Configuration files present and valid
# ✅ Docker configuration optimized for consolidated service
# ✅ Environment variables updated for Phase 1B
# ✅ No webhook dependencies found
# ✅ Enhanced change categorization configured
```

### Step 6: Deploy New Service

```bash
# Start the new unified service
docker compose up -d

# Monitor startup logs
docker compose logs -f process-matches-service

# Verify health
curl http://localhost:8000/health/simple
```

### Step 7: Verify Migration

```bash
# Check service status
curl http://localhost:8000/health/detailed

# Verify enhanced change categorization
docker compose logs process-matches-service | grep "ENABLE_CHANGE_CATEGORIZATION"

# Test processing cycle
curl -X POST http://localhost:8000/process -d '{"dry_run": true}'
```

## 🔧 Configuration Mapping

### Environment Variable Changes

| Old Variable | New Variable | Notes |
|--------------|--------------|-------|
| `WEBHOOK_URL` | *(removed)* | No longer needed |
| `WEBHOOK_SECRET` | *(removed)* | No longer needed |
| `CHANGE_DETECTOR_URL` | *(removed)* | Integrated into service |
| *(new)* | `PROCESSOR_MODE=unified` | Always set to 'unified' |
| *(new)* | `ENABLE_CHANGE_CATEGORIZATION=true` | Enable enhanced features |
| *(new)* | `CHANGE_PRIORITY_SAME_DAY=critical` | Priority configuration |

### Docker Compose Changes

**Removed sections:**
- Webhook-related environment variables
- External change detector service dependencies
- Webhook endpoint configurations

**Added sections:**
- Enhanced change categorization settings
- Unified processor configuration
- Comprehensive environment variable documentation

## 🧪 Testing Migration

### Functional Testing

```bash
# 1. Test health endpoints
curl http://localhost:8000/health/simple
curl http://localhost:8000/health/detailed

# 2. Test manual processing
curl -X POST http://localhost:8000/process -d '{"dry_run": true}'

# 3. Verify change detection
# (Monitor logs for change categorization activity)
docker compose logs process-matches-service | grep "ChangeCategory"

# 4. Test external service connectivity
docker compose exec process-matches-service curl -f http://fogis-api-client-service:8080/hello
```

### Performance Testing

```bash
# Monitor resource usage
docker stats process-matches-service

# Check processing times
docker compose logs process-matches-service | grep "Processing complete"

# Verify memory usage
docker compose exec process-matches-service ps aux
```

## 🚨 Troubleshooting

### Common Migration Issues

#### Service Won't Start

**Symptoms:** Container exits immediately or fails to start

**Solutions:**
```bash
# Check configuration syntax
./scripts/validate_deployment.sh

# Review startup logs
docker compose logs process-matches-service

# Verify environment variables
docker compose exec process-matches-service env | grep PROCESSOR_MODE
```

#### External Service Connectivity Issues

**Symptoms:** Health checks show degraded status

**Solutions:**
```bash
# Test external service connectivity
docker compose exec process-matches-service curl -f http://fogis-api-client-service:8080/hello

# Check network configuration
docker network ls | grep fogis-network

# Verify service URLs in environment
grep "_URL" .env
```

#### Change Detection Not Working

**Symptoms:** No change categorization in logs

**Solutions:**
```bash
# Verify enhanced features are enabled
grep ENABLE_CHANGE_CATEGORIZATION .env

# Check change detection imports
docker compose exec process-matches-service python3 -c "from src.core.change_categorization import GranularChangeDetector; print('OK')"

# Review change detection logs
docker compose logs process-matches-service | grep -i change
```

### Rollback Procedure

If migration fails, you can rollback:

```bash
# Stop new service
docker compose down

# Restore backup configuration
cp .env.backup .env
cp docker-compose.yml.backup docker-compose.yml

# Restore data (if needed)
docker run --rm -v process-matches-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/process-matches-data-backup.tar.gz -C /data

# Start previous version
docker compose up -d
```

## ✅ Post-Migration Validation

### Verification Checklist

- [ ] **Service starts successfully** without errors
- [ ] **Health checks pass** (`/health/simple` and `/health/detailed`)
- [ ] **External services accessible** (FOGIS API, Google Drive, etc.)
- [ ] **Change categorization working** (check logs for `ChangeCategory`)
- [ ] **Processing cycles complete** successfully
- [ ] **Asset generation working** (WhatsApp descriptions, avatars)
- [ ] **Monitoring and alerting** updated for new endpoints
- [ ] **Documentation updated** for team members

### Performance Validation

- [ ] **Startup time** improved (single service vs. multiple)
- [ ] **Memory usage** optimized for unified architecture
- [ ] **Processing time** maintained or improved
- [ ] **Error rates** reduced (fewer service dependencies)
- [ ] **Log volume** manageable with enhanced categorization

## 📊 Monitoring Updates

### Update Monitoring Configuration

**Health Check URLs:**
- Old: Multiple service health checks
- New: Single service health checks at `/health/simple` and `/health/detailed`

**Log Monitoring:**
- Add monitoring for `ChangeCategory` log entries
- Monitor enhanced change detection activity
- Update alerting for unified service architecture

**Metrics:**
- Update dashboards for single service metrics
- Add change categorization metrics
- Monitor stakeholder impact analysis

## 🎯 Next Steps

After successful migration:

1. **Update documentation** for your team
2. **Train team members** on new enhanced change detection features
3. **Configure monitoring** for change categorization metrics
4. **Plan Phase 2** notification system integration
5. **Remove old backup files** after validation period

## 📞 Support

If you encounter issues during migration:

1. **Check troubleshooting section** above
2. **Review deployment validation** output
3. **Check GitHub issues** for similar problems
4. **Create support issue** with migration details

---

**Migration Guide for FOGIS Match List Processor Phase 1B**
*From Webhook Architecture to Unified Processor with Enhanced Change Detection*

**Questions? Check the [Deployment Guide](DEPLOYMENT_GUIDE.md) or create a GitHub issue.**
