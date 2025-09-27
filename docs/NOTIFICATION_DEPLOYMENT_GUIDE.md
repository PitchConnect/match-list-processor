# Notification System Deployment Guide

## 🚀 **Production Deployment Checklist**

This guide provides step-by-step instructions for safely enabling the notification system in production.

### **📋 Pre-Deployment Checklist**

#### **1. Configuration Validation**
- [ ] Notification system architecture is complete
- [ ] All required configuration files are present
- [ ] Environment variables are properly configured
- [ ] Stakeholder database is populated with real contacts
- [ ] Channel credentials are valid and tested

#### **2. Security Review**
- [ ] Sensitive credentials are stored as environment variables
- [ ] No hardcoded passwords or tokens in configuration files
- [ ] HTTPS is used for all webhook endpoints
- [ ] Rate limiting is configured appropriately
- [ ] Audit logging is enabled

#### **3. Testing Completion**
- [ ] All notification channels tested individually
- [ ] End-to-end testing completed successfully
- [ ] Error handling and recovery tested
- [ ] Performance testing under load completed
- [ ] Stakeholder filtering and routing verified

## **🔧 Step-by-Step Deployment**

### **Phase 1: Configuration Setup**

#### **Step 1: Enable Notification System**
```bash
# Update unified processor configuration
cd match-list-processor
python scripts/setup_notifications.py --interactive
```

#### **Step 2: Configure Environment Variables**
```bash
# Copy environment template
cp .env.template .env

# Edit with production values
nano .env
```

**Required Environment Variables:**
```bash
# Core settings
NOTIFICATION_SYSTEM_ENABLED=true
NOTIFICATION_BATCH_SIZE=10
NOTIFICATION_BATCH_TIMEOUT=30

# Email configuration (example with Gmail)
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourcompany.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=fogis-notifications@yourcompany.com
SMTP_USE_TLS=true

# Discord configuration
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
DISCORD_BOT_USERNAME=FOGIS Match Bot

# Security settings
NOTIFICATION_ENCRYPT_DATA=true
NOTIFICATION_DEBUG=false
```

#### **Step 3: Setup Stakeholder Database**
```bash
# Copy stakeholder template
cp config/stakeholders_template.json data/stakeholders.json

# Edit with real stakeholder information
nano data/stakeholders.json
```

**Update stakeholder information:**
- Replace example email addresses with real ones
- Add Discord user IDs if using Discord notifications
- Configure notification preferences for each stakeholder
- Set up notification groups and rules

### **Phase 2: Channel Configuration**

#### **Email Channel Setup**

**Gmail Configuration:**
1. Enable 2-factor authentication
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password as `SMTP_PASSWORD`

**Corporate SMTP Configuration:**
```bash
SMTP_HOST=mail.yourcompany.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourcompany.com
SMTP_PASSWORD=your-secure-password
SMTP_USE_TLS=true
```

#### **Discord Channel Setup**

1. **Create Discord Webhook:**
   - Go to Server Settings > Integrations > Webhooks
   - Click "New Webhook"
   - Configure channel and permissions
   - Copy webhook URL

2. **Configure Environment:**
   ```bash
   DISCORD_ENABLED=true
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...
   DISCORD_BOT_USERNAME=FOGIS Match Bot
   ```

#### **Webhook Channel Setup**

1. **Setup Webhook Endpoint:**
   - Deploy webhook receiver service
   - Configure authentication
   - Test endpoint accessibility

2. **Configure Environment:**
   ```bash
   WEBHOOK_ENABLED=true
   WEBHOOK_URL=https://your-webhook-endpoint.com/notifications
   WEBHOOK_AUTH_TOKEN=your-secure-token
   WEBHOOK_TIMEOUT=30
   ```

### **Phase 3: Testing and Validation**

#### **Step 1: Validate Configuration**
```bash
# Run configuration validation
python scripts/setup_notifications.py --validate-only
```

#### **Step 2: Test Individual Channels**
```bash
# Test email channel
python scripts/test_notifications.py --channel email --dry-run

# Test Discord channel
python scripts/test_notifications.py --channel discord --dry-run

# Test webhook channel
python scripts/test_notifications.py --channel webhook --dry-run
```

#### **Step 3: End-to-End Testing**
```bash
# Run comprehensive test (dry run first)
python scripts/test_notifications.py --dry-run

# Run actual test with limited scope
NOTIFICATION_TEST_MODE=true python scripts/test_notifications.py
```

#### **Step 4: Production Test**
```bash
# Send test notification to production channels
python scripts/test_notifications.py --channel email
```

### **Phase 4: Gradual Rollout**

#### **Step 1: Enable Test Mode**
```bash
# Start with test mode enabled
NOTIFICATION_TEST_MODE=true
NOTIFICATION_TEST_EMAIL=admin@yourcompany.com
```

