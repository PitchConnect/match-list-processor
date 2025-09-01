"""Stakeholder management for notification system."""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from ..models.notification_models import NotificationChannel
from ..models.stakeholder_models import ContactInfo, NotificationPreferences, Stakeholder

logger = logging.getLogger(__name__)


class StakeholderManager:
    """Manages stakeholder data and preferences."""

    def __init__(self, storage_path: str = "data/stakeholders.json"):
        """Initialize stakeholder manager.

        Args:
            storage_path: Path to stakeholder data file
        """
        self.storage_path = storage_path
        self.stakeholders: Dict[str, Stakeholder] = {}
        self._ensure_storage_directory()
        self._load_stakeholders()

    def _ensure_storage_directory(self) -> None:
        """Ensure storage directory exists."""
        directory = os.path.dirname(self.storage_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _load_stakeholders(self) -> None:
        """Load stakeholders from storage."""
        if not os.path.exists(self.storage_path):
            logger.info(
                f"Stakeholder file {self.storage_path} not found, starting with empty database"
            )
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.stakeholders = {}
            for stakeholder_data in data.get("stakeholders", []):
                stakeholder = Stakeholder.from_dict(stakeholder_data)
                self.stakeholders[stakeholder.stakeholder_id] = stakeholder

            logger.info(f"Loaded {len(self.stakeholders)} stakeholders from {self.storage_path}")

        except Exception as e:
            logger.error(f"Error loading stakeholders from {self.storage_path}: {e}")
            self.stakeholders = {}

    def _save_stakeholders(self) -> None:
        """Save stakeholders to storage."""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "stakeholders": [s.to_dict() for s in self.stakeholders.values()],
            }

            # Write to temporary file first, then rename for atomic operation
            temp_path = f"{self.storage_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            os.rename(temp_path, self.storage_path)
            logger.debug(f"Saved {len(self.stakeholders)} stakeholders to {self.storage_path}")

        except Exception as e:
            logger.error(f"Error saving stakeholders to {self.storage_path}: {e}")

    def register_stakeholder(self, stakeholder: Stakeholder) -> None:
        """Register a new stakeholder or update existing one.

        Args:
            stakeholder: Stakeholder to register
        """
        stakeholder.updated_at = datetime.utcnow()
        self.stakeholders[stakeholder.stakeholder_id] = stakeholder
        self._save_stakeholders()
        logger.info(f"Registered stakeholder: {stakeholder.name} ({stakeholder.stakeholder_id})")

    def get_stakeholder(self, stakeholder_id: str) -> Optional[Stakeholder]:
        """Get stakeholder by ID.

        Args:
            stakeholder_id: Stakeholder ID

        Returns:
            Stakeholder if found, None otherwise
        """
        return self.stakeholders.get(stakeholder_id)

    def get_stakeholder_by_fogis_id(self, fogis_person_id: str) -> Optional[Stakeholder]:
        """Get stakeholder by FOGIS person ID.

        Args:
            fogis_person_id: FOGIS person ID

        Returns:
            Stakeholder if found, None otherwise
        """
        for stakeholder in self.stakeholders.values():
            if stakeholder.fogis_person_id == fogis_person_id:
                return stakeholder
        return None

    def get_stakeholders_by_role(self, role: str) -> List[Stakeholder]:
        """Get all stakeholders with a specific role.

        Args:
            role: Role to filter by

        Returns:
            List of stakeholders with the specified role
        """
        return [s for s in self.stakeholders.values() if s.role == role and s.active]

    def get_all_stakeholders(self) -> List[Stakeholder]:
        """Get all active stakeholders.

        Returns:
            List of all active stakeholders
        """
        return [s for s in self.stakeholders.values() if s.active]

    def create_stakeholder_from_referee_data(self, referee_data: Dict) -> Stakeholder:
        """Create stakeholder from FOGIS referee data.

        Args:
            referee_data: Referee data from FOGIS API

        Returns:
            Created stakeholder
        """
        person_id = str(referee_data.get("personid", ""))
        name = referee_data.get("personnamn", "Unknown")
        email = referee_data.get("epostadress", "")

        # Check if stakeholder already exists
        existing = self.get_stakeholder_by_fogis_id(person_id)
        if existing:
            return existing

        # Create new stakeholder
        stakeholder = Stakeholder(
            name=name,
            role="referee",
            fogis_person_id=person_id,
        )

        # Add email contact if available
        if email:
            stakeholder.add_contact_info(NotificationChannel.EMAIL, email, verified=False)

        # Set default preferences for referees
        stakeholder.preferences = NotificationPreferences(
            enabled_channels={NotificationChannel.EMAIL},
            enabled_change_types={
                "new_assignment",
                "referee_change",
                "time_change",
                "date_change",
                "venue_change",
                "cancellation",
            },
            minimum_priority="medium",
        )

        self.register_stakeholder(stakeholder)
        return stakeholder

    def update_stakeholder_preferences(
        self, stakeholder_id: str, preferences: NotificationPreferences
    ) -> bool:
        """Update stakeholder preferences.

        Args:
            stakeholder_id: Stakeholder ID
            preferences: New preferences

        Returns:
            True if updated successfully, False otherwise
        """
        stakeholder = self.get_stakeholder(stakeholder_id)
        if not stakeholder:
            return False

        stakeholder.preferences = preferences
        stakeholder.updated_at = datetime.utcnow()
        self._save_stakeholders()
        logger.info(f"Updated preferences for stakeholder: {stakeholder.name}")
        return True

    def add_contact_info(
        self,
        stakeholder_id: str,
        channel: NotificationChannel,
        address: str,
        verified: bool = False,
    ) -> bool:
        """Add contact information to stakeholder.

        Args:
            stakeholder_id: Stakeholder ID
            channel: Notification channel
            address: Contact address
            verified: Whether contact is verified

        Returns:
            True if added successfully, False otherwise
        """
        stakeholder = self.get_stakeholder(stakeholder_id)
        if not stakeholder:
            return False

        stakeholder.add_contact_info(channel, address, verified)
        self._save_stakeholders()
        logger.info(f"Added {channel.value} contact for stakeholder: {stakeholder.name}")
        return True

    def deactivate_stakeholder(self, stakeholder_id: str) -> bool:
        """Deactivate a stakeholder.

        Args:
            stakeholder_id: Stakeholder ID

        Returns:
            True if deactivated successfully, False otherwise
        """
        stakeholder = self.get_stakeholder(stakeholder_id)
        if not stakeholder:
            return False

        stakeholder.active = False
        stakeholder.updated_at = datetime.utcnow()
        self._save_stakeholders()
        logger.info(f"Deactivated stakeholder: {stakeholder.name}")
        return True

    def get_statistics(self) -> Dict:
        """Get stakeholder statistics.

        Returns:
            Dictionary with stakeholder statistics
        """
        total = len(self.stakeholders)
        active = len([s for s in self.stakeholders.values() if s.active])
        by_role = {}
        by_channel = {}

        for stakeholder in self.stakeholders.values():
            if not stakeholder.active:
                continue

            # Count by role
            role = stakeholder.role or "unknown"
            by_role[role] = by_role.get(role, 0) + 1

            # Count by enabled channels
            for channel in stakeholder.preferences.enabled_channels:
                channel_name = channel.value
                by_channel[channel_name] = by_channel.get(channel_name, 0) + 1

        return {
            "total_stakeholders": total,
            "active_stakeholders": active,
            "inactive_stakeholders": total - active,
            "by_role": by_role,
            "by_channel": by_channel,
        }
