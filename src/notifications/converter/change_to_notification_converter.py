"""Converter from change categorization to notifications."""

import logging
from typing import Any, Dict, List

from ...core.change_categorization import CategorizedChanges, ChangeCategory, ChangePriority
from ..models.notification_models import ChangeNotification, NotificationPriority
from ..stakeholders.stakeholder_resolver import StakeholderResolver

logger = logging.getLogger(__name__)


class ChangeToNotificationConverter:
    """Converts change categorization results to notifications."""

    def __init__(self, stakeholder_resolver: StakeholderResolver):
        """Initialize converter.

        Args:
            stakeholder_resolver: Stakeholder resolver for recipient targeting
        """
        self.stakeholder_resolver = stakeholder_resolver

        # Mapping from change priority to notification priority
        self.priority_mapping = {
            ChangePriority.CRITICAL: NotificationPriority.CRITICAL,
            ChangePriority.HIGH: NotificationPriority.HIGH,
            ChangePriority.MEDIUM: NotificationPriority.MEDIUM,
            ChangePriority.LOW: NotificationPriority.LOW,
        }

    def convert_changes_to_notifications(
        self, categorized_changes: CategorizedChanges, match_data: Dict[str, Any]
    ) -> List[ChangeNotification]:
        """Convert categorized changes to notifications.

        Args:
            categorized_changes: Categorized changes from change detector
            match_data: Match data for context

        Returns:
            List of notifications to send
        """
        if not categorized_changes or not categorized_changes.changes:
            logger.info("No changes to convert to notifications")
            return []

        notifications = []

        # Group changes by category and priority for efficient notification creation
        grouped_changes = self._group_changes_by_category_and_priority(categorized_changes.changes)

        for (category, priority), changes in grouped_changes.items():
            notification = self._create_notification_for_changes(
                changes, category, priority, match_data
            )

            if notification and notification.recipients:
                notifications.append(notification)
                logger.info(
                    f"Created notification for {category.value} with {len(notification.recipients)} recipients"
                )
            else:
                logger.warning(f"No recipients found for {category.value} notification")

        logger.info(
            f"Converted {len(categorized_changes.changes)} changes to {len(notifications)} notifications"
        )
        return notifications

    def _group_changes_by_category_and_priority(self, changes: List) -> Dict:
        """Group changes by category and priority.

        Args:
            changes: List of individual changes

        Returns:
            Dictionary mapping (category, priority) tuples to change lists
        """
        grouped: Dict[tuple, List] = {}

        for change in changes:
            key = (change.category, change.priority)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(change)

        return grouped

    def _create_notification_for_changes(
        self,
        changes: List,
        category: ChangeCategory,
        priority: ChangePriority,
        match_data: Dict[str, Any],
    ) -> ChangeNotification:
        """Create notification for a group of changes.

        Args:
            changes: List of changes in this category/priority
            category: Change category
            priority: Change priority
            match_data: Match data for context

        Returns:
            Created notification
        """
        # Generate change summary
        change_summary = self._generate_change_summary(changes, category)

        # Convert field changes to notification format
        field_changes = []
        for change in changes:
            field_changes.append(
                {
                    "field_name": change.field_name,
                    "previous_value": change.previous_value,
                    "current_value": change.current_value,
                    "change_description": change.change_description,
                }
            )

        # Resolve recipients based on change category and stakeholder types
        recipients = self.stakeholder_resolver.resolve_notification_recipients(
            match_data, category.value, priority.value
        )

        # Extract affected stakeholder types
        affected_stakeholders = []
        for change in changes:
            for stakeholder in change.affected_stakeholders:
                if stakeholder.value not in affected_stakeholders:
                    affected_stakeholders.append(stakeholder.value)

        # Create notification
        notification = ChangeNotification(
            change_category=category.value,
            priority=self.priority_mapping.get(priority, NotificationPriority.MEDIUM),
            change_summary=change_summary,
            field_changes=field_changes,
            match_context=match_data,
            affected_stakeholders=affected_stakeholders,
            recipients=recipients,
        )

        return notification

    def _generate_change_summary(self, changes: List, category: ChangeCategory) -> str:
        """Generate human-readable change summary.

        Args:
            changes: List of changes
            category: Change category

        Returns:
            Human-readable change summary
        """
        if not changes:
            return "No changes detected"

        # Category-specific summary generation
        if category == ChangeCategory.NEW_ASSIGNMENT:
            return self._generate_new_assignment_summary(changes)
        elif category == ChangeCategory.REFEREE_CHANGE:
            return self._generate_referee_change_summary(changes)
        elif category == ChangeCategory.TIME_CHANGE:
            return self._generate_time_change_summary(changes)
        elif category == ChangeCategory.DATE_CHANGE:
            return self._generate_date_change_summary(changes)
        elif category == ChangeCategory.VENUE_CHANGE:
            return self._generate_venue_change_summary(changes)
        elif category == ChangeCategory.TEAM_CHANGE:
            return self._generate_team_change_summary(changes)
        elif category == ChangeCategory.CANCELLATION:
            return "Match has been cancelled"
        elif category == ChangeCategory.POSTPONEMENT:
            return "Match has been postponed"
        else:
            # Generic summary for other categories
            if len(changes) == 1:
                return str(changes[0].change_description)
            else:
                return f"{len(changes)} changes detected in {category.value.replace('_', ' ')}"

    def _generate_new_assignment_summary(self, changes: List) -> str:
        """Generate summary for new assignments."""
        referee_count = len([c for c in changes if "referee" in c.change_description.lower()])

        if referee_count == 1:
            return "New referee assignment"
        elif referee_count > 1:
            return f"{referee_count} new referee assignments"
        else:
            return "New match assignment"

    def _generate_referee_change_summary(self, changes: List) -> str:
        """Generate summary for referee changes."""
        if len(changes) == 1:
            return "Referee assignment changed"
        else:
            return f"{len(changes)} referee assignment changes"

    def _generate_time_change_summary(self, changes: List) -> str:
        """Generate summary for time changes."""
        time_change = next((c for c in changes if c.field_name == "avsparkstid"), None)
        if time_change:
            return f"Match time changed from {time_change.previous_value} to {time_change.current_value}"
        else:
            return "Match time has been changed"

    def _generate_date_change_summary(self, changes: List) -> str:
        """Generate summary for date changes."""
        date_change = next((c for c in changes if c.field_name == "speldatum"), None)
        if date_change:
            return f"Match date changed from {date_change.previous_value} to {date_change.current_value}"
        else:
            return "Match date has been changed"

    def _generate_venue_change_summary(self, changes: List) -> str:
        """Generate summary for venue changes."""
        venue_change = next((c for c in changes if c.field_name == "anlaggningnamn"), None)
        if venue_change:
            return f"Match venue changed from {venue_change.previous_value} to {venue_change.current_value}"
        else:
            return "Match venue has been changed"

    def _generate_team_change_summary(self, changes: List) -> str:
        """Generate summary for team changes."""
        team_changes = [c for c in changes if "lag" in c.field_name]

        if len(team_changes) == 1:
            change = team_changes[0]
            team_type = "home" if "lag1" in change.field_name else "away"
            return f"{team_type.title()} team changed from {change.previous_value} to {change.current_value}"
        elif len(team_changes) > 1:
            return f"{len(team_changes)} team changes"
        else:
            return "Team information has been changed"

    def create_notification_from_match_data(
        self,
        match_data: Dict[str, Any],
        change_category: str = "new_assignment",
        priority: str = "medium",
    ) -> ChangeNotification:
        """Create notification directly from match data (for new matches).

        Args:
            match_data: Match data
            change_category: Change category
            priority: Priority level

        Returns:
            Created notification
        """
        # Resolve recipients
        recipients = self.stakeholder_resolver.resolve_notification_recipients(
            match_data, change_category, priority
        )

        # Generate summary for new match
        home_team = match_data.get("lag1namn", "TBD")
        away_team = match_data.get("lag2namn", "TBD")
        change_summary = f"New match assignment: {home_team} vs {away_team}"

        # Extract referee information for field changes
        field_changes = []
        referees = match_data.get("domaruppdraglista", [])
        for referee in referees:
            field_changes.append(
                {
                    "field_name": "referee_assignment",
                    "previous_value": "None",
                    "current_value": f"{referee.get('personnamn', 'Unknown')} ({referee.get('uppdragstyp', 'Unknown')})",
                    "change_description": f"Assigned {referee.get('personnamn', 'Unknown')} as {referee.get('uppdragstyp', 'Unknown')}",
                }
            )

        # Determine affected stakeholders
        affected_stakeholders = ["referees", "coordinators"]

        # Create notification
        notification = ChangeNotification(
            change_category=change_category,
            priority=NotificationPriority(priority),
            change_summary=change_summary,
            field_changes=field_changes,
            match_context=match_data,
            affected_stakeholders=affected_stakeholders,
            recipients=recipients,
        )

        return notification
