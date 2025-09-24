#!/usr/bin/env python3
"""
Message Formatter for Redis Integration

Provides message formatting utilities for Redis pub/sub integration.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List


class MatchUpdateMessageFormatter:
    """Formats match update messages for Redis publishing."""

    @staticmethod
    def format_match_updates(matches: List[Dict], changes: Dict, metadata: Dict = None) -> str:
        """
        Format match updates message for Redis publishing.

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


class ProcessingStatusMessageFormatter:
    """Formats processing status messages for Redis publishing."""

    @staticmethod
    def format_processing_status(status: str, details: Dict = None) -> str:
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
        alert_type: str, message: str, severity: str = "info", details: Dict = None
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
