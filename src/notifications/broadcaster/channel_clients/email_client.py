"""Email notification client."""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

from ...models.notification_models import (
    ChangeNotification,
    DeliveryResult,
    DeliveryStatus,
    NotificationChannel,
    NotificationRecipient,
)
from ...templates.email_templates import EmailTemplateEngine

logger = logging.getLogger(__name__)


class EmailNotificationClient:
    """Email notification client using SMTP."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize email client.

        Args:
            config: Email configuration dictionary
        """
        self.config = config
        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.smtp_username = config.get("smtp_username", "")
        self.smtp_password = config.get("smtp_password", "")
        self.email_from = config.get("email_from", "fogis@example.com")
        self.use_tls = config.get("use_tls", True)
        self.enabled = config.get("enabled", False)

        # Initialize template engine
        self.template_engine = EmailTemplateEngine()

        if not self.enabled:
            logger.info("Email notifications are disabled")

    async def send_notification(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> DeliveryResult:
        """Send email notification to recipient.

        Args:
            notification: Notification to send
            recipient: Email recipient

        Returns:
            Delivery result
        """
        if not self.enabled:
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.FAILED,
                message="Email notifications are disabled",
            )

        try:
            # Generate email content
            subject = self._generate_subject(notification)
            html_body = self._generate_html_body(notification, recipient)
            text_body = self._generate_text_body(notification, recipient)

            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._send_email_sync, recipient.address, subject, html_body, text_body
            )

            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.DELIVERED,
                message="Email sent successfully",
            )

        except Exception as e:
            logger.error(f"Failed to send email to {recipient.address}: {e}")
            return DeliveryResult(
                recipient_id=recipient.stakeholder_id,
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.FAILED,
                message="Email delivery failed",
                error_details=str(e),
            )

    def _send_email_sync(
        self, to_address: str, subject: str, html_body: str, text_body: str
    ) -> None:
        """Send email synchronously.

        Args:
            to_address: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body
        """
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = to_address

        # Add text and HTML parts
        text_part = MIMEText(text_body, "plain", "utf-8")
        html_part = MIMEText(html_body, "html", "utf-8")

        msg.attach(text_part)
        msg.attach(html_part)

        # Send email
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_address}")

    def _generate_subject(self, notification: ChangeNotification) -> str:
        """Generate email subject.

        Args:
            notification: Notification data

        Returns:
            Email subject string
        """
        priority_emoji = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📢",
            "low": "ℹ️",
        }

        emoji = priority_emoji.get(notification.priority.value, "📢")

        # Extract match info for subject
        match_context = notification.match_context
        home_team = match_context.get("lag1namn", "Unknown")
        away_team = match_context.get("lag2namn", "Unknown")

        return f"{emoji} FOGIS: {notification.change_summary} - {home_team} vs {away_team}"

    def _generate_html_body(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> str:
        """Generate HTML email body.

        Args:
            notification: Notification data
            recipient: Recipient information

        Returns:
            HTML email body
        """
        match_context = notification.match_context

        # Priority styling
        priority_colors = {
            "critical": "#dc2626",  # red
            "high": "#ea580c",  # orange
            "medium": "#2563eb",  # blue
            "low": "#059669",  # green
        }

        priority_color = priority_colors.get(notification.priority.value, "#2563eb")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self._generate_subject(notification)}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: {priority_color}; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .match-info {{ background: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 5px; }}
        .change-details {{ background: #fff3cd; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
        .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
        .priority-badge {{ background: {priority_color}; color: white; padding: 4px 8px; border-radius: 3px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏆 FOGIS Match Notification</h1>
        <span class="priority-badge">{notification.priority.value.upper()} PRIORITY</span>
    </div>

    <div class="content">
        <p>Hello {recipient.name},</p>

        <div class="change-details">
            <h3>📋 Change Summary</h3>
            <p><strong>{notification.change_summary}</strong></p>
            <p><em>Category:</em> {notification.change_category.replace('_', ' ').title()}</p>
        </div>

        <div class="match-info">
            <h3>⚽ Match Information</h3>
            <p><strong>Teams:</strong> {match_context.get('lag1namn', 'TBD')} vs {match_context.get('lag2namn', 'TBD')}</p>
            <p><strong>Date:</strong> {match_context.get('speldatum', 'TBD')}</p>
            <p><strong>Time:</strong> {match_context.get('avsparkstid', 'TBD')}</p>
            <p><strong>Venue:</strong> {match_context.get('anlaggningnamn', 'TBD')}</p>
            <p><strong>Competition:</strong> {match_context.get('serienamn', 'TBD')}</p>
        </div>

        {self._generate_field_changes_html(notification)}

        <p>Please review this information and take any necessary action.</p>

        <p>Best regards,<br>
        FOGIS Notification System</p>
    </div>

    <div class="footer">
        <p>This is an automated notification from the FOGIS Match List Processor.</p>
        <p>Notification ID: {notification.notification_id}</p>
        <p>Sent: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
</body>
</html>
        """

        return html.strip()

    def _generate_text_body(
        self, notification: ChangeNotification, recipient: NotificationRecipient
    ) -> str:
        """Generate plain text email body.

        Args:
            notification: Notification data
            recipient: Recipient information

        Returns:
            Plain text email body
        """
        match_context = notification.match_context

        text = f"""
FOGIS Match Notification - {notification.priority.value.upper()} PRIORITY

Hello {recipient.name},

CHANGE SUMMARY:
{notification.change_summary}

Category: {notification.change_category.replace('_', ' ').title()}

MATCH INFORMATION:
Teams: {match_context.get('lag1namn', 'TBD')} vs {match_context.get('lag2namn', 'TBD')}
Date: {match_context.get('speldatum', 'TBD')}
Time: {match_context.get('avsparkstid', 'TBD')}
Venue: {match_context.get('anlaggningnamn', 'TBD')}
Competition: {match_context.get('serienamn', 'TBD')}

{self._generate_field_changes_text(notification)}

Please review this information and take any necessary action.

Best regards,
FOGIS Notification System

---
This is an automated notification from the FOGIS Match List Processor.
Notification ID: {notification.notification_id}
Sent: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        """

        return text.strip()

    def _generate_field_changes_html(self, notification: ChangeNotification) -> str:
        """Generate HTML for field changes.

        Args:
            notification: Notification data

        Returns:
            HTML string for field changes
        """
        if not notification.field_changes:
            return ""

        html = '<div class="change-details"><h3>📝 Detailed Changes</h3><ul>'

        for change in notification.field_changes:
            field_name = change.get("field_name", "Unknown")
            previous = change.get("previous_value", "None")
            current = change.get("current_value", "None")
            html += f"<li><strong>{field_name}:</strong> {previous} → {current}</li>"

        html += "</ul></div>"
        return html

    def _generate_field_changes_text(self, notification: ChangeNotification) -> str:
        """Generate text for field changes.

        Args:
            notification: Notification data

        Returns:
            Text string for field changes
        """
        if not notification.field_changes:
            return ""

        text = "DETAILED CHANGES:\n"

        for change in notification.field_changes:
            field_name = change.get("field_name", "Unknown")
            previous = change.get("previous_value", "None")
            current = change.get("current_value", "None")
            text += f"- {field_name}: {previous} → {current}\n"

        return text
