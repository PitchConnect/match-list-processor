"""Advanced email template engine for notifications."""

import logging
import os
from string import Template
from typing import Any, Dict, Optional

from .template_models import NotificationTemplate, RenderedTemplate, TemplateContext, TemplateType

logger = logging.getLogger(__name__)


class EmailTemplateEngine:
    """Advanced email template engine with HTML and text support."""

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize template engine.

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "default_templates"
        )
        self._templates: Dict[TemplateType, NotificationTemplate] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default email templates."""
        # New assignment template
        self._templates[TemplateType.NEW_ASSIGNMENT] = NotificationTemplate(
            template_type=TemplateType.NEW_ASSIGNMENT,
            name="New Referee Assignment",
            description="Notification for new referee assignments",
            subject_template="⚽ New Assignment: ${match_team1} vs ${match_team2} - ${match_date}",
            html_template=self._get_new_assignment_html_template(),
            text_template=self._get_new_assignment_text_template(),
        )

        # Time change template
        self._templates[TemplateType.TIME_CHANGE] = NotificationTemplate(
            template_type=TemplateType.TIME_CHANGE,
            name="Match Time Change",
            description="Notification for match time changes",
            subject_template="🕐 Time Change: ${match_team1} vs ${match_team2} - Now ${match_time}",
            html_template=self._get_time_change_html_template(),
            text_template=self._get_time_change_text_template(),
        )

        # Venue change template
        self._templates[TemplateType.VENUE_CHANGE] = NotificationTemplate(
            template_type=TemplateType.VENUE_CHANGE,
            name="Venue Change",
            description="Notification for venue changes",
            subject_template="📍 Venue Change: ${match_team1} vs ${match_team2} - ${match_venue}",
            html_template=self._get_venue_change_html_template(),
            text_template=self._get_venue_change_text_template(),
        )

        # Cancellation template
        self._templates[TemplateType.CANCELLATION] = NotificationTemplate(
            template_type=TemplateType.CANCELLATION,
            name="Match Cancellation",
            description="Notification for match cancellations",
            subject_template="❌ CANCELLED: ${match_team1} vs ${match_team2} - ${match_date}",
            html_template=self._get_cancellation_html_template(),
            text_template=self._get_cancellation_text_template(),
        )

    def render_template(
        self, template_type: TemplateType, context: TemplateContext
    ) -> RenderedTemplate:
        """Render template with context data.

        Args:
            template_type: Type of template to render
            context: Context data for rendering

        Returns:
            Rendered template ready for delivery
        """
        template = self._templates.get(template_type)
        if not template:
            logger.warning(f"Template not found for type: {template_type}")
            # Fall back to basic template
            template = self._get_fallback_template(template_type)

        context_dict = context.to_dict()

        try:
            # Flatten context for template substitution
            flat_context = self._flatten_context(context_dict)

            # Check if critical fields are missing
            if not flat_context.get("match_team1") or not flat_context.get("match_team2"):
                logger.warning("Critical template fields missing, using fallback")
                return self._get_fallback_rendered_template(template_type, context)

            # Render subject
            subject_template = Template(template.subject_template)
            subject = subject_template.safe_substitute(flat_context)

            # Render HTML content
            html_template = Template(template.html_template)
            html_content = html_template.safe_substitute(flat_context)

            # Render text content
            text_template = Template(template.text_template)
            text_content = text_template.safe_substitute(flat_context)

            return RenderedTemplate(
                template_type=template_type,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                context=context,
            )

        except Exception as e:
            logger.error(f"Template rendering failed for {template_type}: {e}")
            return self._get_fallback_rendered_template(template_type, context)

    def get_template(self, template_type: TemplateType) -> Optional[NotificationTemplate]:
        """Get template by type.

        Args:
            template_type: Template type to retrieve

        Returns:
            Template if found, None otherwise
        """
        return self._templates.get(template_type)

    def add_template(self, template: NotificationTemplate) -> None:
        """Add or update template.

        Args:
            template: Template to add
        """
        self._templates[template.template_type] = template
        logger.info(f"Added template: {template.name}")

    def _flatten_context(self, context_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested context dictionary for template substitution.

        Args:
            context_dict: Nested context dictionary

        Returns:
            Flattened dictionary with underscore notation keys for Python Template
        """
        flat_dict = {}

        def _flatten_recursive(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}_{key}" if prefix else key
                    if isinstance(value, dict):
                        _flatten_recursive(value, new_key)
                    else:
                        flat_dict[new_key] = str(value) if value is not None else ""
            else:
                flat_dict[prefix] = str(obj) if obj is not None else ""

        _flatten_recursive(context_dict)
        return flat_dict

    def _get_new_assignment_html_template(self) -> str:
        """Get HTML template for new assignments."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Referee Assignment</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: ${branding_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .match-info { background: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0; }
        .highlight { color: ${branding_color}; font-weight: bold; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: ${branding_color}; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚽ New Referee Assignment</h1>
            <p>You have been assigned to officiate a match</p>
        </div>
        <div class="content">
            <p>Hello <strong>${recipient_name}</strong>,</p>

            <p>You have been assigned as <span class="highlight">${recipient_role}</span> for the following match:</p>

            <div class="match-info">
                <h3>${match_team1} vs ${match_team2}</h3>
                <p><strong>Date:</strong> ${match_date}</p>
                <p><strong>Time:</strong> ${match_time}</p>
                <p><strong>Venue:</strong> ${match_venue}</p>
                <p><strong>Series:</strong> ${match_series}</p>
                <p><strong>Match Number:</strong> ${match_number}</p>
            </div>

            <p>Please confirm your availability and prepare for the match. If you have any questions or concerns, please contact the match coordinator immediately.</p>

            <p><strong>Important:</strong> Please arrive at the venue at least 30 minutes before kick-off.</p>
        </div>
        <div class="footer">
            <p>${branding_footer}</p>
            <p>Notification ID: ${system_notification_id}</p>
            <p>If you have questions, contact: ${system_support_email}</p>
        </div>
    </div>
</body>
</html>
        """.strip()

    def _get_new_assignment_text_template(self) -> str:
        """Get text template for new assignments."""
        return """
⚽ NEW REFEREE ASSIGNMENT

Hello ${recipient_name},

You have been assigned as ${recipient_role} for the following match:

MATCH DETAILS:
${match_team1} vs ${match_team2}
Date: ${match_date}
Time: ${match_time}
Venue: ${match_venue}
Series: ${match_series}
Match Number: ${match_number}

Please confirm your availability and prepare for the match. If you have any questions or concerns, please contact the match coordinator immediately.

IMPORTANT: Please arrive at the venue at least 30 minutes before kick-off.

---
${branding_footer}
Notification ID: ${system_notification_id}
Support: ${system_support_email}
        """.strip()

    def _get_time_change_html_template(self) -> str:
        """Get HTML template for time changes."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Match Time Change</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .match-info { background: #fef3c7; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #f59e0b; }
        .highlight { color: #f59e0b; font-weight: bold; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }
        .alert { background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 15px; border-radius: 4px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕐 Match Time Change</h1>
            <p>Important update for your assigned match</p>
        </div>
        <div class="content">
            <div class="alert">
                <strong>ATTENTION:</strong> The match time has been changed!
            </div>

            <p>Hello <strong>${recipient_name}</strong>,</p>

            <p>The time for your assigned match has been updated:</p>

            <div class="match-info">
                <h3>${match_team1} vs ${match_team2}</h3>
                <p><strong>Date:</strong> ${match_date}</p>
                <p><strong>NEW Time:</strong> <span class="highlight">${match_time}</span></p>
                <p><strong>Venue:</strong> ${match_venue}</p>
                <p><strong>Your Role:</strong> ${recipient_role}</p>
            </div>

            <p>Please update your calendar and ensure you can still attend at the new time. If this change creates a conflict, please contact the match coordinator immediately.</p>
        </div>
        <div class="footer">
            <p>${branding.footer}</p>
            <p>Notification ID: ${system.notification_id}</p>
        </div>
    </div>
</body>
</html>
        """.strip()

    def _get_time_change_text_template(self) -> str:
        """Get text template for time changes."""
        return """
🕐 MATCH TIME CHANGE

ATTENTION: The match time has been changed!

Hello ${recipient.name},

The time for your assigned match has been updated:

UPDATED MATCH DETAILS:
${match.team1} vs ${match.team2}
Date: ${match.date}
NEW Time: ${match.time}
Venue: ${match.venue}
Your Role: ${recipient.role}

Please update your calendar and ensure you can still attend at the new time. If this change creates a conflict, please contact the match coordinator immediately.

---
${branding.footer}
Notification ID: ${system.notification_id}
        """.strip()

    def _get_venue_change_html_template(self) -> str:
        """Get HTML template for venue changes."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Venue Change</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #8b5cf6; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .match-info { background: #f3f4f6; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #8b5cf6; }
        .highlight { color: #8b5cf6; font-weight: bold; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }
        .alert { background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 15px; border-radius: 4px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📍 Venue Change</h1>
            <p>Important location update for your match</p>
        </div>
        <div class="content">
            <div class="alert">
                <strong>ATTENTION:</strong> The match venue has been changed!
            </div>

            <p>Hello <strong>${recipient.name}</strong>,</p>

            <p>The venue for your assigned match has been updated:</p>

            <div class="match-info">
                <h3>${match.team1} vs ${match.team2}</h3>
                <p><strong>Date:</strong> ${match.date}</p>
                <p><strong>Time:</strong> ${match.time}</p>
                <p><strong>NEW Venue:</strong> <span class="highlight">${match.venue}</span></p>
                <p><strong>Your Role:</strong> ${recipient.role}</p>
            </div>

            <p>Please note the new location and plan your travel accordingly. Make sure to arrive at least 30 minutes before kick-off at the new venue.</p>
        </div>
        <div class="footer">
            <p>${branding.footer}</p>
            <p>Notification ID: ${system.notification_id}</p>
        </div>
    </div>
</body>
</html>
        """.strip()

    def _get_venue_change_text_template(self) -> str:
        """Get text template for venue changes."""
        return """
📍 VENUE CHANGE

ATTENTION: The match venue has been changed!

Hello ${recipient.name},

The venue for your assigned match has been updated:

UPDATED MATCH DETAILS:
${match.team1} vs ${match.team2}
Date: ${match.date}
Time: ${match.time}
NEW Venue: ${match.venue}
Your Role: ${recipient.role}

Please note the new location and plan your travel accordingly. Make sure to arrive at least 30 minutes before kick-off at the new venue.

---
${branding.footer}
Notification ID: ${system.notification_id}
        """.strip()

    def _get_cancellation_html_template(self) -> str:
        """Get HTML template for cancellations."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Match Cancelled</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center; }
        .content { padding: 30px; }
        .match-info { background: #fef2f2; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #dc2626; }
        .highlight { color: #dc2626; font-weight: bold; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>❌ Match Cancelled</h1>
            <p>Your assigned match has been cancelled</p>
        </div>
        <div class="content">
            <p>Hello <strong>${recipient.name}</strong>,</p>

            <p>Unfortunately, the following match has been <span class="highlight">CANCELLED</span>:</p>

            <div class="match-info">
                <h3>${match.team1} vs ${match.team2}</h3>
                <p><strong>Original Date:</strong> ${match.date}</p>
                <p><strong>Original Time:</strong> ${match.time}</p>
                <p><strong>Venue:</strong> ${match.venue}</p>
                <p><strong>Your Role:</strong> ${recipient.role}</p>
            </div>

            <p>You are no longer required to attend this match. Please update your calendar accordingly.</p>

            <p>If you have any questions about this cancellation, please contact the match coordinator.</p>
        </div>
        <div class="footer">
            <p>${branding.footer}</p>
            <p>Notification ID: ${system.notification_id}</p>
        </div>
    </div>
</body>
</html>
        """.strip()

    def _get_cancellation_text_template(self) -> str:
        """Get text template for cancellations."""
        return """
❌ MATCH CANCELLED

Hello ${recipient.name},

Unfortunately, the following match has been CANCELLED:

CANCELLED MATCH:
${match.team1} vs ${match.team2}
Original Date: ${match.date}
Original Time: ${match.time}
Venue: ${match.venue}
Your Role: ${recipient.role}

You are no longer required to attend this match. Please update your calendar accordingly.

If you have any questions about this cancellation, please contact the match coordinator.

---
${branding.footer}
Notification ID: ${system.notification_id}
        """.strip()

    def _get_fallback_template(self, template_type: TemplateType) -> NotificationTemplate:
        """Get fallback template for unknown types."""
        return NotificationTemplate(
            template_type=template_type,
            name="Generic Notification",
            description="Fallback template for unknown notification types",
            subject_template="FOGIS Notification: ${change_summary}",
            html_template="<p>Hello ${recipient_name},</p><p>${change_summary}</p><p>Match: ${match_team1} vs ${match_team2}</p>",
            text_template="Hello ${recipient_name},\n\n${change_summary}\n\nMatch: ${match_team1} vs ${match_team2}",
        )

    def _get_fallback_rendered_template(
        self, template_type: TemplateType, context: TemplateContext
    ) -> RenderedTemplate:
        """Get fallback rendered template for errors."""
        return RenderedTemplate(
            template_type=template_type,
            subject=f"FOGIS Notification: {context.change_summary}",
            html_content=f"<p>Hello {context.recipient_name},</p><p>{context.change_summary}</p>",
            text_content=f"Hello {context.recipient_name},\n\n{context.change_summary}",
            context=context,
        )
