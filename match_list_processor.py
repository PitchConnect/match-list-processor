"""
DEPRECATED: This module is kept for backward compatibility.
Please use the new modular structure in the src/ directory.

This file now serves as a wrapper around the new implementation.
"""

import warnings
from src.app import main

# Issue deprecation warning
warnings.warn(
    "match_list_processor.py is deprecated. Use 'python -m src.app' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Main execution - delegate to new implementation
if __name__ == "__main__":
    main()


