# Troubleshooting Monitoring System

## Overview

This guide provides step-by-step troubleshooting procedures for common monitoring system issues, alert scenarios, and notification delivery problems.

## Common Alert Scenarios

### FOGIS Authentication Expired

**Symptoms**:
- Repeated 401 authentication failure alerts
- Match processing stops
- No new matches detected

**Diagnosis**:
```bash
# Check FOGIS credentials
echo "Username: $FOGIS_USERNAME"
echo "Password: [REDACTED]"
echo "API Key: ${FOGIS_API_KEY:0:8}..."

# Test manual authentication
curl -u "$FOGIS_USERNAME:$FOGIS_PASSWORD" \
     -H "X-API-Key: $FOGIS_API_KEY" \
     https://api.fogis.com/auth/test
```

**Resolution Steps**:
1. **Verify Credentials**:
   ```bash
   # Check if credentials are set
   if [ -z "$FOGIS_USERNAME" ]; then
     echo "❌ FOGIS_USERNAME not set"
   fi

   if [ -z "$FOGIS_PASSWORD" ]; then
     echo "❌ FOGIS_PASSWORD not set"
   fi
   ```

2. **Test Login Manually**:
   - Visit FOGIS web interface
   - Attempt login with same credentials
   - Check for account lockout or suspension

3. **Update Credentials**:
   ```bash
   # Update environment variables
   export FOGIS_PASSWORD="new_password"

   # Restart services
   docker-compose restart match-list-processor
   ```

4. **Verify Recovery**:
   ```bash
   # Wait 2 minutes then check logs
   sleep 120
   docker-compose logs --tail=20 match-list-processor | grep -i auth
   ```

### Google Drive Quota Exceeded

**Symptoms**:
- 403 authorization failure alerts from Google Drive
- File upload failures
- Storage-related error messages

**Diagnosis**:
```bash
# Check Google Drive quota
curl -H "Authorization: Bearer $GDRIVE_TOKEN" \
     "https://www.googleapis.com/drive/v3/about?fields=storageQuota"
```

**Resolution Steps**:
1. **Review Storage Usage**:
   - Check Google Drive storage quota
   - Identify large files consuming space
   - Review retention policies

2. **Clean Up Storage**:
   ```bash
   # List large files
   curl -H "Authorization: Bearer $GDRIVE_TOKEN" \
        "https://www.googleapis.com/drive/v3/files?q=size>100000000&fields=files(id,name,size)"

   # Delete old files (if appropriate)
   # curl -X DELETE -H "Authorization: Bearer $GDRIVE_TOKEN" \
   #      "https://www.googleapis.com/drive/v3/files/{file_id}"
   ```

3. **Upgrade Storage Plan**:
   - Contact Google Workspace admin
   - Upgrade to higher storage tier
   - Implement storage monitoring

### Service Temporarily Unavailable

**Symptoms**:
- 500/502/503 error alerts
- Intermittent service failures
- Timeout errors

**Diagnosis**:
```bash
# Check service status pages
curl -s https://status.fogis.com/api/v2/status.json
curl -s https://status.cloud.google.com/

# Test service endpoints
curl -I https://api.fogis.com/health
curl -I https://www.googleapis.com/drive/v3/about
```

**Resolution Steps**:
1. **Verify External Service Status**:
   - Check official status pages
   - Monitor social media for outage reports
   - Contact service providers if needed

2. **Implement Retry Logic**:
   ```bash
   # Increase retry attempts temporarily
   export API_RETRY_ATTEMPTS=5
   export API_RETRY_DELAY=10

   docker-compose restart match-list-processor
   ```

3. **Enable Graceful Degradation**:
   ```bash
   # Enable fallback mode
   export ENABLE_FALLBACK_MODE=true
   export FALLBACK_NOTIFICATION_ONLY=true
   ```

### Network Connectivity Issues

**Symptoms**:
- Connection timeout alerts
- DNS resolution failures
- Network unreachable errors

**Diagnosis**:
```bash
# Test basic connectivity
ping -c 4 8.8.8.8
ping -c 4 api.fogis.com

# Test DNS resolution
nslookup api.fogis.com
nslookup www.googleapis.com

# Check routing
traceroute api.fogis.com
```

**Resolution Steps**:
1. **Check Network Configuration**:
   ```bash
   # Check network interfaces
   ip addr show

   # Check routing table
   ip route show

   # Check DNS configuration
   cat /etc/resolv.conf
   ```

