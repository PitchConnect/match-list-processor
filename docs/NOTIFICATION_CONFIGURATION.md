# Notification Configuration Guide

## Overview

This guide provides comprehensive instructions for configuring the notification system, including stakeholder management, channel setup, alert routing, and monitoring options.

## Environment Variables

### Core Monitoring Configuration

```bash
# Enable/disable monitoring system
MONITORING_ENABLED=true

# Alert cooldown period (seconds)
ALERT_COOLDOWN_SECONDS=300

# Response time threshold for slow response alerts (seconds)
SLOW_RESPONSE_THRESHOLD_SECONDS=15

# Enable/disable notification service
NOTIFICATION_SERVICE_ENABLED=true
```

### Service-Specific Monitoring

```bash
# FOGIS API Client Monitoring
FOGIS_MONITORING_ENABLED=true
FOGIS_TIMEOUT_SECONDS=30
FOGIS_RETRY_ATTEMPTS=3

# Google Drive Service Monitoring
GDRIVE_MONITORING_ENABLED=true
GDRIVE_TIMEOUT_SECONDS=60
GDRIVE_RETRY_ATTEMPTS=2

# Avatar Service Monitoring
AVATAR_MONITORING_ENABLED=true
AVATAR_TIMEOUT_SECONDS=45
AVATAR_RETRY_ATTEMPTS=2

# Phonebook Service Monitoring
PHONEBOOK_MONITORING_ENABLED=true
PHONEBOOK_TIMEOUT_SECONDS=30
PHONEBOOK_RETRY_ATTEMPTS=3
```

### Notification Channel Configuration

```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourcompany.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true

# Discord Webhook Configuration
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
DISCORD_WEBHOOK_ENABLED=true

# Generic Webhook Configuration
WEBHOOK_URL=https://your-monitoring-system.com/webhook
WEBHOOK_ENABLED=true
WEBHOOK_TIMEOUT_SECONDS=10
```

### System Alert Configuration

```bash
# Stakeholder roles that receive system alerts
SYSTEM_ALERT_STAKEHOLDER_ROLES=Administrator,SystemAdmin,DevOps

# Alert severity levels to process
ALERT_SEVERITY_LEVELS=critical,high,medium

# Maximum alerts per service per hour
MAX_ALERTS_PER_SERVICE_PER_HOUR=10
```

## Stakeholder Management

### Stakeholder Configuration

Stakeholders are configured in the notification system database. Each stakeholder has:

```python
# Stakeholder Model
{
    "stakeholder_id": "admin-001",
    "name": "System Administrator",
    "role": "Administrator",
    "contact_info": [
        {
            "channel": "email",
            "address": "admin@company.com",
            "active": true
        },
        {
            "channel": "discord",
            "address": "webhook_url",
            "active": true
        }
    ],
    "alert_preferences": {
        "critical": ["email", "discord"],
        "high": ["email", "discord"],
        "medium": ["email"]
    }
}
```

### Adding Stakeholders

**Via Configuration File** (`config/stakeholders.yml`):
```yaml
stakeholders:
  - stakeholder_id: "admin-001"
    name: "Primary Administrator"
    role: "Administrator"
    contact_info:
      - channel: "email"
        address: "admin@company.com"
        active: true
      - channel: "discord"
        address: "https://discord.com/api/webhooks/admin_channel"
        active: true
    alert_preferences:
      critical: ["email", "discord"]
      high: ["email", "discord"]
      medium: ["email"]

  - stakeholder_id: "devops-001"
    name: "DevOps Engineer"
    role: "DevOps"
    contact_info:
      - channel: "email"
        address: "devops@company.com"
        active: true
    alert_preferences:
      critical: ["email"]
      high: ["email"]
      medium: []
```

**Via API** (if management endpoints are available):
```bash
# Add new stakeholder
curl -X POST http://localhost:8000/api/stakeholders \
  -H "Content-Type: application/json" \
  -d '{
    "stakeholder_id": "ops-001",
    "name": "Operations Team",
    "role": "SystemAdmin",
    "contact_info": [
      {
        "channel": "email",
        "address": "ops@company.com",
        "active": true
      }
    ]
  }'
```

### Stakeholder Roles

