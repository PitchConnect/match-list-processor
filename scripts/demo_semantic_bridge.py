#!/usr/bin/env python3
"""
Demonstration script for the Semantic Analysis Bridge (Issue #52).

This script demonstrates how the SemanticToLegacyAdapter converts rich semantic
analysis to legacy categorized changes format, enabling the match-list-processor
to fully replace the match-list-change-detector service.
"""

import json
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# flake8: noqa: E402
from notifications.adapters.semantic_to_legacy_adapter import SemanticToLegacyAdapter
from notifications.analysis.semantic_analyzer import SemanticChangeAnalyzer


def create_sample_match_data():
    """Create sample match data for demonstration."""
    prev_match = {
        "matchid": "12345",
        "hemmalag": "Team A",
        "bortalag": "Team B",
        "speldatum": "2024-01-15",
        "tid": "15:00",
        "anlaggningnamn": "Stadium A",
        "domaruppdraglista": [{"id": "ref1", "namn": "John Doe", "roll": "Huvuddomare"}],
        "status": "Bekräftad",
    }

    curr_match = {
        "matchid": "12345",
        "hemmalag": "Team A",
        "bortalag": "Team B",
        "speldatum": "2024-01-15",
        "tid": "16:00",  # Time changed
        "anlaggningnamn": "Stadium B",  # Venue changed
        "domaruppdraglista": [
            {"id": "ref1", "namn": "John Doe", "roll": "Huvuddomare"},
            {"id": "ref2", "namn": "Jane Smith", "roll": "Assisterande domare"},  # New referee
        ],
        "status": "Bekräftad",
    }

    return prev_match, curr_match


def demonstrate_semantic_analysis():
    """Demonstrate semantic analysis capabilities."""
    print("🧠 SEMANTIC ANALYSIS DEMONSTRATION")
    print("=" * 50)

    # Create sample data
    prev_match, curr_match = create_sample_match_data()

    print("📊 Sample Match Changes:")
    print(f"  • Time: {prev_match['tid']} → {curr_match['tid']}")
    print(f"  • Venue: {prev_match['anlaggningnamn']} → {curr_match['anlaggningnamn']}")
    print(
        f"  • Referees: {len(prev_match['domaruppdraglista'])} → {len(curr_match['domaruppdraglista'])}"
    )
    print()

    # Perform semantic analysis
    analyzer = SemanticChangeAnalyzer()
    semantic_analysis = analyzer.analyze_match_changes(prev_match, curr_match)

    print("🔍 Semantic Analysis Results:")
    print(f"  • Match ID: {semantic_analysis.match_id}")
    print(f"  • Change Category: {semantic_analysis.change_category}")
    print(f"  • Overall Impact: {semantic_analysis.overall_impact.value}")
    print(f"  • Overall Urgency: {semantic_analysis.overall_urgency.value}")
    print(f"  • Field Changes: {len(semantic_analysis.field_changes)}")
    print(f"  • Change Summary: {semantic_analysis.change_summary}")
    print()

    # Show detailed field changes
    print("📋 Detailed Field Changes:")
    for i, change in enumerate(semantic_analysis.field_changes, 1):
        print(f"  {i}. {change.field_display_name}")
        print(f"     • Path: {change.field_path}")
        print(f"     • Type: {change.change_type}")
        print(f"     • Impact: {change.business_impact.value}")
        print(f"     • Urgency: {change.urgency.value}")
        print(f"     • Description: {change.user_friendly_description}")
        print(f"     • Stakeholders: {', '.join(change.affected_stakeholders)}")
        print()

    # Show stakeholder impact map
    print("👥 Stakeholder Impact Map:")
    for stakeholder, messages in semantic_analysis.stakeholder_impact_map.items():
        print(f"  • {stakeholder.title()}:")
        for message in messages:
            print(f"    - {message}")
    print()

    # Show recommended actions
    print("💡 Recommended Actions:")
    for action in semantic_analysis.recommended_actions:
        print(f"  • {action}")
    print()

    return semantic_analysis


def demonstrate_bridge_conversion(semantic_analysis):
    """Demonstrate the semantic to legacy bridge conversion."""
    print("🌉 SEMANTIC TO LEGACY BRIDGE DEMONSTRATION")
    print("=" * 50)

    # Create adapter
    adapter = SemanticToLegacyAdapter()

    print("🔄 Converting semantic analysis to legacy format...")

    # Convert to legacy format
    categorized_changes = adapter.convert_semantic_to_categorized(semantic_analysis)

    print("✅ Conversion Complete!")
    print()

    print("📊 Legacy Format Results:")
    print(f"  • Total Changes: {categorized_changes.total_changes}")
    print(f"  • Critical Changes: {categorized_changes.critical_changes}")
    print(f"  • High Priority Changes: {categorized_changes.high_priority_changes}")
    print(f"  • Change Categories: {len(categorized_changes.change_categories)}")
    print(f"  • Affected Stakeholders: {len(categorized_changes.affected_stakeholder_types)}")
    print()

    # Show individual changes
    print("📋 Legacy Change Details:")
    for i, change in enumerate(categorized_changes.changes, 1):
        print(f"  {i}. {change.field_name}")
        print(f"     • Category: {change.category.value}")
        print(f"     • Priority: {change.priority.value}")
        print(f"     • Previous: {change.previous_value}")
        print(f"     • Current: {change.current_value}")
        print(f"     • Description: {change.change_description}")
        print(f"     • Stakeholders: {[s.value for s in change.affected_stakeholders]}")
        print(f"     • Timestamp: {change.timestamp}")
        print()

    # Show change categories
    print("🏷️ Change Categories:")
    for category in categorized_changes.change_categories:
        print(f"  • {category.value}")
    print()

    # Show stakeholder types
    print("👥 Affected Stakeholder Types:")
    for stakeholder_type in categorized_changes.affected_stakeholder_types:
        print(f"  • {stakeholder_type.value}")
    print()

    return categorized_changes


