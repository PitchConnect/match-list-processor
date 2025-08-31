#!/bin/bash
# Test script to verify CI hanging fixes locally

set -e

echo "🧪 Testing CI Hanging Fixes Locally"
echo "=================================="

# Set test environment
export PYTEST_CURRENT_TEST="local_verification"
export RUN_MODE="oneshot"
export PROCESSOR_MODE="unified"

cd "$(dirname "$0")/.."

echo "📋 Step 1: Running unit tests (should be fast)"
python3 -m pytest tests/test_change_detector.py -v --timeout=10

echo "📋 Step 2: Running unified processor tests (should be fast)"
python3 -m pytest tests/test_unified_processor.py -v --timeout=10

echo "📋 Step 3: Running integration tests with timeout (critical test)"
echo "⏱️  This should complete within 30 seconds or timeout..."
timeout 45s python3 -m pytest tests/test_unified_integration.py::TestUnifiedIntegration::test_unified_app_initialization -v --timeout=30

echo "📋 Step 4: Testing service mode safety"
echo "⏱️  This should complete quickly due to test mode detection..."
timeout 45s python3 -m pytest tests/test_unified_integration.py::TestUnifiedIntegration::test_service_mode_safe_execution -v --timeout=30

echo "📋 Step 5: Running all integration tests with aggressive timeout"
echo "⏱️  This should complete within 2 minutes or timeout..."
timeout 120s python3 -m pytest tests/test_unified_integration.py -v --timeout=30

echo "✅ All tests completed successfully!"
echo "🚀 CI hanging fixes verified - safe to push to GitHub"

echo ""
echo "📊 Test Summary:"
echo "- Unit tests: ✅ Fast execution"
echo "- Unified processor tests: ✅ Fast execution"
echo "- Integration tests: ✅ Timeout protection working"
echo "- Service mode: ✅ Test mode detection working"
echo ""
echo "🎯 Ready for CI/CD pipeline!"
