"""
Logging configuration for the API Test Analysis POC.
"""

import logging
import sys

from config import LOG_LEVEL, LOG_FILE


def setup_logger(name: str = "api_analysis") -> logging.Logger:
    """
    Create and configure the application logger.

    The logger writes to both:
    - Console
    - Log file
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers if setup_logger() is called multiple times
    if logger.handlers:
        return logger

    # Convert configured log level to logging constant
    log_level = getattr(
        logging,
        LOG_LEVEL.upper(),
        logging.INFO
    )

    logger.setLevel(log_level)

    # --------------------------------------------------------
    # Console Handler
    # --------------------------------------------------------

    console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(log_level)

    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler.setFormatter(console_formatter)

    # --------------------------------------------------------
    # File Handler
    # --------------------------------------------------------

    try:
        file_handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8"
        )

        file_handler.setLevel(log_level)

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)

    except OSError as exc:
        # File logging should not prevent the POC from running.
        logger.warning(
            "Unable to create log file '%s': %s",
            LOG_FILE,
            exc
        )

    # Add console handler
    logger.addHandler(console_handler)

    # Prevent messages from being propagated to the root logger
    logger.propagate = False

    return logger


def get_logger(name: str = "api_analysis") -> logging.Logger:
    """
    Return an already configured logger.
    """

    return setup_logger(name)
