"""Tests for notification template system."""

import unittest

from src.notifications.templates.email_templates import EmailTemplateEngine
from src.notifications.templates.template_models import (
    NotificationTemplate,
    TemplateContext,
    TemplateType,
)


class TestTemplateModels(unittest.TestCase):
    """Test template models."""

    def test_template_context_creation(self):
        """Test template context creation."""
        context = TemplateContext(
            match_id="12345",
            match_number="1",
            team1_name="Team A",
            team2_name="Team B",
            match_date="2025-09-01",
            match_time="14:00",
            venue_name="Test Stadium",
            series_name="Test League",
            change_type="new_assignment",
            change_summary="New referee assignment",
            recipient_name="Test Referee",
            recipient_role="Huvuddomare",
        )

        self.assertEqual(context.match_id, "12345")
        self.assertEqual(context.team1_name, "Team A")
        self.assertEqual(context.change_type, "new_assignment")

        # Test dictionary conversion
        context_dict = context.to_dict()
        self.assertIn("match", context_dict)
        self.assertIn("change", context_dict)
        self.assertIn("recipient", context_dict)
        self.assertEqual(context_dict["match"]["team1"], "Team A")

    def test_notification_template_creation(self):
        """Test notification template creation."""
        template = NotificationTemplate(
            template_type=TemplateType.NEW_ASSIGNMENT,
            name="Test Template",
            description="Test description",
            subject_template="Test Subject: ${match.team1} vs ${match.team2}",
            html_template="<p>Test HTML</p>",
            text_template="Test Text",
        )

        self.assertEqual(template.template_type, TemplateType.NEW_ASSIGNMENT)
        self.assertEqual(template.name, "Test Template")
        self.assertTrue(template.is_active)

        # Test dictionary conversion
        template_dict = template.to_dict()
        self.assertEqual(template_dict["template_type"], "new_assignment")
        self.assertEqual(template_dict["name"], "Test Template")

        # Test from dictionary
        restored_template = NotificationTemplate.from_dict(template_dict)
        self.assertEqual(restored_template.template_type, TemplateType.NEW_ASSIGNMENT)
        self.assertEqual(restored_template.name, "Test Template")