#### **Step 2: Limited Stakeholder Group**
```json
{
  "stakeholders": [
    {
      "id": "admin-001",
      "name": "System Administrator",
      "email": "admin@yourcompany.com",
      "role": "Administrator",
      "active": true
    }
  ]
}
```

#### **Step 3: Gradual Expansion**
1. **Week 1:** Admin notifications only
2. **Week 2:** Add referee coordinators
3. **Week 3:** Add system administrators
4. **Week 4:** Full stakeholder rollout

#### **Step 4: Full Production**
```bash
# Disable test mode
NOTIFICATION_TEST_MODE=false

# Enable all channels
EMAIL_ENABLED=true
DISCORD_ENABLED=true
WEBHOOK_ENABLED=true
```

## **📊 Monitoring and Maintenance**

### **Monitoring Setup**

#### **Log Monitoring**
```bash
# Monitor notification logs
tail -f logs/notification_system.log

# Check for errors
grep ERROR logs/notification_system.log

# Monitor delivery statistics
cat data/notification_analytics.json | jq '.delivery_stats'
```

#### **Health Checks**
```bash
# Enable health monitoring
NOTIFICATION_HEALTH_CHECK_ENABLED=true

# Check system health
python scripts/test_notifications.py --validate-only
```

#### **Performance Monitoring**
- Monitor notification delivery times
- Track failure rates by channel
- Monitor rate limiting and throttling
- Check memory and CPU usage

### **Maintenance Tasks**

#### **Daily Tasks**
- [ ] Check notification logs for errors
- [ ] Monitor delivery statistics
- [ ] Verify all channels are operational

#### **Weekly Tasks**
- [ ] Review stakeholder preferences
- [ ] Check rate limiting effectiveness
- [ ] Update notification analytics
- [ ] Test backup notification channels

#### **Monthly Tasks**
- [ ] Review and update stakeholder database
- [ ] Rotate authentication tokens
- [ ] Performance optimization review
- [ ] Security audit of notification system

## **🚨 Troubleshooting Guide**

### **Common Issues**

#### **Email Delivery Problems**
```bash
# Check SMTP configuration
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('user@gmail.com', 'password')
print('SMTP connection successful')
"

# Test email delivery
python scripts/test_notifications.py --channel email
```

#### **Discord Webhook Issues**
```bash
# Test webhook manually
curl -X POST "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'

# Check webhook configuration
python scripts/test_notifications.py --channel discord --dry-run
```

#### **Performance Issues**
```bash
# Check batch processing
grep "batch" logs/notification_system.log

# Monitor memory usage
ps aux | grep python

# Check rate limiting
grep "rate_limit" logs/notification_system.log
```

### **Emergency Procedures**

#### **Disable Notifications**
```bash
# Quick disable
export NOTIFICATION_SYSTEM_ENABLED=false

# Or update configuration
sed -i 's/notification_system: true/notification_system: false/' config/unified_processor.yml
```

#### **Channel-Specific Disable**
```bash
# Disable specific channels
export EMAIL_ENABLED=false
export DISCORD_ENABLED=false
export WEBHOOK_ENABLED=false
```

#### **Emergency Contact Override**
```bash
# Override all notifications to admin
export NOTIFICATION_TEST_MODE=true
export NOTIFICATION_TEST_EMAIL=emergency@yourcompany.com
```

## **🔒 Security Best Practices**

### **Credential Management**
- Use environment variables for all sensitive data
- Rotate passwords and tokens regularly
- Use dedicated service accounts
- Implement least-privilege access

### **Data Protection**
- Enable data encryption in production
- Mask sensitive information in logs
- Implement audit logging
- Regular security reviews

### **Access Control**
- Limit notification system access
- Monitor configuration changes
- Implement change approval process
- Regular access reviews

### **Network Security**
- Use HTTPS for all communications
- Implement firewall rules
- Monitor network traffic
- Regular security scans

## **📈 Performance Optimization**

### **Batch Processing**
```bash
# Optimize batch size
NOTIFICATION_BATCH_SIZE=20
NOTIFICATION_BATCH_TIMEOUT=60
```

### **Rate Limiting**
```bash
# Configure appropriate limits
EMAIL_MAX_PER_MINUTE=50
DISCORD_MAX_PER_MINUTE=10
WEBHOOK_MAX_PER_MINUTE=100
```

### **Caching**
- Cache stakeholder preferences
- Cache notification templates
- Implement connection pooling
- Use async processing

### **Resource Management**
- Monitor memory usage
- Implement connection limits
- Use connection pooling
- Regular cleanup tasks

---

**This deployment guide ensures a safe, gradual rollout of the notification system with proper monitoring, security, and maintenance procedures.**
