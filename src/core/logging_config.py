"""
Centralized logging configuration for the Match List Processor.

This module provides standardized logging configuration across all components
with support for structured logging, error context, and monitoring integration.
"""

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ContextualFormatter(logging.Formatter):
    """Custom formatter that adds contextual information to log records."""

    def format(self, record: logging.LogRecord) -> str:
        # Add timestamp if not present
        if not hasattr(record, "timestamp"):
            record.timestamp = datetime.now().isoformat()

        # Add service context
        if not hasattr(record, "service"):
            record.service = "match-list-processor"

        # Add component context based on logger name
        if not hasattr(record, "component"):
            name_parts = record.name.split(".")
            if len(name_parts) >= 2:
                record.component = name_parts[-1]
            else:
                record.component = "core"

        # Add error context for exceptions
        if record.exc_info and not hasattr(record, "error_type"):
            record.error_type = record.exc_info[0].__name__ if record.exc_info[0] else "Unknown"

        return super().format(record)


class SensitiveDataFilter(logging.Filter):
    """Filter to remove or mask sensitive information from log records."""

    SENSITIVE_PATTERNS = [
        "password",
        "token",
        "key",
        "secret",
        "credential",
        "auth",
        "authorization",
        "bearer",
        "api_key",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        # Mask sensitive data in the message
        if hasattr(record, "msg") and isinstance(record.msg, str):
            record.msg = self._mask_sensitive_data(record.msg)

        # Mask sensitive data in arguments
        if hasattr(record, "args") and record.args:
            record.args = tuple(
                self._mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def _mask_sensitive_data(self, text: str) -> str:
        """Mask sensitive data patterns in text."""
        import re

        for pattern in self.SENSITIVE_PATTERNS:
            # Match pattern followed by various separators and values
            regex = rf'({pattern}["\s]*[:=]["\s]*)([^"\s,}}]+)'
            text = re.sub(regex, r"\1********", text, flags=re.IGNORECASE)

        return text


def get_logging_config(
    log_level: str = "INFO",
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = False,
    enable_structured: bool = True,
    log_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate logging configuration dictionary.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string
        log_file: Log file name (if enable_file is True)
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_structured: Enable structured logging with context
        log_dir: Directory for log files

    Returns:
        Logging configuration dictionary
    """
    # Default format strings
    if log_format is None:
        if enable_structured:
            log_format = (
                "%(timestamp)s - %(service)s - %(component)s - %(levelname)s - "
                "%(name)s:%(lineno)d - %(message)s"
            )
        else:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Determine log file path
    if enable_file and log_file:
        if log_dir:
            log_dir_path = Path(log_dir)
            log_dir_path.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir_path / log_file
        else:
            log_file_path = Path(log_file)
    else:
        log_file_path = None

    # Build configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "()": ContextualFormatter if enable_structured else logging.Formatter,
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "()": ContextualFormatter if enable_structured else logging.Formatter,
                "format": (
                    "%(timestamp)s - %(service)s - %(component)s - %(levelname)s - "
                    "%(name)s:%(funcName)s:%(lineno)d - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "filters": {
            "sensitive_data": {
                "()": SensitiveDataFilter,
            }
        },
        "handlers": {},
        "loggers": {
            "": {"level": log_level, "handlers": [], "propagate": False},  # Root logger
            "src": {"level": log_level, "handlers": [], "propagate": False},  # Application logger
            "requests": {  # Reduce requests library verbosity
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
            "urllib3": {  # Reduce urllib3 verbosity
                "level": "WARNING",
                "handlers": [],
                "propagate": True,
            },
        },
    }

    # Add console handler
    if enable_console:
        config["handlers"]["console"] = {  # type: ignore
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "filters": ["sensitive_data"],
            "stream": "ext://sys.stdout",
        }
        config["loggers"][""]["handlers"].append("console")  # type: ignore
        config["loggers"]["src"]["handlers"].append("console")  # type: ignore

    # Add file handler
    if enable_file and log_file_path:
        config["handlers"]["file"] = {  # type: ignore
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filters": ["sensitive_data"],
            "filename": str(log_file_path),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        }
        config["loggers"][""]["handlers"].append("file")  # type: ignore
        config["loggers"]["src"]["handlers"].append("file")  # type: ignore

    return config


def configure_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_console: Optional[bool] = None,
    enable_file: Optional[bool] = None,
    enable_structured: Optional[bool] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Configure logging for the application using environment variables and parameters.

    Environment variables:
        LOG_LEVEL: Logging level (default: INFO)
        LOG_FORMAT: Custom log format string
        LOG_FILE: Log file name
        LOG_DIR: Directory for log files
        LOG_ENABLE_CONSOLE: Enable console logging (default: true)
        LOG_ENABLE_FILE: Enable file logging (default: false)
        LOG_ENABLE_STRUCTURED: Enable structured logging (default: true)

    Args:
        log_level: Override LOG_LEVEL environment variable
        log_format: Override LOG_FORMAT environment variable
        log_file: Override LOG_FILE environment variable
        enable_console: Override LOG_ENABLE_CONSOLE environment variable
        enable_file: Override LOG_ENABLE_FILE environment variable
        enable_structured: Override LOG_ENABLE_STRUCTURED environment variable
        log_dir: Override LOG_DIR environment variable
    """
    # Get configuration from environment variables with defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT")
    log_file = log_file or os.getenv("LOG_FILE", "match-list-processor.log")
    log_dir = log_dir or os.getenv("LOG_DIR", "logs")

    # Parse boolean environment variables
    if enable_console is None:
        enable_console = os.getenv("LOG_ENABLE_CONSOLE", "true").lower() in ("true", "1", "yes")
    if enable_file is None:
        enable_file = os.getenv("LOG_ENABLE_FILE", "false").lower() in ("true", "1", "yes")
    if enable_structured is None:
        enable_structured = os.getenv("LOG_ENABLE_STRUCTURED", "true").lower() in (
            "true",
            "1",
            "yes",
        )

    # Generate and apply configuration
    config = get_logging_config(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        enable_console=enable_console,
        enable_file=enable_file,
        enable_structured=enable_structured,
        log_dir=log_dir,
    )

    logging.config.dictConfig(config)

    # Log configuration success
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, console={enable_console}, "
        f"file={enable_file}, structured={enable_structured}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_error_context(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    operation: Optional[str] = None,
) -> None:
    """
    Log an error with additional context information.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Additional context information
        operation: Description of the operation that failed
    """
    error_info = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "operation": operation or "unknown",
    }

    if context:
        error_info.update(context)

    logger.error(
        f"Operation '{error_info['operation']}' failed: {error_info['error_message']}",
        extra={"error_context": error_info},
        exc_info=True,
    )


# Initialize logging on module import if not already configured
if not logging.getLogger().handlers:
    configure_logging()
