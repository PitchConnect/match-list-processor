# 🔔 Notification System Quick Start Guide

## **🚀 From Zero to Notifications in 5 Steps**

This guide will get you from the current "notifications disabled" state to a fully functional notification system.

### **📋 Current Status**
- ✅ **Architecture Complete**: Comprehensive notification system implemented
- ✅ **Multi-channel Support**: Email, Discord, and Webhook clients ready
- ✅ **Stakeholder Management**: Full stakeholder and preference management
- ✅ **Semantic Analysis**: Advanced change categorization with notifications
- ❌ **System Disabled**: `notification_system: false` in configuration
- ❌ **No Configuration**: Missing channel credentials and stakeholder data

---

## **🔧 Step 1: Run Setup Script**

The setup script will guide you through enabling the notification system:

```bash
cd match-list-processor
python scripts/setup_notifications.py --interactive
```

**What this does:**
- ✅ Enables notification system in configuration
- ✅ Creates stakeholder database from template
- ✅ Validates system prerequisites
- ✅ Provides next steps guidance

---

## **📧 Step 2: Configure Notification Channels**

### **Option A: Quick Test Setup (Recommended for first try)**

```bash
# Copy environment template
cp .env.template .env

# Edit with test values
nano .env
```

**Minimal test configuration:**
```bash
# Enable system
NOTIFICATION_SYSTEM_ENABLED=true

# Disable all channels for testing
EMAIL_ENABLED=false
DISCORD_ENABLED=false
WEBHOOK_ENABLED=false

# Enable test mode
NOTIFICATION_TEST_MODE=true
NOTIFICATION_DEBUG=true
```

### **Option B: Email Channel Setup**

**Gmail Example:**
```bash
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Generate at https://myaccount.google.com/apppasswords
SMTP_FROM=fogis-notifications@yourcompany.com
SMTP_USE_TLS=true
```

### **Option C: Discord Channel Setup**

1. **Create Discord Webhook:**
   - Server Settings → Integrations → Webhooks → New Webhook
   - Copy webhook URL

2. **Configure:**
   ```bash
   DISCORD_ENABLED=true
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
   DISCORD_BOT_USERNAME=FOGIS Match Bot
   ```

---

## **👥 Step 3: Configure Stakeholders**

Edit the stakeholder database with real contact information:

```bash
nano data/stakeholders.json
```

**Update these fields:**
- Replace `admin@yourcompany.com` with real admin email
- Replace `referee.coordinator@yourcompany.com` with real coordinator email
- Add Discord user IDs if using Discord
- Configure notification preferences

**Example stakeholder:**
```json
{
  "id": "admin-001",
  "name": "Your Name",
  "email": "your-real-email@company.com",
  "role": "Administrator",
  "active": true,
  "preferences": {
    "channels": ["email"],
    "notification_types": ["match_changes", "system_alerts"],
    "priority_filter": "medium",
    "immediate_delivery": true
  }
}
```

---

## **🧪 Step 4: Test the System**

### **Validate Configuration**
```bash
python scripts/setup_notifications.py --validate-only
```

### **Test Notifications (Dry Run)**
```bash
# Test all channels without sending
python scripts/test_notifications.py --dry-run

# Test specific channel
python scripts/test_notifications.py --channel email --dry-run
```

### **Send Test Notification**
```bash
# Send actual test notification
python scripts/test_notifications.py --channel email
```

**Expected output:**
```
🧪 Comprehensive Notification System Test
========================================

📋 Testing Stakeholder Filtering
----------------------------------------
ℹ️  Found 4 stakeholders
ℹ️  Found 1 referees
ℹ️  Found 1 referee coordinators
✅ Stakeholder filtering test completed

📋 Testing Email Channel
----------------------------------------
✅ Test notification sent via email

Test Results: 5/5 passed
✅ All tests passed!
```

---

## **🚀 Step 5: Enable in Production**

### **Update Configuration**
```bash
# Enable notification system
sed -i 's/notification_system: false/notification_system: true/' config/unified_processor.yml

# Or edit manually
nano config/unified_processor.yml
```

