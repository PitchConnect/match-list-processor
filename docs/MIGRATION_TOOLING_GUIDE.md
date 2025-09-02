# Migration Tooling Guide

## 🎯 Overview

This guide covers the comprehensive migration tooling developed for Issue #53 to seamlessly transition from the `match-list-change-detector` service to the unified `match-list-processor` service.

## 📁 Migration Tools Structure

```
scripts/migration/
├── migrate_to_unified_processor.sh    # Main migration script
├── migrate_config.py                  # Configuration migration utility
├── validate_migrated_config.py       # Configuration validation
├── validate_post_migration.py        # Post-migration validation
└── rollback_migration.sh             # Emergency rollback script
```

## 🚀 Quick Start

### Basic Migration

```bash
# Run complete migration with backup
./scripts/migration/migrate_to_unified_processor.sh

# Skip backup (not recommended for production)
./scripts/migration/migrate_to_unified_processor.sh --skip-backup

# Force migration even if validation fails
./scripts/migration/migrate_to_unified_processor.sh --force
```

### Emergency Rollback

```bash
# Rollback to previous state
./scripts/migration/rollback_migration.sh --backup-dir migration_backup_20250902_123456

# Rollback with data restoration
./scripts/migration/rollback_migration.sh --backup-dir migration_backup_20250902_123456 --restore-data
```

## 📋 Migration Process

### Phase 1: Pre-Migration Validation

The migration tool performs comprehensive pre-migration checks:

- ✅ **Prerequisites Check**: Docker, Docker Compose, Python 3
- ✅ **Service State Validation**: Current service status
- ✅ **Data Volume Check**: Existing data volumes
- ✅ **Network Connectivity**: Docker network validation
- ✅ **Configuration Validation**: Docker Compose file syntax

### Phase 2: Backup Creation

Automatic backup of current state:

```
migration_backup_YYYYMMDD_HHMMSS/
├── migration_metadata.json           # Migration metadata
├── docker-compose.yml                # Current Docker Compose
├── .env                              # Current environment variables
├── config/                           # Configuration directory
├── process-matches-data.tar.gz       # Data volume backup
└── migration_log_YYYYMMDD_HHMMSS.txt # Migration log
```

### Phase 3: Configuration Migration

Automated configuration transformation:

#### Environment Variable Mapping

| Old Variable | New Variable | Notes |
|-------------|-------------|-------|
| `CHANGE_DETECTOR_MODE` | `PROCESSOR_MODE` | Always set to "unified" |
| `DETECTOR_RUN_MODE` | `RUN_MODE` | service/oneshot |
| `DETECTOR_SERVICE_INTERVAL` | `SERVICE_INTERVAL` | Processing interval |
| `CHANGE_DETECTOR_DATA_FOLDER` | `DATA_FOLDER` | Data storage path |

#### New Unified Processor Variables

```bash
# Semantic Analysis Configuration
ENABLE_SEMANTIC_ANALYSIS=true
FALLBACK_TO_LEGACY=true

# Change Categorization
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical

# Delivery Monitoring
ENABLE_DELIVERY_MONITORING=true
```

#### Deprecated Variables (Removed)

- `WEBHOOK_URL`
- `WEBHOOK_SECRET`
- `WEBHOOK_ENABLED`
- `CHANGE_DETECTOR_WEBHOOK_PORT`
- `DETECTOR_WEBHOOK_HOST`

### Phase 4: Service Migration

1. **Stop Old Services**: Graceful shutdown of existing services
2. **Start New Services**: Deploy unified processor
3. **Network Setup**: Create required Docker networks and volumes
4. **Health Validation**: Verify service startup

### Phase 5: Post-Migration Validation

Comprehensive validation suite:

- ✅ **Service Health**: Basic and detailed health checks
- ✅ **Docker Services**: Container status validation
- ✅ **Data Integrity**: Data volume and file validation
- ✅ **Configuration**: Migrated configuration validation
- ✅ **Network Connectivity**: Service communication tests
- ✅ **Semantic Analysis**: Integration verification

## 🛠️ Individual Tools Usage

### Configuration Migration Utility

```bash
# Migrate configuration manually
python3 scripts/migration/migrate_config.py \
    --input .env \
    --output .env.migrated \
    --backup-dir backup_directory \
    --verbose
```

