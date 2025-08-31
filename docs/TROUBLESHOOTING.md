# Troubleshooting Guide - FOGIS Match List Processor

**Version: 2.0.0 (Phase 1B Consolidated Service)**
**Updated: 2025-08-31**

## Overview

This guide provides solutions for common issues with the FOGIS Match List Processor unified service. The troubleshooting steps are organized by symptom and include both quick fixes and detailed diagnostic procedures.

## 🚨 Quick Diagnostic Commands

### Service Status Check

```bash
# Check if service is running
docker compose ps

# Check service health
curl http://localhost:8000/health/simple

# Get detailed health information
curl http://localhost:8000/health/detailed

# View recent logs
docker compose logs --tail=50 process-matches-service
```

### Configuration Validation

```bash
# Run comprehensive validation
./scripts/validate_deployment.sh

# Check environment variables
docker compose exec process-matches-service env | grep -E "(PROCESSOR_MODE|ENABLE_CHANGE)"

# Validate Docker Compose syntax
docker compose config
```

## 🔧 Common Issues and Solutions

### 1. Service Won't Start

#### Symptoms
- Container exits immediately
- Service fails to start
- Health checks fail

#### Diagnostic Steps

```bash
# Check container status
docker compose ps

# View startup logs
docker compose logs process-matches-service

# Check for configuration errors
./scripts/validate_deployment.sh

# Verify environment variables
docker compose config
```

#### Common Causes and Solutions

**Configuration Syntax Error:**
```bash
# Check Docker Compose syntax
docker compose config

# Fix syntax errors in docker-compose.yml or .env
# Common issues: missing quotes, invalid YAML indentation
```

**Missing Environment Variables:**
```bash
# Check required variables
grep -E "(PROCESSOR_MODE|FOGIS_API_CLIENT_URL)" .env

# Copy from template if missing
cp .env.example .env
# Edit with your values
```

**Port Conflicts:**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Change port in docker-compose.yml if needed
ports:
  - "8001:8000"  # Use different host port
```

**Volume Permission Issues:**
```bash
# Fix volume permissions
sudo chown -R 1000:1000 data/
sudo chmod 755 data/
```

### 2. External Service Connectivity Issues

#### Symptoms
- Health checks show "degraded" status
- Processing fails with connection errors
- External service timeouts

#### Diagnostic Steps

```bash
# Test external service connectivity
docker compose exec process-matches-service curl -f http://fogis-api-client-service:8080/hello
docker compose exec process-matches-service curl -f http://whatsapp-avatar-service:5002/health
docker compose exec process-matches-service curl -f http://google-drive-service:5000/health

# Check network connectivity
docker network ls | grep fogis-network
docker network inspect fogis-network
```

#### Solutions

**Service Not Running:**
```bash
# Check if external services are running
docker ps | grep -E "(fogis-api|whatsapp-avatar|google-drive)"

# Start missing services
docker compose -f ../fogis_api_client_python/docker-compose.yml up -d
docker compose -f ../TeamLogoCombiner/docker-compose.yml up -d
```

**Network Issues:**
```bash
# Recreate network if needed
docker network rm fogis-network
docker network create fogis-network

# Restart services
docker compose down && docker compose up -d
```

**Wrong Service URLs:**
```bash
# Verify service URLs in environment
grep "_URL" .env

# Update URLs to match actual service names
FOGIS_API_CLIENT_URL=http://fogis-api-client-service:8080
```

### 3. Change Detection Not Working

#### Symptoms
- No change categorization in logs
- Changes not being detected
- Missing `ChangeCategory` log entries

#### Diagnostic Steps

```bash
# Check if enhanced features are enabled
grep ENABLE_CHANGE_CATEGORIZATION .env

# Verify change detection imports
docker compose exec process-matches-service python3 -c "from src.core.change_categorization import GranularChangeDetector; print('OK')"

# Look for change detection logs
docker compose logs process-matches-service | grep -i "change"
docker compose logs process-matches-service | grep "ChangeCategory"
```

#### Solutions

**Enhanced Features Disabled:**
```bash
# Enable change categorization in .env
ENABLE_CHANGE_CATEGORIZATION=true
CHANGE_PRIORITY_SAME_DAY=critical

# Restart service
docker compose restart process-matches-service
```

**Import Errors:**
```bash
# Check Python dependencies
docker compose exec process-matches-service pip list | grep -E "(pydantic|datetime)"

# Rebuild container if needed
docker compose build --no-cache process-matches-service
```

**No Changes to Detect:**
```bash
# Force processing to test change detection
curl -X POST http://localhost:8000/process -d '{"force": true, "dry_run": true}'

# Check if previous matches file exists
docker compose exec process-matches-service ls -la /data/previous_matches.json
```

### 4. Processing Failures

#### Symptoms
- Processing cycles fail
- Errors in processing logs
- Assets not generated

#### Diagnostic Steps

```bash
# Check processing logs
docker compose logs process-matches-service | grep -E "(Processing|ERROR)"

# Test manual processing
curl -X POST http://localhost:8000/process -d '{"dry_run": true}'

# Check data directory
docker compose exec process-matches-service ls -la /data/
```

#### Solutions

**Data Directory Issues:**
```bash
# Check data directory permissions
docker compose exec process-matches-service ls -la /data/

# Fix permissions if needed
docker compose exec process-matches-service chown -R app:app /data/
```

**API Client Issues:**
```bash
# Test FOGIS API connectivity
docker compose exec process-matches-service curl -f http://fogis-api-client-service:8080/matches

