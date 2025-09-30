#\!/bin/bash

# Find all Python files that have datetime imports and fix them
find ./src ./tests -name "*.py" -exec grep -l "datetime" {} \; | while read file; do
    echo "Processing $file..."

    # Remove any existing UTC imports
    sed -i '' '/from datetime import.*UTC/d' "$file"

    # Fix imports to include timezone
    if grep -q "from datetime import datetime" "$file"; then
        # If it already has datetime import, add timezone to it
        sed -i '' 's/from datetime import datetime$/from datetime import datetime, timezone/' "$file"
        sed -i '' 's/from datetime import datetime, timedelta$/from datetime import datetime, timedelta, timezone/' "$file"
    elif grep -q "import datetime" "$file" && \! grep -q "from datetime import" "$file"; then
        # If it only has "import datetime", add timezone import
        sed -i '' '/import datetime/a\
from datetime import timezone' "$file"
    fi

    # Replace all datetime.utcnow() calls
    sed -i '' 's/datetime\.utcnow()/datetime.now(timezone.utc)/g' "$file"
done

echo "All files processed\!"
