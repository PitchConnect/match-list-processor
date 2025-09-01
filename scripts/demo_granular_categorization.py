#!/usr/bin/env python3
"""
Demonstration script for enhanced granular change categorization.

This script showcases the comprehensive change categorization capabilities
implemented for Issue #26, including detection of specific change types,
priority assessment, and stakeholder impact analysis.

Usage:
    python scripts/demo_granular_categorization.py
"""

import os
import sys
from datetime import datetime

# Add project root to path for imports
project_root = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, project_root)

from src.core.change_categorization import (  # noqa: E402
    ChangeCategory,
    ChangePriority,
    StakeholderType,
)
from src.core.change_detector import GranularChangeDetector  # noqa: E402


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print("=" * 60)


def print_changes_summary(changes):
    """Print a comprehensive summary of detected changes."""
    print("📊 CHANGE DETECTION SUMMARY")
    print(f"  - Has changes: {changes.has_changes}")
    print(f"  - Total changes: {changes.total_changes}")
    print(f"  - New matches: {len(changes.new_matches)}")
    print(f"  - Updated matches: {len(changes.updated_matches)}")
    print(f"  - Removed matches: {len(changes.removed_matches)}")

    if hasattr(changes, "categorized_changes") and changes.categorized_changes:
        cat_changes = changes.categorized_changes
        print("\n🎯 GRANULAR CATEGORIZATION")
        print(f"  - Categorized changes: {cat_changes.total_changes}")
        print(f"  - Critical changes: {cat_changes.critical_changes}")
        print(f"  - High priority changes: {cat_changes.high_priority_changes}")
        print(f"  - Change categories: {[c.value for c in cat_changes.change_categories]}")
        print(
            f"  - Affected stakeholders: {[s.value for s in cat_changes.affected_stakeholder_types]}"
        )

        print("\n📋 DETAILED CHANGES:")
        for i, change in enumerate(cat_changes.changes, 1):
            print(f"  {i}. {change.category.value.upper()}")
            print(f"     Description: {change.change_description}")
            print(f"     Priority: {change.priority.value}")
            print(f"     Stakeholders: {[s.value for s in change.affected_stakeholders]}")
            print(f"     Field: {change.field_name}")
            print(f"     Change: {change.previous_value} → {change.current_value}")


def demo_new_assignment_detection():
    """Demonstrate detection of new referee assignments."""
    print_section("NEW ASSIGNMENT DETECTION")

    detector = GranularChangeDetector()

    # Scenario: New match with referee assignments
    current_matches = [
        {
            "matchid": "12345",
            "matchnr": 1,
            "domaruppdraglista": [
                {"personid": 456, "personnamn": "John Referee", "uppdragstyp": "Huvuddomare"},
                {
                    "personid": 789,
                    "personnamn": "Jane Assistant",
                    "uppdragstyp": "Assisterande dommare",
                },
            ],
            "speldatum": "2025-09-01",
            "avsparkstid": "14:00",
            "anlaggningnamn": "Stadium Arena",
            "lag1namn": "Team Alpha",
            "lag2namn": "Team Beta",
            "serienamn": "Premier League",
        }
    ]

    changes = detector.detect_changes(current_matches)
    print_changes_summary(changes)


def demo_multiple_change_types():
    """Demonstrate detection of multiple change types in a single match."""
    print_section("MULTIPLE CHANGE TYPES DETECTION")

    detector = GranularChangeDetector()

    # Save previous match state
    previous_matches = [
        {
            "matchid": "12345",
            "domaruppdraglista": [],
            "speldatum": "2025-09-01",
            "avsparkstid": "14:00",
            "anlaggningnamn": "Old Stadium",
            "lag1namn": "Team Alpha",
            "lag2namn": "Team Beta",
        }
    ]
    detector.save_current_matches(previous_matches)

    # Current match with multiple changes
    current_matches = [
        {
            "matchid": "12345",
            "domaruppdraglista": [
                {"personid": 456, "personnamn": "New Referee", "uppdragstyp": "Huvuddomare"}
            ],
            "speldatum": "2025-09-02",  # Date changed
            "avsparkstid": "16:00",  # Time changed
            "anlaggningnamn": "New Stadium",  # Venue changed
            "lag1namn": "Team Alpha United",  # Team name changed
            "lag2namn": "Team Beta FC",  # Team name changed
        }
    ]

    changes = detector.detect_changes(current_matches)
    print_changes_summary(changes)


