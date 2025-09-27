#!/usr/bin/env python3
"""
Message Formatter for Redis Integration

Provides message formatting utilities for Redis pub/sub integration.
Includes Enhanced Schema v2.0 with Organization ID mapping for logo service integration.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class MatchUpdateMessageFormatter:
    """Formats match update messages for Redis publishing."""

    @staticmethod
    def format_match_updates(
        matches: List[Dict], changes: Dict, metadata: Optional[Dict] = None
    ) -> str:
        """
        Format match updates message for Redis publishing (Legacy v1.0).

        Args:
            matches: List of match dictionaries
            changes: Change detection results
            metadata: Additional processing metadata

        Returns:
            str: JSON formatted message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": matches,
                "metadata": {
                    "total_matches": len(matches),
                    "has_changes": bool(changes),
                    "change_summary": changes.get("summary", {}),
                    "processing_timestamp": datetime.utcnow().isoformat() + "Z",
                    **(metadata or {}),
                },
            },
        }

        return json.dumps(message, ensure_ascii=False)


class EnhancedSchemaV2Formatter:
    """
    Enhanced Schema v2.0 formatter with Organization ID mapping for logo service integration.

    Addresses issue #69: Uses Organization IDs (lag1foreningid/lag2foreningid) for logo service
    instead of Team Database IDs (lag1lagid/lag2lagid) to generate real team logos.
    """

    @staticmethod
    def format_match_updates_v2(
        matches: List[Dict], changes_summary: Optional[Dict] = None, metadata: Optional[Dict] = None
    ) -> str:
        """
        Format match updates using Enhanced Schema v2.0 with corrected Organization ID mapping.

        Args:
            matches: List of FOGIS match objects
            changes_summary: Change detection results with detailed_changes
            metadata: Optional metadata

        Returns:
            JSON string with Enhanced Schema v2.0 structure
        """
        processed_matches = []
        detailed_changes = []

        # Process changes summary if provided
        if changes_summary and hasattr(changes_summary, "get"):
            detailed_changes = changes_summary.get("detailed_changes", [])
        elif isinstance(changes_summary, dict):
            detailed_changes = changes_summary.get("detailed_changes", [])

        for match in matches:
            # Extract team information with Organization ID mapping
            home_team = {
                "name": match.get("lag1namn", "N/A"),
                "id": match.get("lag1lagid"),  # Database ID for references
                "logo_id": match.get("lag1foreningid"),  # Organization ID for logo service
                "organization_id": match.get("lag1foreningid"),
            }

            away_team = {
                "name": match.get("lag2namn", "N/A"),
                "id": match.get("lag2lagid"),  # Database ID for references
                "logo_id": match.get("lag2foreningid"),  # Organization ID for logo service
                "organization_id": match.get("lag2foreningid"),
            }

            # Extract referee information with full contact data
            referees = []
            for referee in match.get("domaruppdraglista", []):
                referee_data = {
                    "name": referee.get("namn", "N/A"),
                    "role": referee.get("uppdragstyp", "N/A"),
                }

                # Add contact information if available
                if referee.get("mobil") or referee.get("epost"):
                    referee_data["contact"] = {}
                    if referee.get("mobil"):
                        referee_data["contact"]["mobile"] = referee.get("mobil")
                    if referee.get("epost"):
                        referee_data["contact"]["email"] = referee.get("epost")

                    # Add address information if available
                    if any(
                        [referee.get("adress"), referee.get("postnummer"), referee.get("postort")]
                    ):
                        referee_data["contact"]["address"] = {
                            "street": referee.get("adress", ""),
                            "postal_code": referee.get("postnummer", ""),
                            "city": referee.get("postort", ""),
                        }

                referees.append(referee_data)

            # Extract team contacts if available
            team_contacts = []
            if match.get("lag1kontakt"):
                team_contacts.append(
                    {
                        "name": match.get("lag1kontakt", {}).get("namn", "N/A"),
                        "team_name": match.get("lag1namn", "N/A"),
                        "contact": {
                            "mobile": match.get("lag1kontakt", {}).get("mobil", ""),
                            "email": match.get("lag1kontakt", {}).get("epost", ""),
                        },
                    }
                )

            if match.get("lag2kontakt"):
                team_contacts.append(
                    {
                        "name": match.get("lag2kontakt", {}).get("namn", "N/A"),
                        "team_name": match.get("lag2namn", "N/A"),
                        "contact": {
                            "mobile": match.get("lag2kontakt", {}).get("mobil", ""),
                            "email": match.get("lag2kontakt", {}).get("epost", ""),
                        },
                    }
                )

            processed_match = {
                "match_id": match.get("matchid"),
                "teams": {"home": home_team, "away": away_team},
                "date": match.get("speldatum"),
                "time": match.get("avsparkstid"),
                "venue": {
                    "name": match.get("anlaggningnamn", "N/A"),
                    "address": match.get("anlaggningadress", ""),
                },
                "referees": referees,
                "team_contacts": team_contacts,
                "series": {
                    "name": match.get("serienamn", "N/A"),
                    "level": match.get("serieniva", "N/A"),
                },
                "status": match.get("matchstatus", "scheduled"),
            }

            processed_matches.append(processed_match)

        # Create Enhanced Schema v2.0 message
        message = {
            "schema_version": "2.0",
            "schema_type": "enhanced_with_contacts_and_logo_ids",
            "backward_compatible": True,
            "new_fields": [
                "teams.home.logo_id",
                "teams.away.logo_id",
                "team_contacts",
                "referees.contact",
            ],
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": processed_matches,
                "detailed_changes": detailed_changes,
                "metadata": {
                    "total_matches": len(processed_matches),
                    "has_changes": bool(changes_summary),
                    "change_summary": (
                        changes_summary.get("summary", {})
                        if changes_summary and hasattr(changes_summary, "get")
                        else {}
                    ),
                    "processing_timestamp": datetime.utcnow().isoformat() + "Z",
                    **(metadata or {}),
                },
            },
        }

        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def format_match_updates_v1_legacy(
        matches: List[Dict], changes_summary: Optional[Dict] = None, metadata: Optional[Dict] = None
    ) -> str:
        """
        Legacy v1.0 formatter for backward compatibility.
        Maintains simplified schema for existing subscribers.
        """
        simplified_matches = []
        for match in matches:
            simplified_match = {
                "match_id": match.get("matchid"),
                "teams": f"{match.get('lag1namn', 'N/A')} vs {match.get('lag2namn', 'N/A')}",
                "date": match.get("speldatum"),
                "time": match.get("avsparkstid"),
                "venue": match.get("anlaggningnamn"),
                "referees": [ref.get("namn") for ref in match.get("domaruppdraglista", [])],
            }
            simplified_matches.append(simplified_match)

        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "match-list-processor",
            "version": "1.0",
            "type": "match_updates",
            "payload": {
                "matches": simplified_matches,
                "metadata": {
                    "total_matches": len(simplified_matches),
                    "has_changes": bool(changes_summary),
                    "processing_timestamp": datetime.utcnow().isoformat() + "Z",
                    **(metadata or {}),
                },
            },
        }

        return json.dumps(message, ensure_ascii=False)


class ProcessingStatusMessageFormatter:
    """Formats processing status messages for Redis publishing."""

    @staticmethod
    def format_processing_status(status: str, details: Optional[Dict] = None) -> str:
        """
        Format processing status message for Redis publishing.

        Args:
            status: Processing status (started, completed, failed)
            details: Additional processing details

        Returns:
            str: JSON formatted message
        """
        message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "match-list-processor",
            "version": "1.0",
            "type": "processing_status",
            "payload": {
                "status": status,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "details": details or {},
            },
        }

        return json.dumps(message, ensure_ascii=False)

    @staticmethod
    def format_system_alert(
        alert_type: str, message: str, severity: str = "info", details: Optional[Dict] = None
    ) -> str:
        """
        Format system alert message for Redis publishing.

        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Alert severity (info, warning, error)
            details: Additional alert details

        Returns:
            str: JSON formatted message
        """
        alert_message = {
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "match-list-processor",
            "version": "1.0",
            "type": "system_alert",
            "payload": {
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "details": details or {},
            },
        }

        return json.dumps(alert_message, ensure_ascii=False)