**Administrator**:
- Receives all system alerts
- Critical authentication failures
- Service outage notifications
- Performance degradation alerts

**SystemAdmin**:
- Infrastructure-related alerts
- Service availability issues
- Configuration problems
- Security-related notifications

**DevOps**:
- Deployment-related alerts
- CI/CD pipeline issues
- Performance monitoring
- Resource utilization alerts

**Developer**:
- Application-specific errors
- Code-related failures
- Integration issues
- Debug information

## Notification Channels

### Email Configuration

**SMTP Setup**:
```bash
# Gmail Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use app-specific password
SMTP_USE_TLS=true

# Outlook Configuration
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true

# Custom SMTP Server
SMTP_HOST=mail.yourcompany.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourcompany.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

**Email Template Configuration**:
```python
# Email template settings
EMAIL_TEMPLATE_CRITICAL = """
Subject: 🚨 CRITICAL: {service} Alert - {alert_type}

Service: {service}
Alert Type: {alert_type}
Severity: {severity}
Timestamp: {timestamp}

Error Details:
{error_details}

Recovery Actions:
{recovery_actions}

Affected Functionality:
{affected_functionality}

System: Match List Processor v2.0.0
"""
```

### Discord Webhook Configuration

**Setup Discord Webhook**:
1. Go to Discord Server Settings → Integrations → Webhooks
2. Create New Webhook
3. Copy webhook URL
4. Set environment variable:
   ```bash
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop
   ```

**Discord Message Format**:
```python
# Discord embed configuration
DISCORD_EMBED_COLORS = {
    "critical": 15158332,  # Red
    "high": 16753920,      # Orange
    "medium": 16776960     # Yellow
}

DISCORD_EMBED_TEMPLATE = {
    "embeds": [{
        "title": "🚨 System Alert: {alert_type}",
        "description": "{message}",
        "color": "{color}",
        "fields": [
            {"name": "Service", "value": "{service}", "inline": True},
            {"name": "Severity", "value": "{severity}", "inline": True},
            {"name": "Timestamp", "value": "{timestamp}", "inline": True}
        ]
    }]
}
```

### Generic Webhook Configuration

**Setup Generic Webhook**:
```bash
# Basic webhook configuration
WEBHOOK_URL=https://your-system.com/webhook
WEBHOOK_ENABLED=true
WEBHOOK_TIMEOUT_SECONDS=10

# Authentication (if required)
WEBHOOK_AUTH_TYPE=bearer  # Options: none, basic, bearer, api_key
WEBHOOK_AUTH_TOKEN=your-auth-token

# Custom headers
WEBHOOK_HEADERS='{"X-API-Key": "your-api-key", "Content-Type": "application/json"}'
```

**Webhook Payload Format**:
```json
{
  "alert_type": "authentication_failure",
  "service": "fogis-api-client",
  "severity": "critical",
  "message": "FOGIS API authentication failed",
  "error_details": "HTTP 401: Unauthorized access",
  "timestamp": "2025-09-02T17:30:00Z",
  "recovery_actions": [
    "Check FOGIS credentials in environment variables",
    "Verify FOGIS account status"
  ],
  "affected_functionality": [
    "Match processing suspended",
    "Change detection unavailable"
  ],
  "system_info": {
    "service": "match-list-processor",
    "version": "2.0.0",
    "environment": "production"
  }
}
```

## Alert Routing Configuration

### Severity-Based Routing

```yaml
# Alert routing configuration
alert_routing:
  critical:
    channels: ["email", "discord", "webhook"]
    stakeholder_roles: ["Administrator", "SystemAdmin"]
    immediate_delivery: true
    escalation_timeout: 300  # 5 minutes

  high:
    channels: ["email", "discord"]
    stakeholder_roles: ["Administrator", "SystemAdmin", "DevOps"]
    immediate_delivery: true
    escalation_timeout: 900  # 15 minutes

  medium:
    channels: ["email"]
    stakeholder_roles: ["Administrator", "DevOps"]
    immediate_delivery: false
    batch_delivery: true
    batch_interval: 1800  # 30 minutes
