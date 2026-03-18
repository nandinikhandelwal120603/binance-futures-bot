"""
Logging configuration for the Trading Bot.

Sets up dual logging:
- Console output (INFO level) with colored formatting
- File output (DEBUG level) for detailed API request/response logging
"""

import logging
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the application logger.

    Args:
        log_level: Minimum log level for console output (default: INFO).

    Returns:
        Configured logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"trading_bot_{timestamp}.log")

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers on re-initialization
    if logger.handlers:
        logger.handlers.clear()

    # ── File Handler (DEBUG level - captures everything) ──
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # ── Console Handler (configurable level) ──
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    logger.info("Logging initialized → %s", log_file)
    return logger
