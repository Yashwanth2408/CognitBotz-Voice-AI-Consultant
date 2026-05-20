"""
utils/logger.py
---------------
Structured, rotating application logger for the Voice AI Consultant.

Design rationale:
  - Rotating file handler prevents log files from growing unbounded in production.
  - Structured format includes timestamp, level, module, and message.
  - Single logger instance shared across all modules via get_logger().
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config.settings import (
    LOG_LEVEL,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOGS_DIR,
)

# Ensure the logs directory exists before creating file handlers
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Log format: ISO timestamp | level | module name | message
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Module-level flag prevents duplicate handler registration if imported multiple times
_configured: bool = False


def _configure_root_logger() -> None:
    """Configure root logger once. Subsequent calls are no-ops."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler — outputs INFO+ to stdout for developer visibility
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Rotating file handler — captures all levels to persistent log file
    file_handler = RotatingFileHandler(
        filename=LOGS_DIR / "voice_agent.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.DEBUG))
    file_handler.setFormatter(formatter)

    # Error-specific log — separate file for rapid error triage
    error_handler = RotatingFileHandler(
        filename=LOGS_DIR / "errors.log",
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root.addHandler(error_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger for a module.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Component initialised")

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        Configured Logger instance.
    """
    _configure_root_logger()
    return logging.getLogger(name)