```

### Service-Specific Routing

```yaml
# Service-specific alert routing
service_routing:
  fogis-api-client:
    critical: ["Administrator", "SystemAdmin"]
    high: ["Administrator", "DevOps"]
    medium: ["DevOps"]

  google-drive-service:
    critical: ["Administrator"]
    high: ["Administrator", "DevOps"]
    medium: ["DevOps"]

  avatar-service:
    critical: ["Administrator"]
    high: ["DevOps"]
    medium: ["Developer"]
```

### Time-Based Routing

```yaml
# Time-based routing (business hours vs after hours)
time_routing:
  business_hours:
    timezone: "UTC"
    start_time: "09:00"
    end_time: "17:00"
    weekdays: [1, 2, 3, 4, 5]  # Monday-Friday
    channels: ["email"]

  after_hours:
    channels: ["email", "discord", "webhook"]
    escalation_enabled: true
    escalation_delay: 600  # 10 minutes
```

## Notification Deduplication

### Deduplication Configuration

```bash
# Alert deduplication settings
ALERT_DEDUPLICATION_ENABLED=true
ALERT_COOLDOWN_SECONDS=300
ALERT_BURST_THRESHOLD=5
ALERT_BURST_WINDOW_SECONDS=60
```

### Deduplication Logic

```python
# Deduplication key generation
deduplication_key = f"{service}:{alert_type}:{severity}"

# Cooldown tracking
last_alert_time = alert_cache.get(deduplication_key)
current_time = time.time()

if last_alert_time and (current_time - last_alert_time) < cooldown_seconds:
    # Skip duplicate alert
    logger.info(f"Skipping duplicate alert: {deduplication_key}")
    return

# Update last alert time
alert_cache.set(deduplication_key, current_time)
```

### Burst Protection

```python
# Burst detection and aggregation
burst_key = f"{service}:burst"
burst_count = burst_cache.get(burst_key, 0)

if burst_count >= ALERT_BURST_THRESHOLD:
    # Send aggregated alert instead of individual alerts
    send_burst_summary_alert(service, burst_count)
    burst_cache.delete(burst_key)
else:
    # Send individual alert
    send_individual_alert(alert_data)
    burst_cache.increment(burst_key)
```

## Testing Configuration

### Test Notification Delivery

```bash
# Test email delivery
python -m src.notifications.test_email_delivery \
  --recipient admin@company.com \
  --subject "Test Alert" \
  --message "This is a test notification"

# Test Discord webhook
python -m src.notifications.test_discord_webhook \
  --webhook-url "$DISCORD_WEBHOOK_URL" \
  --message "Test Discord notification"

# Test generic webhook
python -m src.notifications.test_webhook \
  --webhook-url "$WEBHOOK_URL" \
  --payload '{"test": "notification"}'
```

### Configuration Validation

```bash
# Validate notification configuration
python -m src.notifications.validate_config

# Test stakeholder resolution
python -m src.notifications.test_stakeholder_resolution \
  --alert-type authentication_failure \
  --severity critical

# Test alert routing
python -m src.notifications.test_alert_routing \
  --service fogis-api-client \
  --severity high
```

## Troubleshooting Configuration

### Common Issues

**Email Delivery Failures**:
```bash
# Check SMTP configuration
python -c "
import smtplib
server = smtplib.SMTP('$SMTP_HOST', $SMTP_PORT)
server.starttls()
server.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
print('SMTP connection successful')
server.quit()
"
```

**Discord Webhook Failures**:
```bash
# Test Discord webhook
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message from monitoring system"}'
```

**Stakeholder Resolution Issues**:
```bash
# Check stakeholder configuration
python -m src.notifications.debug_stakeholders \
  --role Administrator \
  --alert-type authentication_failure
```

### Configuration Validation

```python
# Configuration validation script
def validate_notification_config():
    """Validate notification system configuration."""

    # Check required environment variables
    required_vars = [
        'MONITORING_ENABLED',
        'NOTIFICATION_SERVICE_ENABLED',
        'SMTP_HOST',
        'SMTP_USERNAME'
    ]

    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ Missing required variable: {var}")

    # Test notification channels
    test_email_delivery()
    test_discord_webhook()
    test_stakeholder_resolution()

    print("✅ Configuration validation complete")
```
