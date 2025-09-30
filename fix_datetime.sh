#\!/bin/bash

# Files to fix
files=(
    "./src/notifications/adapters/semantic_to_legacy_adapter.py"
    "./src/notifications/monitoring/delivery_monitor.py"
    "./src/notifications/monitoring/health_checker.py"
    "./src/services/api_client.py"
)

for file in "${files[@]}"; do
    echo "Fixing $file..."

    # Check if file has datetime import and add UTC if needed
    if grep -q "from datetime import datetime" "$file"; then
        if \! grep -q "from datetime import datetime, UTC" "$file"; then
            sed -i '' 's/from datetime import datetime/from datetime import datetime, UTC/' "$file"
        fi
    elif grep -q "import datetime" "$file"; then
        # For files that use "import datetime", we need a different approach
        if \! grep -q "from datetime import UTC" "$file"; then
            sed -i '' '/import datetime/a\
from datetime import UTC' "$file"
        fi
    fi

    # Replace datetime.utcnow() with datetime.now(UTC)
    sed -i '' 's/datetime\.utcnow()/datetime.now(UTC)/g' "$file"
done

echo "Done\!"
