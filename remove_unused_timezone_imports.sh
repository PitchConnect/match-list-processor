#\!/bin/bash

# Files with unused timezone imports
files=(
    "./src/core/logging_config.py"
    "./src/notifications/analysis/analyzers/time_analyzer.py"
    "./src/notifications/analysis/base_analyzer.py"
    "./src/notifications/analysis/models/analysis_models.py"
    "./src/notifications/analysis/semantic_analyzer.py"
    "./src/notifications/analytics/metrics_models.py"
    "./src/notifications/monitoring/models.py"
    "./tests/integration/test_semantic_notification_integration.py"
    "./tests/unit/test_backward_compatibility.py"
    "./tests/unit/test_milestone_1_coverage_boost.py"
    "./tests/unit/test_milestone_1_semantic_analysis.py"
    "./tests/unit/test_semantic_to_legacy_adapter.py"
)

for file in "${files[@]}"; do
    echo "Removing unused timezone import from $file..."

    # Remove timezone from datetime imports if it's not used
    sed -i '' 's/from datetime import timezone//' "$file"
    sed -i '' 's/, timezone//' "$file"
done

echo "Done\!"