def demo_same_day_priority_assessment():
    """Demonstrate same-day priority assessment."""
    print_section("SAME-DAY PRIORITY ASSESSMENT")

    detector = GranularChangeDetector()

    # Get today's date for same-day scenario
    today = datetime.now().strftime("%Y-%m-%d")

    # Save previous match state
    previous_matches = [
        {"matchid": "12345", "domaruppdraglista": [], "speldatum": today, "avsparkstid": "14:00"}
    ]
    detector.save_current_matches(previous_matches)

    # Current match with same-day changes (should be CRITICAL priority)
    current_matches = [
        {
            "matchid": "12345",
            "domaruppdraglista": [
                {"personid": 456, "personnamn": "Emergency Referee", "uppdragstyp": "Huvuddomare"}
            ],
            "speldatum": today,
            "avsparkstid": "16:00",  # Time changed on same day
        }
    ]

    changes = detector.detect_changes(current_matches)
    print_changes_summary(changes)

    print("\n⚠️  SAME-DAY CHANGE ANALYSIS:")
    print(f"  - Match date: {today} (today)")
    print("  - All changes automatically elevated to CRITICAL priority")
    print("  - Immediate notification required for all stakeholders")


def demo_stakeholder_impact_analysis():
    """Demonstrate stakeholder impact analysis."""
    print_section("STAKEHOLDER IMPACT ANALYSIS")

    detector = GranularChangeDetector()

    # Save previous match state
    previous_matches = [
        {
            "matchid": "12345",
            "domaruppdraglista": [{"personid": 123, "personnamn": "Old Referee"}],
            "speldatum": "2025-09-01",
            "avsparkstid": "14:00",
            "anlaggningnamn": "Stadium A",
            "lag1namn": "Team A",
            "lag2namn": "Team B",
        }
    ]
    detector.save_current_matches(previous_matches)

    # Current match with changes affecting different stakeholder groups
    current_matches = [
        {
            "matchid": "12345",
            "domaruppdraglista": [
                {"personid": 456, "personnamn": "New Referee"}
            ],  # Affects REFEREES
            "speldatum": "2025-09-02",  # Affects ALL
            "avsparkstid": "16:00",  # Affects ALL
            "anlaggningnamn": "Stadium B",  # Affects ALL
            "lag1namn": "Team A United",  # Affects TEAMS
            "lag2namn": "Team B FC",  # Affects TEAMS
        }
    ]

    changes = detector.detect_changes(current_matches)
    print_changes_summary(changes)

    print("\n👥 STAKEHOLDER IMPACT BREAKDOWN:")
    if hasattr(changes, "categorized_changes") and changes.categorized_changes:
        stakeholder_changes = {}
        for change in changes.categorized_changes.changes:
            for stakeholder in change.affected_stakeholders:
                if stakeholder not in stakeholder_changes:
                    stakeholder_changes[stakeholder] = []
                stakeholder_changes[stakeholder].append(change.category.value)

        for stakeholder, change_types in stakeholder_changes.items():
            print(f"  - {stakeholder.value.upper()}: {', '.join(set(change_types))}")


def demo_change_category_coverage():
    """Demonstrate coverage of all change categories."""
    print_section("CHANGE CATEGORY COVERAGE")

    print("📋 SUPPORTED CHANGE CATEGORIES:")
    for category in ChangeCategory:
        print(f"  - {category.value.upper()}: {category.name}")

    print("\n🎯 PRIORITY LEVELS:")
    for priority in ChangePriority:
        print(f"  - {priority.value.upper()}: {priority.name}")

    print("\n👥 STAKEHOLDER TYPES:")
    for stakeholder in StakeholderType:
        print(f"  - {stakeholder.value.upper()}: {stakeholder.name}")


def main():
    """Run all demonstrations."""
    print("🚀 GRANULAR CHANGE CATEGORIZATION DEMONSTRATION")
    print("Issue #26 - Enhanced Change Detection and Categorization")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Run all demonstrations
        demo_change_category_coverage()
        demo_new_assignment_detection()
        demo_multiple_change_types()
        demo_same_day_priority_assessment()
        demo_stakeholder_impact_analysis()

        print_section("DEMONSTRATION COMPLETE")
        print("✅ All granular change categorization features demonstrated successfully!")
        print("\n🎯 KEY CAPABILITIES SHOWCASED:")
        print("  - Comprehensive change category detection")
        print("  - Priority assessment with same-day escalation")
        print("  - Stakeholder impact analysis")
        print("  - Field-level change tracking")
        print("  - Integration with unified processor")

        print("\n📈 READY FOR PHASE 2:")
        print("  - Notification system can leverage detailed change information")
        print("  - Stakeholder targeting based on change impact")
        print("  - Priority-based notification delivery")
        print("  - Comprehensive change audit trail")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