class TestEmailTemplateEngine(unittest.TestCase):
    """Test email template engine."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = EmailTemplateEngine()
        self.context = TemplateContext(
            match_id="12345",
            match_number="1",
            team1_name="Team Alpha",
            team2_name="Team Beta",
            match_date="2025-09-01",
            match_time="14:00",
            venue_name="Test Stadium",
            series_name="Test League",
            change_type="new_assignment",
            change_summary="New referee assignment",
            recipient_name="Test Referee",
            recipient_role="Huvuddomare",
        )

    def test_engine_initialization(self):
        """Test template engine initialization."""
        self.assertIsInstance(self.engine, EmailTemplateEngine)
        self.assertIn(TemplateType.NEW_ASSIGNMENT, self.engine._templates)
        self.assertIn(TemplateType.TIME_CHANGE, self.engine._templates)
        self.assertIn(TemplateType.VENUE_CHANGE, self.engine._templates)
        self.assertIn(TemplateType.CANCELLATION, self.engine._templates)

    def test_render_new_assignment_template(self):
        """Test rendering new assignment template."""
        rendered = self.engine.render_template(TemplateType.NEW_ASSIGNMENT, self.context)

        self.assertEqual(rendered.template_type, TemplateType.NEW_ASSIGNMENT)
        self.assertIn("Team Alpha", rendered.subject)
        self.assertIn("Team Beta", rendered.subject)
        self.assertIn("Test Referee", rendered.html_content)
        self.assertIn("Huvuddomare", rendered.html_content)
        self.assertIn("Test Stadium", rendered.html_content)

        # Check text content
        self.assertIn("Team Alpha", rendered.text_content)
        self.assertIn("Test Referee", rendered.text_content)

    def test_render_time_change_template(self):
        """Test rendering time change template."""
        self.context.change_type = "time_change"
        self.context.change_summary = "Match time changed"

        rendered = self.engine.render_template(TemplateType.TIME_CHANGE, self.context)

        self.assertEqual(rendered.template_type, TemplateType.TIME_CHANGE)
        self.assertIn("Time Change", rendered.subject)
        self.assertIn("14:00", rendered.subject)
        self.assertIn("ATTENTION", rendered.html_content)
        self.assertIn("time has been changed", rendered.html_content)

    def test_render_venue_change_template(self):
        """Test rendering venue change template."""
        self.context.change_type = "venue_change"
        self.context.change_summary = "Venue changed"

        rendered = self.engine.render_template(TemplateType.VENUE_CHANGE, self.context)

        self.assertEqual(rendered.template_type, TemplateType.VENUE_CHANGE)
        self.assertIn("Venue Change", rendered.subject)
        self.assertIn("Test Stadium", rendered.subject)
        self.assertIn("venue has been changed", rendered.html_content)

    def test_render_cancellation_template(self):
        """Test rendering cancellation template."""
        self.context.change_type = "cancellation"
        self.context.change_summary = "Match cancelled"

        rendered = self.engine.render_template(TemplateType.CANCELLATION, self.context)

        self.assertEqual(rendered.template_type, TemplateType.CANCELLATION)
        self.assertIn("CANCELLED", rendered.subject)
        self.assertIn("CANCELLED", rendered.html_content)
        self.assertIn("no longer required", rendered.html_content)

    def test_get_template(self):
        """Test getting template by type."""
        template = self.engine.get_template(TemplateType.NEW_ASSIGNMENT)
        self.assertIsNotNone(template)
        self.assertEqual(template.template_type, TemplateType.NEW_ASSIGNMENT)

        # Test non-existent template
        template = self.engine.get_template(TemplateType.DIGEST)
        self.assertIsNone(template)

    def test_add_custom_template(self):
        """Test adding custom template."""
        custom_template = NotificationTemplate(
            template_type=TemplateType.REMINDER,
            name="Custom Reminder",
            description="Custom reminder template",
            subject_template="Reminder: ${match_team1} vs ${match_team2}",
            html_template="<p>Reminder: ${change_summary}</p>",
            text_template="Reminder: ${change_summary}",
        )

        self.engine.add_template(custom_template)

        # Test retrieval
        retrieved = self.engine.get_template(TemplateType.REMINDER)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Custom Reminder")

        # Test rendering
        self.context.change_summary = "Match reminder"
        rendered = self.engine.render_template(TemplateType.REMINDER, self.context)
        self.assertIn("Reminder", rendered.subject)
        self.assertIn("Match reminder", rendered.html_content)

    def test_fallback_template_for_unknown_type(self):
        """Test fallback template for unknown types."""
        # This should use fallback template
        rendered = self.engine.render_template(TemplateType.DIGEST, self.context)

        self.assertEqual(rendered.template_type, TemplateType.DIGEST)
        self.assertIn("FOGIS Notification", rendered.subject)
        self.assertIn("Team Alpha", rendered.html_content)

    def test_template_rendering_error_handling(self):
        """Test template rendering with invalid context."""
        # Create context with missing required fields
        invalid_context = TemplateContext(
            match_id="",
            match_number="",
            team1_name="",
            team2_name="",
            match_date="",
            match_time="",
            venue_name="",
            series_name="",
            change_type="",
            change_summary="Test",
        )

        # Should still render without errors (using fallback)
        rendered = self.engine.render_template(TemplateType.NEW_ASSIGNMENT, invalid_context)
        self.assertIsNotNone(rendered)
        self.assertIn("Test", rendered.subject)

    def test_html_template_structure(self):
        """Test HTML template structure and styling."""
        rendered = self.engine.render_template(TemplateType.NEW_ASSIGNMENT, self.context)

        # Check for proper HTML structure
        self.assertIn("<!DOCTYPE html>", rendered.html_content)
        self.assertIn("<html>", rendered.html_content)
        self.assertIn("<head>", rendered.html_content)
        self.assertIn("<body>", rendered.html_content)

        # Check for styling
        self.assertIn("font-family", rendered.html_content)
        self.assertIn("color:", rendered.html_content)

        # Check for responsive design
        self.assertIn("viewport", rendered.html_content)
        self.assertIn("max-width", rendered.html_content)

    def test_template_branding_customization(self):
        """Test template branding customization."""
        self.context.brand_color = "#ff0000"
        self.context.footer_text = "Custom Footer"
        self.context.system_name = "Custom System"

        rendered = self.engine.render_template(TemplateType.NEW_ASSIGNMENT, self.context)

        self.assertIn("#ff0000", rendered.html_content)
        self.assertIn("Custom Footer", rendered.html_content)


if __name__ == "__main__":
    unittest.main()
