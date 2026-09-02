"""
Logging configuration for the API Test Analysis POC.
"""

import logging
import logging.handlers
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure logging
logger = logging.getLogger('api_analysis')
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
console_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.handlers.RotatingFileHandler(
    logs_dir / LOG_FILE,
    maxBytes=10485760,  # 10MB
    backupCount=5
)
file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
file_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f'api_analysis.{name}')
