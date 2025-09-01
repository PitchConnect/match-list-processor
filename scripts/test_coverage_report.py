#!/usr/bin/env python3
"""
Comprehensive test coverage analysis and reporting script.

This script provides detailed analysis of test coverage, identifies gaps,
and generates comprehensive reports for the unified match processor service.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class TestCoverageAnalyzer:
    """Analyze and report on test coverage."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.coverage_threshold = 90.0
        self.critical_modules = [
            "src/core/unified_processor.py",
            "src/core/change_categorization.py",
            "src/core/change_detector.py",
            "src/app_unified.py",
        ]

    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite and collect coverage data."""
        print("🧪 Running comprehensive test suite...")

        # Run tests with coverage
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=json:coverage.json",
            "--cov-branch",
            "--tb=short",
            "--durations=10",
            "-v",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Test execution timed out after 10 minutes",
                "returncode": -1,
            }

    def analyze_coverage_json(self) -> Dict[str, Any]:
        """Analyze coverage data from JSON report."""
        coverage_file = self.project_root / "coverage.json"

        if not coverage_file.exists():
            return {"error": "Coverage JSON file not found"}

        try:
            with open(coverage_file, "r") as f:
                coverage_data = json.load(f)

            # Extract summary data
            summary = coverage_data.get("totals", {})
            files = coverage_data.get("files", {})

            # Analyze per-file coverage
            file_analysis = {}
            for file_path, file_data in files.items():
                file_analysis[file_path] = {
                    "coverage_percent": file_data.get("summary", {}).get("percent_covered", 0),
                    "lines_covered": file_data.get("summary", {}).get("covered_lines", 0),
                    "lines_total": file_data.get("summary", {}).get("num_statements", 0),
                    "missing_lines": file_data.get("missing_lines", []),
                    "excluded_lines": file_data.get("excluded_lines", []),
                }

            return {
                "overall_coverage": summary.get("percent_covered", 0),
                "lines_covered": summary.get("covered_lines", 0),
                "lines_total": summary.get("num_statements", 0),
                "branches_covered": summary.get("covered_branches", 0),
                "branches_total": summary.get("num_branches", 0),
                "files": file_analysis,
            }
        except Exception as e:
            return {"error": f"Failed to analyze coverage JSON: {str(e)}"}

    def identify_coverage_gaps(self, coverage_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify coverage gaps and prioritize them."""
        gaps = []

        if "files" not in coverage_data:
            return gaps

        for file_path, file_data in coverage_data["files"].items():
            coverage_percent = file_data.get("coverage_percent", 0)
            missing_lines = file_data.get("missing_lines", [])

            # Identify critical gaps
            is_critical = any(critical in file_path for critical in self.critical_modules)

            if coverage_percent < self.coverage_threshold:
                gap = {
                    "file": file_path,
                    "coverage_percent": coverage_percent,
                    "missing_lines": missing_lines,
                    "lines_missing": len(missing_lines),
                    "is_critical": is_critical,
                    "priority": (
                        "HIGH" if is_critical else "MEDIUM" if coverage_percent < 80 else "LOW"
                    ),
                }
                gaps.append(gap)

        # Sort by priority and coverage percentage
        gaps.sort(key=lambda x: (x["is_critical"], -x["coverage_percent"]), reverse=True)

        return gaps

    def analyze_test_categories(self) -> Dict[str, Any]:
        """Analyze test categories and distribution."""
        test_files = list(self.project_root.glob("tests/**/*.py"))

        categories = {
            "unit": [],
            "integration": [],
            "performance": [],
            "security": [],
            "api": [],
            "health": [],
            "change_detection": [],
            "comprehensive": [],
        }

        for test_file in test_files:
            if test_file.name.startswith("test_"):
                # Categorize based on file path and name
                file_path = str(test_file.relative_to(self.project_root))

                if "unit" in file_path:
                    categories["unit"].append(file_path)
                elif "integration" in file_path:
                    categories["integration"].append(file_path)
                elif "performance" in file_path:
                    categories["performance"].append(file_path)
                elif "security" in file_path:
                    categories["security"].append(file_path)
                elif "api" in file_path or "health" in file_path:
                    categories["api"].append(file_path)
                elif "change" in file_path:
                    categories["change_detection"].append(file_path)
                elif "comprehensive" in file_path:
                    categories["comprehensive"].append(file_path)

        return {
            "categories": categories,
            "total_test_files": len(test_files),
            "distribution": {cat: len(files) for cat, files in categories.items()},
        }

    def generate_coverage_report(self) -> str:
        """Generate comprehensive coverage report."""
        print("📊 Generating comprehensive coverage report...")

        # Run tests and collect data
        test_results = self.run_comprehensive_tests()
        coverage_data = self.analyze_coverage_json()
        coverage_gaps = self.identify_coverage_gaps(coverage_data)
        test_categories = self.analyze_test_categories()

        # Generate report
        report = []
        report.append("# 🧪 COMPREHENSIVE TEST COVERAGE REPORT")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Test Execution Summary
        report.append("## 🚀 Test Execution Summary")
        report.append("")
        if test_results["success"]:
            report.append("✅ **Test Suite Status:** PASSED")
        else:
            report.append("❌ **Test Suite Status:** FAILED")
            report.append(f"**Error:** {test_results['stderr']}")
        report.append("")

        # Coverage Summary
        report.append("## 📊 Coverage Summary")
        report.append("")
        if "error" not in coverage_data:
            overall_coverage = coverage_data.get("overall_coverage", 0)
            status_emoji = "✅" if overall_coverage >= self.coverage_threshold else "⚠️"

            report.append(f"{status_emoji} **Overall Coverage:** {overall_coverage:.1f}%")
            report.append(
                f"📈 **Lines Covered:** {coverage_data.get('lines_covered', 0):,} / {coverage_data.get('lines_total', 0):,}"
            )
            report.append(
                f"🌿 **Branch Coverage:** {coverage_data.get('branches_covered', 0):,} / {coverage_data.get('branches_total', 0):,}"
            )
            report.append(f"🎯 **Target Coverage:** {self.coverage_threshold}%")
        else:
            report.append(f"❌ **Coverage Analysis Failed:** {coverage_data['error']}")
        report.append("")

        # Test Categories
        report.append("## 🏷️ Test Categories")
        report.append("")
        report.append("| Category | Test Files | Description |")
        report.append("|----------|------------|-------------|")

        category_descriptions = {
            "unit": "Unit tests for individual components",
            "integration": "Integration tests for component interaction",
            "performance": "Performance and load tests",
            "security": "Security and vulnerability tests",
            "api": "API endpoint and health check tests",
            "change_detection": "Change detection specific tests",
            "comprehensive": "Comprehensive test suites",
        }

        for category, count in test_categories["distribution"].items():
            description = category_descriptions.get(category, "Other tests")
            report.append(f"| {category.title()} | {count} | {description} |")

        report.append("")
        report.append(f"**Total Test Files:** {test_categories['total_test_files']}")
        report.append("")

        # Coverage Gaps
        if coverage_gaps:
            report.append("## ⚠️ Coverage Gaps")
            report.append("")
            report.append("| File | Coverage | Missing Lines | Priority |")
            report.append("|------|----------|---------------|----------|")

            for gap in coverage_gaps[:10]:  # Top 10 gaps
                file_name = gap["file"].split("/")[-1]
                coverage = f"{gap['coverage_percent']:.1f}%"
                missing = gap["lines_missing"]
                priority = gap["priority"]
                priority_emoji = (
                    "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "🟢"
                )

                report.append(
                    f"| {file_name} | {coverage} | {missing} | {priority_emoji} {priority} |"
                )

            report.append("")

        # Critical Module Analysis
        report.append("## 🎯 Critical Module Coverage")
        report.append("")

        if "files" in coverage_data:
            report.append("| Module | Coverage | Status |")
            report.append("|--------|----------|--------|")

            for critical_module in self.critical_modules:
                module_data = None
                for file_path, file_data in coverage_data["files"].items():
                    if critical_module in file_path:
                        module_data = file_data
                        break

                if module_data:
                    coverage = module_data.get("coverage_percent", 0)
                    status = (
                        "✅ Good" if coverage >= self.coverage_threshold else "⚠️ Needs Improvement"
                    )
                    module_name = critical_module.split("/")[-1]
                    report.append(f"| {module_name} | {coverage:.1f}% | {status} |")
                else:
                    module_name = critical_module.split("/")[-1]
                    report.append(f"| {module_name} | N/A | ❌ Not Found |")

        report.append("")

        # Recommendations
        report.append("## 💡 Recommendations")
        report.append("")

        if coverage_data.get("overall_coverage", 0) >= self.coverage_threshold:
            report.append(
                "✅ **Excellent coverage!** The test suite meets the 90% coverage threshold."
            )
        else:
            report.append("⚠️ **Coverage below threshold.** Consider adding tests for:")

            high_priority_gaps = [gap for gap in coverage_gaps if gap["priority"] == "HIGH"]
            for gap in high_priority_gaps[:5]:
                report.append(f"   - {gap['file']} ({gap['coverage_percent']:.1f}% coverage)")

        report.append("")
        report.append("### 🎯 Next Steps")
        report.append("")
        report.append("1. **Focus on critical modules** with coverage below 90%")
        report.append("2. **Add edge case tests** for complex logic")
        report.append("3. **Improve integration test coverage** for external service interactions")
        report.append("4. **Add performance regression tests** for critical paths")
        report.append("5. **Enhance security test coverage** for input validation")

        report.append("")
        report.append("---")
        report.append("*Report generated by comprehensive test coverage analyzer*")

        return "\n".join(report)

    def save_report(self, report: str, filename: str = "test_coverage_report.md") -> str:
        """Save coverage report to file."""
        report_path = self.project_root / filename

        with open(report_path, "w") as f:
            f.write(report)

        return str(report_path)


def main():
    """Main function to run coverage analysis."""
    project_root = Path(__file__).parent.parent
    analyzer = TestCoverageAnalyzer(str(project_root))

    print("🔍 Starting comprehensive test coverage analysis...")

    # Generate comprehensive report
    report = analyzer.generate_coverage_report()

    # Save report
    report_path = analyzer.save_report(report)

    print(f"📋 Coverage report saved to: {report_path}")
    print("")
    print("📊 Coverage Summary:")

    # Quick summary
    coverage_data = analyzer.analyze_coverage_json()
    if "error" not in coverage_data:
        overall_coverage = coverage_data.get("overall_coverage", 0)
        threshold = analyzer.coverage_threshold

        if overall_coverage >= threshold:
            print(f"✅ Coverage: {overall_coverage:.1f}% (Target: {threshold}%)")
        else:
            print(f"⚠️  Coverage: {overall_coverage:.1f}% (Target: {threshold}%)")
            print(f"   Gap: {threshold - overall_coverage:.1f}% to reach target")
    else:
        print(f"❌ Coverage analysis failed: {coverage_data['error']}")


if __name__ == "__main__":
    main()