2. **Test Docker Network**:
   ```bash
   # Check Docker network
   docker network ls
   docker network inspect bridge

   # Test container connectivity
   docker-compose exec match-list-processor ping api.fogis.com
   ```

3. **Restart Network Services**:
   ```bash
   # Restart Docker networking
   docker-compose down
   docker network prune -f
   docker-compose up -d
   ```

## Monitoring System Issues

### Notification Delivery Failures

**Symptoms**:
- Alerts generated but not received
- Email delivery errors in logs
- Discord webhook failures

**Diagnosis**:
```bash
# Check notification service logs
docker-compose logs notification-service | grep -i error

# Test email delivery
python -m src.notifications.test_email \
  --recipient admin@company.com \
  --subject "Test Alert"

# Test Discord webhook
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test notification"}'
```

**Resolution Steps**:
1. **Verify Email Configuration**:
   ```bash
   # Test SMTP connection
   python -c "
   import smtplib
   server = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT)
   server.starttls()
   server.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
   print('SMTP connection successful')
   server.quit()
   "
   ```

2. **Check Webhook URLs**:
   ```bash
   # Verify Discord webhook
   if [ -n "$DISCORD_WEBHOOK_URL" ]; then
     curl -I "$DISCORD_WEBHOOK_URL"
   else
     echo "❌ DISCORD_WEBHOOK_URL not set"
   fi
   ```

3. **Review Stakeholder Configuration**:
   ```bash
   # Check stakeholder setup
   python -m src.notifications.debug_stakeholders
   ```

### Alert Spam Prevention

**Symptoms**:
- Too many duplicate alerts
- Alert fatigue
- Important alerts missed

**Diagnosis**:
```bash
# Check alert frequency
grep "Sent.*alert" /var/log/match-list-processor.log | \
  tail -50 | cut -d' ' -f1-3 | uniq -c

# Review cooldown settings
echo "Alert cooldown: $ALERT_COOLDOWN_SECONDS seconds"
```

**Resolution Steps**:
1. **Adjust Cooldown Settings**:
   ```bash
   # Increase cooldown period
   export ALERT_COOLDOWN_SECONDS=600  # 10 minutes

   # Enable burst protection
   export ALERT_BURST_THRESHOLD=3
   export ALERT_BURST_WINDOW_SECONDS=300
   ```

2. **Review Alert Thresholds**:
   ```bash
   # Increase response time threshold
   export SLOW_RESPONSE_THRESHOLD_SECONDS=30

   # Adjust retry attempts
   export API_RETRY_ATTEMPTS=3
   ```

3. **Implement Alert Aggregation**:
   ```bash
   # Enable alert batching
   export ENABLE_ALERT_BATCHING=true
   export ALERT_BATCH_INTERVAL=1800  # 30 minutes
   ```

### Performance Impact Monitoring

**Symptoms**:
- Slower processing cycles
- Increased memory usage
- Higher CPU utilization

**Diagnosis**:
```bash
# Monitor system resources
docker stats --no-stream

# Check processing times
grep "Processing cycle completed" /var/log/match-list-processor.log | \
  tail -10 | grep -o "took [0-9.]*s"

# Monitor memory usage
docker-compose exec match-list-processor \
  python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

**Resolution Steps**:
1. **Optimize Monitoring Configuration**:
   ```bash
   # Disable non-critical monitoring
   export AVATAR_MONITORING_ENABLED=false
   export PHONEBOOK_MONITORING_ENABLED=false

   # Reduce monitoring frequency
   export MONITORING_CHECK_INTERVAL=60
   ```

2. **Tune Alert Thresholds**:
   ```bash
   # Increase thresholds to reduce false positives
   export SLOW_RESPONSE_THRESHOLD_SECONDS=30
   export HIGH_MEMORY_THRESHOLD_PERCENT=90
   ```

3. **Enable Async Processing**:
   ```bash
   # Ensure async notification delivery
   export ASYNC_NOTIFICATION_ENABLED=true
   export NOTIFICATION_QUEUE_SIZE=100
   ```

## System Health Validation

### Health Check Procedures

**Complete System Health Check**:
```bash
#!/bin/bash
# health_check.sh

echo "🔍 Running system health check..."

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Check logs for errors
echo "📋 Recent Errors:"
docker-compose logs --since=1h | grep -i error | tail -10

