"""Stakeholder resolution for notification targeting."""

import logging
from typing import Any, Dict, List

from ..models.notification_models import NotificationRecipient
from .stakeholder_manager import StakeholderManager

logger = logging.getLogger(__name__)


class StakeholderResolver:
    """Resolves stakeholders who should receive notifications."""

    def __init__(self, stakeholder_manager: StakeholderManager):
        """Initialize stakeholder resolver.

        Args:
            stakeholder_manager: Stakeholder manager instance
        """
        self.stakeholder_manager = stakeholder_manager

    def resolve_notification_recipients(
        self, match_data: Dict[str, Any], change_category: str, priority: str
    ) -> List[NotificationRecipient]:
        """Resolve stakeholders who should receive notifications.

        Args:
            match_data: Match data containing referee information
            change_category: Type of change (e.g., 'new_assignment', 'time_change')
            priority: Priority level (e.g., 'critical', 'high', 'medium', 'low')

        Returns:
            List of notification recipients
        """
        recipients = []

        # Extract referee information from match data
        referees = match_data.get("domaruppdraglista", [])

        # Resolve referee stakeholders
        referee_recipients = self._resolve_referee_recipients(referees, change_category, priority)
        recipients.extend(referee_recipients)

        # Resolve coordinator stakeholders for certain change types
        if self._should_notify_coordinators(change_category, priority):
            coordinator_recipients = self._resolve_coordinator_recipients(change_category, priority)
            recipients.extend(coordinator_recipients)

        # Resolve team stakeholders for team-related changes
        if self._should_notify_teams(change_category):
            team_recipients = self._resolve_team_recipients(match_data, change_category, priority)
            recipients.extend(team_recipients)

        # Remove duplicates based on stakeholder_id and channel
        unique_recipients = self._deduplicate_recipients(recipients)

        logger.info(
            f"Resolved {len(unique_recipients)} recipients for {change_category} notification"
        )
        return unique_recipients

    def _resolve_referee_recipients(
        self, referees: List[Dict], change_category: str, priority: str
    ) -> List[NotificationRecipient]:
        """Resolve referee recipients from referee data.

        Args:
            referees: List of referee data from match
            change_category: Type of change
            priority: Priority level

        Returns:
            List of notification recipients for referees
        """
        recipients = []

        for referee_data in referees:
            # Get or create stakeholder for this referee
            stakeholder = self.stakeholder_manager.create_stakeholder_from_referee_data(
                referee_data
            )

            # Check if stakeholder should receive this notification
            if not stakeholder.should_receive_notification(change_category, priority):
                continue

            # Create recipients for each enabled channel
            for channel in stakeholder.get_enabled_channels():
                contact = stakeholder.get_contact_by_channel(channel)
                if contact and contact.active:
                    recipient = NotificationRecipient(
                        stakeholder_id=stakeholder.stakeholder_id,
                        name=stakeholder.name,
                        channel=channel,
                        address=contact.address,
                        preferences=stakeholder.preferences.to_dict(),
                    )
                    recipients.append(recipient)

        return recipients

    def _resolve_coordinator_recipients(
        self, change_category: str, priority: str
    ) -> List[NotificationRecipient]:
        """Resolve coordinator recipients.

        Args:
            change_category: Type of change
            priority: Priority level

        Returns:
            List of notification recipients for coordinators
        """
        recipients = []
        coordinators = self.stakeholder_manager.get_stakeholders_by_role("coordinator")

        for coordinator in coordinators:
            if not coordinator.should_receive_notification(change_category, priority):
                continue

            for channel in coordinator.get_enabled_channels():
                contact = coordinator.get_contact_by_channel(channel)
                if contact and contact.active:
                    recipient = NotificationRecipient(
                        stakeholder_id=coordinator.stakeholder_id,
                        name=coordinator.name,
                        channel=channel,
                        address=contact.address,
                        preferences=coordinator.preferences.to_dict(),
                    )
                    recipients.append(recipient)

        return recipients

    def _resolve_team_recipients(
        self, match_data: Dict[str, Any], change_category: str, priority: str
    ) -> List[NotificationRecipient]:
        """Resolve team recipients for team-related changes.

        Args:
            match_data: Match data
            change_category: Type of change
            priority: Priority level

        Returns:
            List of notification recipients for teams
        """
        recipients = []

        # For now, we don't have team contact information in the system
        # This would be implemented when team management is added
        # Teams would be notified through their registered contacts

        # Placeholder for future team notification implementation
        team_managers = self.stakeholder_manager.get_stakeholders_by_role("team_manager")

        for team_manager in team_managers:
            if not team_manager.should_receive_notification(change_category, priority):
                continue

            # Check if this team manager is associated with the teams in this match
            # This would require additional metadata linking team managers to teams

            for channel in team_manager.get_enabled_channels():
                contact = team_manager.get_contact_by_channel(channel)
                if contact and contact.active:
                    recipient = NotificationRecipient(
                        stakeholder_id=team_manager.stakeholder_id,
                        name=team_manager.name,
                        channel=channel,
                        address=contact.address,
                        preferences=team_manager.preferences.to_dict(),
                    )
                    recipients.append(recipient)

        return recipients

    def _should_notify_coordinators(self, change_category: str, priority: str) -> bool:
        """Check if coordinators should be notified for this change.

        Args:
            change_category: Type of change
            priority: Priority level

        Returns:
            True if coordinators should be notified
        """
        # Coordinators should be notified for:
        # - All new assignments
        # - All referee changes
        # - Critical priority changes
        # - Cancellations and postponements
        coordinator_change_types = {
            "new_assignment",
            "referee_change",
            "cancellation",
            "postponement",
            "status_change",
        }

        return change_category in coordinator_change_types or priority == "critical"

    def _should_notify_teams(self, change_category: str) -> bool:
        """Check if teams should be notified for this change.

        Args:
            change_category: Type of change

        Returns:
            True if teams should be notified
        """
        # Teams should be notified for:
        # - Time changes
        # - Date changes
        # - Venue changes
        # - Cancellations
        # - Team-related changes
        team_change_types = {
            "time_change",
            "date_change",
            "venue_change",
            "cancellation",
            "postponement",
            "team_change",
        }

        return change_category in team_change_types

    def _deduplicate_recipients(
        self, recipients: List[NotificationRecipient]
    ) -> List[NotificationRecipient]:
        """Remove duplicate recipients based on stakeholder_id and channel.

        Args:
            recipients: List of recipients that may contain duplicates

        Returns:
            List of unique recipients
        """
        seen = set()
        unique_recipients = []

        for recipient in recipients:
            key = (recipient.stakeholder_id, recipient.channel.value)
            if key not in seen:
                seen.add(key)
                unique_recipients.append(recipient)

        return unique_recipients

    def get_recipients_for_stakeholder_types(
        self, stakeholder_types: List[str], change_category: str, priority: str
    ) -> List[NotificationRecipient]:
        """Get recipients for specific stakeholder types.

        Args:
            stakeholder_types: List of stakeholder types (e.g., ['referees', 'coordinators'])
            change_category: Type of change
            priority: Priority level

        Returns:
            List of notification recipients
        """
        recipients = []

        for stakeholder_type in stakeholder_types:
            if stakeholder_type == "referees":
                # For referees, we need match data - this would be called differently
                continue
            elif stakeholder_type == "coordinators":
                coordinator_recipients = self._resolve_coordinator_recipients(
                    change_category, priority
                )
                recipients.extend(coordinator_recipients)
            elif stakeholder_type == "teams":
                # For teams, we need match data - this would be called differently
                continue
            elif stakeholder_type == "all":
                # Get all active stakeholders
                all_stakeholders = self.stakeholder_manager.get_all_stakeholders()
                for stakeholder in all_stakeholders:
                    if not stakeholder.should_receive_notification(change_category, priority):
                        continue

                    for channel in stakeholder.get_enabled_channels():
                        contact = stakeholder.get_contact_by_channel(channel)
                        if contact and contact.active:
                            recipient = NotificationRecipient(
                                stakeholder_id=stakeholder.stakeholder_id,
                                name=stakeholder.name,
                                channel=channel,
                                address=contact.address,
                                preferences=stakeholder.preferences.to_dict(),
                            )
                            recipients.append(recipient)

        return self._deduplicate_recipients(recipients)
