#!/usr/bin/env python3
"""
Script to automatically fix test files for Issue #84.
Removes FogisPhonebookSyncService mocking and references.
"""

import re
import sys
from pathlib import Path


def fix_test_file(file_path):
    """Fix a single test file by removing phonebook service references."""
    print(f"Processing: {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    original_content = content

    # Remove import of FogisPhonebookSyncService
    content = re.sub(
        r"from src\.services\.phonebook_service import FogisPhonebookSyncService\n", "", content
    )

    # Remove phonebook_service from mock_services dict
    content = re.sub(r'\s*"phonebook_service":\s*Mock\(\),?\n', "", content)

    # Remove FogisPhonebookSyncService patch statements (multi-line)
    content = re.sub(
        r'\s*patch\(\s*["\']src\.(app_persistent|app|app_event_driven|core\.unified_processor)\.FogisPhonebookSyncService["\'],?\s*.*?\),?\n',
        "",
        content,
        flags=re.MULTILINE,
    )

    # Remove phonebook_service attribute assertions
    content = re.sub(r'\s*assert hasattr\(.*?,\s*["\']phonebook_service["\']\)\n', "", content)

    # Remove phonebook_service attribute checks
    content = re.sub(r"\s*assert .*?\.phonebook_service is not None\n", "", content)

    # Remove test methods for phonebook service
    content = re.sub(
        r"    def test_.*?phonebook.*?\(self.*?\):.*?(?=\n    def |\nclass |\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Remove test methods for calendar sync
    content = re.sub(
        r"    def test_.*?calendar_sync.*?\(self.*?\):.*?(?=\n    def |\nclass |\Z)",
        "",
        content,
        flags=re.DOTALL,
    )

    # Fix trailing commas in patch statements
    content = re.sub(r",\s*\),", "),", content)

    # Remove empty lines (more than 2 consecutive)
    content = re.sub(r"\n\n\n+", "\n\n", content)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"  ✅ Updated: {file_path}")
        return True
    else:
        print(f"  ⏭️  No changes: {file_path}")
        return False


def main():
    """Main function to fix all test files."""
    test_files = [
        "tests/test_app.py",
        "tests/test_app_persistent.py",
        "tests/test_event_driven.py",
        "tests/test_health_integration.py",
        "tests/test_health_server.py",
        "tests/test_health_service.py",
        "tests/test_integration.py",
        "tests/test_referee_redis_integration.py",
        "tests/test_unified_integration.py",
        "tests/test_unified_processor.py",
        "tests/integration/test_comprehensive_integration.py",
        "tests/integration/test_event_driven_integration.py",
        "tests/integration/test_semantic_notification_integration.py",
        "tests/integration/test_service_consolidation_e2e.py",
        "tests/performance/test_performance_comprehensive.py",
        "tests/security/test_security_comprehensive.py",
        "tests/unit/test_simple_coverage_90.py",
        "tests/unit/test_unified_processor_comprehensive.py",
        "tests/unit/test_85_percent_threshold.py",
        "tests/unit/test_final_90_percent_breakthrough.py",
        "tests/unit/test_final_90_percent_precision.py",
        "tests/unit/test_final_90_percent_push.py",
        "tests/unit/test_final_90_percent_victory.py",
        "tests/unit/test_focused_coverage_90.py",
        "tests/unit/test_simple_90_percent_push.py",
        "tests/unit/test_strategic_90_percent_final.py",
        "tests/unit/test_ultimate_90_percent_push.py",
        "tests/unit/test_working_coverage_boost.py",
    ]

    updated_count = 0
    for test_file in test_files:
        file_path = Path(test_file)
        if file_path.exists():
            if fix_test_file(file_path):
                updated_count += 1
        else:
            print(f"  ⚠️  Not found: {test_file}")

    print(f"\n✅ Updated {updated_count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