# Test API endpoints
echo "🌐 API Connectivity:"
curl -f -s https://api.fogis.com/health > /dev/null && echo "✅ FOGIS API" || echo "❌ FOGIS API"
curl -f -s https://www.googleapis.com/drive/v3/about > /dev/null && echo "✅ Google Drive" || echo "❌ Google Drive"

# Check notification delivery
echo "📧 Notification System:"
python -m src.notifications.health_check

# Check monitoring metrics
echo "📈 Monitoring Metrics:"
python -m src.monitoring.health_check

echo "✅ Health check complete"
```

**Automated Health Monitoring**:
```bash
# Add to crontab for regular health checks
# */15 * * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1
```

### Performance Benchmarking

**Baseline Performance Test**:
```bash
#!/bin/bash
# performance_test.sh

echo "🚀 Running performance benchmark..."

# Measure processing cycle time
start_time=$(date +%s)
docker-compose exec match-list-processor \
  python -m src.main --test-mode
end_time=$(date +%s)

cycle_time=$((end_time - start_time))
echo "Processing cycle time: ${cycle_time}s"

# Check memory usage
memory_usage=$(docker stats --no-stream --format "table {{.MemPerc}}" | tail -1)
echo "Memory usage: $memory_usage"

# Check CPU usage
cpu_usage=$(docker stats --no-stream --format "table {{.CPUPerc}}" | tail -1)
echo "CPU usage: $cpu_usage"

# Test notification delivery time
notification_start=$(date +%s%3N)
python -m src.notifications.test_delivery
notification_end=$(date +%s%3N)

notification_time=$((notification_end - notification_start))
echo "Notification delivery time: ${notification_time}ms"
```

## Diagnostic Tools

### Log Analysis

**Extract Monitoring Events**:
```bash
# Get all monitoring-related log entries
grep -E "(alert|monitoring|notification)" /var/log/match-list-processor.log | tail -50

# Filter by severity
grep "CRITICAL\|HIGH" /var/log/match-list-processor.log | tail -20

# Check alert frequency
grep "Sent.*alert" /var/log/match-list-processor.log | \
  awk '{print $1" "$2}' | uniq -c | tail -10
```

**Performance Analysis**:
```bash
# Extract processing times
grep "Processing cycle completed" /var/log/match-list-processor.log | \
  grep -o "took [0-9.]*s" | \
  awk '{sum+=$2; count++} END {print "Average:", sum/count "s"}'

# Check error rates
total_requests=$(grep "API request" /var/log/match-list-processor.log | wc -l)
error_requests=$(grep "API request.*error" /var/log/match-list-processor.log | wc -l)
error_rate=$(echo "scale=2; $error_requests * 100 / $total_requests" | bc)
echo "Error rate: $error_rate%"
```

### Configuration Validation

**Validate Monitoring Configuration**:
```bash
#!/bin/bash
# validate_config.sh

echo "🔧 Validating monitoring configuration..."

# Check required environment variables
required_vars=(
  "MONITORING_ENABLED"
  "NOTIFICATION_SERVICE_ENABLED"
  "SMTP_HOST"
  "SMTP_USERNAME"
)

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Missing: $var"
  else
    echo "✅ Set: $var"
  fi
done

# Test notification channels
echo "📧 Testing email delivery..."
python -m src.notifications.test_email --dry-run

echo "💬 Testing Discord webhook..."
python -m src.notifications.test_discord --dry-run

echo "🔗 Testing generic webhook..."
python -m src.notifications.test_webhook --dry-run

echo "✅ Configuration validation complete"
```

### Emergency Procedures

**Disable Monitoring Temporarily**:
```bash
# Disable all monitoring
export MONITORING_ENABLED=false
docker-compose restart match-list-processor

# Disable specific service monitoring
export FOGIS_MONITORING_ENABLED=false
export GDRIVE_MONITORING_ENABLED=false
```

**Emergency Contact Procedures**:
```bash
# Send emergency notification
python -c "
from src.notifications.emergency import send_emergency_alert
send_emergency_alert(
    message='Monitoring system disabled due to issues',
    severity='high',
    recipients=['admin@company.com']
)
"
```

**System Recovery**:
```bash
# Full system restart
docker-compose down
docker system prune -f
docker-compose up -d

# Wait for services to stabilize
sleep 60

# Run health check
./health_check.sh
```
