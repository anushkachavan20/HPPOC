"""
Configuration management for the API Test Analysis POC.
Loads settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

# Datadog Configuration
DATADOG_API_KEY = os.getenv('DATADOG_API_KEY', '')
DATADOG_APP_KEY = os.getenv('DATADOG_APP_KEY', '')
DATADOG_SITE = os.getenv('DATADOG_SITE', 'datadoghq.com')
DATADOG_ENVIRONMENT = os.getenv('DATADOG_ENVIRONMENT', 'poc')
DATADOG_BASE_URL = f'https://api.{DATADOG_SITE}'

# Ollama Configuration
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma:7b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '60'))

# Jira Configuration (Real Jira Cloud API)
JIRA_API_URL = os.getenv('JIRA_API_URL', '')  # e.g., https://yourname.atlassian.net
JIRA_EMAIL = os.getenv('JIRA_EMAIL', '')  # Email associated with Jira account
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN', '')  # API token from Jira Settings
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY', 'PROJ')  # Jira project key

# Analysis Configuration
HISTORICAL_LOOKBACK_DAYS = int(os.getenv('HISTORICAL_LOOKBACK_DAYS', '10'))
FAILURE_PERSISTENT_THRESHOLD = float(os.getenv('FAILURE_PERSISTENT_THRESHOLD', '0.70'))
FAILURE_FLAKY_MIN_ALTERNATIONS = int(os.getenv('FAILURE_FLAKY_MIN_ALTERNATIONS', '2'))
DRY_RUN = os.getenv('DRY_RUN', 'False').lower() == 'true'

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'analysis.log')

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'poc')

# Datadog Tags (applied to all events/metrics)
DATADOG_TAGS = [
    f'environment:{ENVIRONMENT}',
    'test_type:k6',
    'analyzer:poc',
]

# Failure Pattern Classification Thresholds
FAILURE_CLASSIFICATIONS = {
    'healthy': {
        'description': 'Current test passes, minimal recent failures',
        'pass_threshold': 0.9,  # >= 90% pass rate
        'max_failures': 1,
    },
    'new_failure': {
        'description': 'Was passing, now failing',
        'previous_pass_rate': 1.0,  # 100% pass in older history
    },
    'persistent_failure': {
        'description': 'Repeatedly failing',
        'failure_threshold': FAILURE_PERSISTENT_THRESHOLD,  # >= 70% failures
    },
    'flaky_failure': {
        'description': 'Alternating PASS/FAIL pattern',
        'min_alternations': FAILURE_FLAKY_MIN_ALTERNATIONS,
    },
    'resolved_failure': {
        'description': 'Was failing, now passing',
        'previous_failures': True,  # Had failures before
        'current_status': 'PASS',
    },
}

# AI Failure Reason Categories
AI_FAILURE_CATEGORIES = [
    'Authentication',
    'Authorization',
    'Validation',
    'Timeout',
    'Network',
    'Server Error',
    'Database',
    'Dependency',
    'Configuration',
    'Unknown',
]

# Validate critical configuration
if not DATADOG_API_KEY and not DRY_RUN:
    print("WARNING: DATADOG_API_KEY not set. Datadog ingestion will fail.")
    print("Set DATADOG_API_KEY environment variable or use --dry-run mode.")
