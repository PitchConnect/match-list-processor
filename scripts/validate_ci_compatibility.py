#!/usr/bin/env python3
"""
CI/CD Compatibility Validation Script

This script validates that code changes will pass CI/CD checks across different Python versions.
Run this before committing to catch issues early.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔍 {description}")
    print(f"Running: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent.parent
        )

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False

    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def main():
    """Run comprehensive CI/CD compatibility checks."""
    print("🚀 CI/CD Compatibility Validation")
    print("=" * 50)

    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)

    checks = [
        # Code quality checks (same as CI/CD)
        ("python3 -m black --check src/ tests/", "Black code formatting check"),
        ("python3 -m isort --check-only src/ tests/", "Import sorting check"),
        ("python3 -m flake8 src/ tests/", "Flake8 linting check"),
        ("python3 -m mypy src/", "MyPy type checking"),
        ("python3 -m bandit -r src/", "Bandit security check"),
        # Test coverage validation (CRITICAL - matches CI/CD requirement)
        (
            "python3 -m pytest --cov=src --cov-fail-under=84 --cov-report=term-missing -q",
            "Test coverage validation (84% required)",
        ),
        # Test execution
        ("python3 -m pytest tests/redis_integration/ -v", "Redis integration tests"),
        # Import validation
        (
            'python3 -c \'import sys; sys.path.insert(0, "src"); import redis_integration; print("✅ Redis integration imports successfully")\'',
            "Import validation",
        ),
        # Redis type compatibility check
        (
            'python3 -c \'import redis; print(f"Redis version: {redis.__version__}"); print("✅ Redis client compatible")\'',
            "Redis compatibility check",
        ),
    ]

    failed_checks = []

    for cmd, description in checks:
        if not run_command(cmd, description):
            failed_checks.append(description)

    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)

    if failed_checks:
        print(f"❌ {len(failed_checks)} checks FAILED:")
        for check in failed_checks:
            print(f"   - {check}")
        print("\n🚨 DO NOT COMMIT - Fix issues above first!")
        sys.exit(1)
    else:
        print("✅ ALL CHECKS PASSED!")
        print("🎉 Ready for commit and CI/CD pipeline!")
        sys.exit(0)


if __name__ == "__main__":
    main()