# Check API client configuration
grep FOGIS_API_CLIENT_URL .env
```

**Asset Generation Issues:**
```bash
# Test WhatsApp avatar service
docker compose exec process-matches-service curl -f http://whatsapp-avatar-service:5002/health

# Check Google Drive service
docker compose exec process-matches-service curl -f http://google-drive-service:5000/health
```

### 5. Performance Issues

#### Symptoms
- Slow processing times
- High memory usage
- CPU spikes

#### Diagnostic Steps

```bash
# Monitor resource usage
docker stats process-matches-service

# Check processing times
docker compose logs process-matches-service | grep "Processing complete"

# Monitor memory usage
docker compose exec process-matches-service ps aux
```

#### Solutions

**Memory Issues:**
```bash
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M
```

**Processing Optimization:**
```bash
# Adjust processing interval
SERVICE_INTERVAL=7200  # Process every 2 hours instead of 1

# Enable change-only processing
ENABLE_CHANGE_CATEGORIZATION=true  # Only process when changes detected
```

### 6. Health Check Failures

#### Symptoms
- Health endpoints return 503
- Docker health checks fail
- Service marked as unhealthy

#### Diagnostic Steps

```bash
# Test health endpoints manually
curl -v http://localhost:8000/health/simple
curl -v http://localhost:8000/health/detailed

# Check if service is listening on port 8000
docker compose exec process-matches-service netstat -tlnp | grep 8000
```

#### Solutions

**Service Not Listening:**
```bash
# Check if health server is starting
docker compose logs process-matches-service | grep -i "health"

# Verify port configuration
grep -A5 -B5 "8000" docker-compose.yml
```

**Health Check Timeout:**
```bash
# Increase health check timeout in docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/simple"]
  timeout: 30s  # Increase from 10s
  retries: 5    # Increase retries
```

## 🔍 Advanced Diagnostics

### Log Analysis

```bash
# Search for specific error patterns
docker compose logs process-matches-service | grep -E "(ERROR|CRITICAL|Exception)"

# Monitor change categorization
docker compose logs -f process-matches-service | grep "ChangeCategory"

# Check processing cycles
docker compose logs process-matches-service | grep "Processing complete"

# Monitor external service calls
docker compose logs process-matches-service | grep -E "(HTTP|curl|request)"
```

### Performance Monitoring

```bash
# Monitor resource usage over time
watch -n 5 'docker stats process-matches-service --no-stream'

# Check disk usage
docker compose exec process-matches-service df -h

# Monitor network connections
docker compose exec process-matches-service netstat -an
```

### Configuration Debugging

```bash
# Dump all environment variables
docker compose exec process-matches-service env | sort

# Check Python path and imports
docker compose exec process-matches-service python3 -c "import sys; print('\n'.join(sys.path))"

# Verify configuration loading
docker compose exec process-matches-service python3 -c "from src.core.change_categorization import GranularChangeDetector; print('Change detection available')"
```

## 🛠️ Maintenance Commands

### Regular Maintenance

```bash
# Clean up old logs (if log rotation not configured)
docker compose exec process-matches-service find /app/logs -name "*.log" -mtime +7 -delete

# Clean up old data files
docker compose exec process-matches-service find /data -name "*.tmp" -mtime +1 -delete

# Update container images
docker compose pull
docker compose up -d
```

### Backup and Recovery

```bash
# Backup data volume
docker run --rm -v process-matches-data:/data -v $(pwd):/backup alpine \
  tar czf /backup/data-backup-$(date +%Y%m%d).tar.gz -C /data .

# Restore data volume
docker run --rm -v process-matches-data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/data-backup-YYYYMMDD.tar.gz -C /data
```

## 📞 Getting Help

### Before Seeking Help

1. **Run validation script**: `./scripts/validate_deployment.sh`
2. **Check logs**: `docker compose logs process-matches-service`
3. **Test health endpoints**: `curl http://localhost:8000/health/detailed`
4. **Review configuration**: Ensure all required environment variables are set

### Information to Include

When reporting issues, include:

- **Service version**: `curl http://localhost:8000/ | jq .version`
- **Configuration**: Sanitized `.env` file (remove secrets)
- **Logs**: Recent logs from `docker compose logs process-matches-service`
- **Health status**: Output from `/health/detailed` endpoint
- **Environment**: Docker version, OS, hardware specs

### Support Channels

1. **GitHub Issues**: [Create an issue](https://github.com/PitchConnect/match-list-processor/issues)
2. **Documentation**: Check [Deployment Guide](DEPLOYMENT_GUIDE.md) and [API Documentation](API_DOCUMENTATION.md)
3. **Migration Help**: See [Migration Guide](MIGRATION_GUIDE.md) for upgrade issues

## 🔄 Recovery Procedures

### Complete Service Reset

```bash
# Stop service
docker compose down

# Remove containers and volumes (WARNING: This deletes data)
docker compose down -v

# Recreate volumes
docker volume create process-matches-data

# Start fresh
docker compose up -d
```

### Configuration Reset

```bash
# Backup current configuration
cp .env .env.backup

# Reset to defaults
cp .env.example .env

# Edit with your values
nano .env

# Restart service
docker compose restart process-matches-service
```

---

**Troubleshooting Guide for FOGIS Match List Processor v2.0.0**
*Phase 1B Consolidated Service with Enhanced Change Detection*

**Need more help? Check the [Deployment Guide](DEPLOYMENT_GUIDE.md) or create a GitHub issue.**