def demonstrate_backward_compatibility(categorized_changes):
    """Demonstrate backward compatibility with existing notification infrastructure."""
    print("🔄 BACKWARD COMPATIBILITY DEMONSTRATION")
    print("=" * 50)

    print("✅ Legacy Format Compliance Checks:")

    # Check required fields
    required_fields = [
        "changes",
        "total_changes",
        "critical_changes",
        "high_priority_changes",
        "affected_stakeholder_types",
        "change_categories",
    ]

    for field in required_fields:
        has_field = hasattr(categorized_changes, field)
        print(f"  • {field}: {'✅' if has_field else '❌'}")

    print()

    # Check change structure
    print("📋 Change Structure Compliance:")
    if categorized_changes.changes:
        change = categorized_changes.changes[0]
        change_fields = [
            "match_id",
            "category",
            "priority",
            "affected_stakeholders",
            "field_name",
            "previous_value",
            "current_value",
            "change_description",
            "timestamp",
        ]

        for field in change_fields:
            has_field = hasattr(change, field)
            print(f"  • {field}: {'✅' if has_field else '❌'}")

    print()

    # Test serialization
    print("💾 Serialization Compatibility:")
    try:

        # Test basic serialization
        serializable_data = {
            "total_changes": categorized_changes.total_changes,
            "critical_changes": categorized_changes.critical_changes,
            "high_priority_changes": categorized_changes.high_priority_changes,
        }

        json.dumps(serializable_data)  # Test serialization
        print("  • Basic serialization: ✅")

        # Test change serialization
        if categorized_changes.changes:
            change = categorized_changes.changes[0]
            change_data = {
                "match_id": change.match_id,
                "category": change.category.value,
                "priority": change.priority.value,
                "field_name": change.field_name,
                "previous_value": change.previous_value,
                "current_value": change.current_value,
                "timestamp": change.timestamp.isoformat(),
            }

            json.dumps(change_data)  # Test serialization
            print("  • Change serialization: ✅")

    except Exception as e:
        print(f"  • Serialization: ❌ ({e})")

    print()


def demonstrate_benefits():
    """Demonstrate the benefits of the semantic analysis bridge."""
    print("🚀 SEMANTIC ANALYSIS BRIDGE BENEFITS")
    print("=" * 50)

    benefits = [
        "🎯 Service Consolidation: Enables match-list-processor to replace match-list-change-detector",
        "🧠 Enhanced Intelligence: Rich business context in notifications (impact, urgency, stakeholders)",
        "🎨 Better Notifications: Stakeholder-specific targeting and contextual messages",
        "⚡ Smart Prioritization: Intelligent urgency-based priority assignment",
        "🔄 Backward Compatibility: Zero disruption to existing notification infrastructure",
        "🛡️ Fallback Safety: Automatic fallback to legacy detection on errors",
        "⚙️ Configuration Control: Feature flags for gradual rollout",
        "📊 Future-Proof: Easy addition of new semantic analyzers",
        "🔧 Operational Excellence: Unified monitoring and logging",
        "💰 Cost Reduction: Single service architecture reduces operational overhead",
    ]

    for benefit in benefits:
        print(f"  {benefit}")

    print()


def main():
    """Main demonstration function."""
    print("🌉 SEMANTIC ANALYSIS BRIDGE DEMONSTRATION")
    print("Issue #52: Create Semantic Analysis Bridge for Notification Integration")
    print("=" * 70)
    print()

    try:
        # Demonstrate semantic analysis
        semantic_analysis = demonstrate_semantic_analysis()

        # Demonstrate bridge conversion
        categorized_changes = demonstrate_bridge_conversion(semantic_analysis)

        # Demonstrate backward compatibility
        demonstrate_backward_compatibility(categorized_changes)

        # Show benefits
        demonstrate_benefits()

        print("🎉 DEMONSTRATION COMPLETE!")
        print("The Semantic Analysis Bridge successfully converts rich semantic analysis")
        print("to legacy format while preserving business intelligence and maintaining")
        print("backward compatibility with existing notification infrastructure.")
        print()
        print("✅ Ready for service consolidation!")

    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
