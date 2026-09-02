"""
Logging configuration for the API Test Analysis POC.
"""

import logging
import sys

from config import LOG_LEVEL, LOG_FILE


def setup_logger(
    name="api_analysis",
    log_level=None,
    log_file=None,
):
    """
    Create and configure the application logger.

    Parameters
    ----------
    name : str
        Logger name.

    log_level : str, optional
        Logging level such as DEBUG, INFO, WARNING, ERROR.

    log_file : str, optional
        Path to the log file.

    Returns
    -------
    logging.Logger
        Configured logger.
    """

    # Use configuration defaults when values aren't explicitly provided
    if log_level is None:
        log_level = LOG_LEVEL

    if log_file is None:
        log_file = LOG_FILE

    logger = logging.getLogger(name)

    # Convert configured level to logging constant
    numeric_level = getattr(
        logging,
        str(log_level).upper(),
        logging.INFO,
    )

    logger.setLevel(numeric_level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # ========================================================
    # Console Handler
    # ========================================================

    console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setLevel(numeric_level)

    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler.setFormatter(console_formatter)

    logger.addHandler(console_handler)

    # ========================================================
    # File Handler
    # ========================================================

    if log_file:

        try:
            file_handler = logging.FileHandler(
                log_file,
                encoding="utf-8",
            )

            file_handler.setLevel(numeric_level)

            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

            file_handler.setFormatter(file_formatter)

            logger.addHandler(file_handler)

        except OSError as exc:

            logger.warning(
                "Unable to create log file '%s': %s",
                log_file,
                exc,
            )

    # Prevent duplicate messages through the root logger
    logger.propagate = False

    return logger


def get_logger(name="api_analysis"):
    """
    Return a configured logger.
    """

    return setup_logger(name=name)