Change:
```yaml
features:
  notification_system: true  # Changed from false
```

### **Restart the Processor**
```bash
# If running as service
sudo systemctl restart fogis-match-processor

# If running manually
python src/app_unified.py
```

### **Verify Integration**
Check logs for notification system initialization:
```bash
tail -f logs/unified_processor.log | grep -i notification
```

Expected log entries:
```
INFO: Notification system initialized successfully
INFO: Loaded 4 stakeholders from database
INFO: Email channel configured and ready
INFO: Notification system ready for match change detection
```

---

## **📊 Monitoring and Verification**

### **Check Notification Analytics**
```bash
cat data/notification_analytics.json | jq '.delivery_stats'
```

### **Monitor Logs**
```bash
# Notification-specific logs
tail -f logs/notification_system.log

# General system logs
tail -f logs/unified_processor.log | grep -i notification
```

### **Test with Real Match Data**
When the processor detects actual match changes, you should see:
```
INFO: Match changes detected for match 12345
INFO: Categorized 3 changes: 1 high priority, 2 medium priority
INFO: Sending notifications to 2 stakeholders via email
INFO: Notification delivery completed: 2 sent, 0 failed
```

---

## **🔧 Troubleshooting Common Issues**

### **"Notification system disabled"**
```bash
# Check feature flag
grep "notification_system" config/unified_processor.yml

# Should show: notification_system: true
```

### **"No stakeholders found"**
```bash
# Check stakeholder file exists
ls -la data/stakeholders.json

# Validate JSON format
python -m json.tool data/stakeholders.json
```

### **"Email sending failed"**
```bash
# Test SMTP connection
python -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('$SMTP_USERNAME', '$SMTP_PASSWORD')
print('SMTP connection successful')
"
```

### **"Discord webhook failed"**
```bash
# Test webhook manually
curl -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message"}'
```

---

## **📈 Next Steps After Setup**

### **Immediate (First Week)**
1. **Monitor delivery**: Check notification analytics daily
2. **Adjust preferences**: Fine-tune stakeholder notification preferences
3. **Test scenarios**: Verify notifications for different types of match changes
4. **Performance check**: Monitor system performance impact

### **Short-term (First Month)**
1. **Add more stakeholders**: Expand to full stakeholder list
2. **Enable more channels**: Add Discord or webhook notifications
3. **Customize templates**: Adjust notification content and formatting
4. **Set up monitoring**: Implement alerting for notification failures

### **Long-term (Ongoing)**
1. **Regular maintenance**: Update stakeholder database and preferences
2. **Performance optimization**: Tune batch processing and rate limiting
3. **Security reviews**: Rotate credentials and review access
4. **Feature enhancement**: Add new notification types and channels

---

## **🆘 Getting Help**

### **Documentation**
- **Full deployment guide**: `docs/NOTIFICATION_DEPLOYMENT_GUIDE.md`
- **Configuration reference**: `docs/NOTIFICATION_CONFIGURATION.md`
- **Architecture overview**: `docs/NOTIFICATION_SYSTEM_ARCHITECTURE.md`

### **Testing Tools**
- **Setup script**: `python scripts/setup_notifications.py --help`
- **Test script**: `python scripts/test_notifications.py --help`
- **Demo script**: `python scripts/demo_notification_system.py`

### **Configuration Files**
- **Main config**: `config/unified_processor.yml`
- **Channel config**: `config/notification_channels.yml`
- **Stakeholders**: `data/stakeholders.json`
- **Environment**: `.env` (create from `.env.template`)

### **Common Commands**
```bash
# Quick validation
python scripts/setup_notifications.py --validate-only

# Test specific channel
python scripts/test_notifications.py --channel email --dry-run

# Check system status
grep -i notification logs/unified_processor.log | tail -10

# View analytics
cat data/notification_analytics.json | jq '.'
```

---

**🎉 Congratulations! You now have a fully functional notification system that will alert stakeholders about FOGIS match changes, referee assignments, and system alerts.**