### Configuration Validation

```bash
# Validate migrated configuration
python3 scripts/migration/validate_migrated_config.py \
    --config .env.migrated \
    --verbose
```

### Post-Migration Validation

```bash
# Validate migration success
python3 scripts/migration/validate_post_migration.py \
    --backup-dir migration_backup_20250902_123456 \
    --service-url http://localhost:8000 \
    --verbose
```

## 🔧 Configuration Reference

### Required Variables

```bash
PROCESSOR_MODE=unified
RUN_MODE=service
DATA_FOLDER=/data
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
```

### Recommended Variables

```bash
SERVICE_INTERVAL=3600
MIN_REFEREES_FOR_WHATSAPP=2
LOG_LEVEL=INFO
TZ=Europe/Stockholm
```

### Service URLs

```bash
WHATSAPP_AVATAR_SERVICE_URL=http://whatsapp-avatar-service:5002
GOOGLE_DRIVE_SERVICE_URL=http://google-drive-service:5000
PHONEBOOK_SYNC_SERVICE_URL=http://fogis-calendar-phonebook-sync:5003
```

### Feature Flags

```bash
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical
ENABLE_SEMANTIC_ANALYSIS=true
FALLBACK_TO_LEGACY=true
ENABLE_DELIVERY_MONITORING=true
```

## 🚨 Troubleshooting

### Common Issues

#### Migration Fails at Configuration Validation

```bash
# Check configuration manually
python3 scripts/migration/validate_migrated_config.py --config .env --verbose

# Fix issues and retry
./scripts/migration/migrate_to_unified_processor.sh --skip-backup
```

#### Service Health Check Fails

```bash
# Check service logs
docker-compose logs -f process-matches-service

# Check service status
docker-compose ps

# Verify configuration
curl http://localhost:8000/health/simple
```

#### Data Volume Issues

```bash
# Check volume exists
docker volume ls | grep process-matches-data

# Inspect volume
docker volume inspect process-matches-data

# Restore from backup if needed
./scripts/migration/rollback_migration.sh --backup-dir BACKUP_DIR --restore-data
```

### Emergency Procedures

#### Immediate Rollback

```bash
# Find latest backup
ls -la migration_backup_*

# Rollback with data restoration
./scripts/migration/rollback_migration.sh \
    --backup-dir migration_backup_YYYYMMDD_HHMMSS \
    --restore-data \
    --force
```

#### Manual Service Recovery

```bash
# Stop all services
docker-compose down

# Remove problematic containers
docker container prune

# Restart services
docker-compose up -d

# Check health
curl http://localhost:8000/health/detailed
```

## 📊 Validation Reports

### Migration Log

Each migration creates a detailed log:

```
migration_log_YYYYMMDD_HHMMSS.txt
```

Contains:
- Configuration variable mappings
- Added default values
- Deprecated variables removed
- Validation warnings

### Post-Migration Report

JSON report with validation results:

```json
{
  "timestamp": "2025-09-02T12:34:56",
  "overall_success": true,
  "summary": {
    "total": 7,
    "passed": 7,
    "failed": 0
  },
  "validations": {
    "Service Health": {
      "success": true,
      "message": "Service health check passed"
    }
  }
}
```

## 🔒 Security Considerations

- **Backup Security**: Backups may contain sensitive configuration
- **Network Security**: Validate service URLs and network access
- **Data Protection**: Ensure data volume backups are secure
- **Access Control**: Restrict migration script execution

## 📈 Performance Impact

- **Migration Time**: Typically 2-5 minutes
- **Downtime**: ~30 seconds during service transition
- **Resource Usage**: Minimal additional resource requirements
- **Data Transfer**: Only configuration files, data remains in place

## ✅ Success Criteria

Migration is considered successful when:

- ✅ All validation checks pass
- ✅ Service health endpoints respond correctly
- ✅ Semantic analysis integration works
- ✅ No data loss or corruption
- ✅ All dependent services remain functional
- ✅ Performance within acceptable thresholds

## 📞 Support

For migration issues:

1. Check this documentation
2. Review migration logs
3. Run validation tools with `--verbose`
4. Use rollback procedures if needed
5. Consult troubleshooting section
