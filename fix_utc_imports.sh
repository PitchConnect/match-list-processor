#\!/bin/bash

# Files to fix
files=(
    "./src/redis_integration/message_formatter.py"
    "./src/notifications/adapters/semantic_to_legacy_adapter.py"
    "./src/notifications/analysis/models/change_context.py"
    "./src/notifications/monitoring/delivery_monitor.py"
    "./src/notifications/monitoring/health_checker.py"
    "./src/services/api_client.py"
    "./tests/unit/test_milestone_1_delivery_monitoring.py"
    "./tests/unit/test_milestone_1_integration.py"
)

for file in "${files[@]}"; do
    echo "Fixing $file..."

    # Replace UTC import with timezone.utc
    sed -i '' 's/from datetime import datetime, UTC/from datetime import datetime, timezone/' "$file"
    sed -i '' 's/from datetime import datetime, timedelta, UTC/from datetime import datetime, timedelta, timezone/' "$file"

    # Replace datetime.now(UTC) with datetime.now(timezone.utc)
    sed -i '' 's/datetime\.now(UTC)/datetime.now(timezone.utc)/g' "$file"
done

echo "Done\!"
