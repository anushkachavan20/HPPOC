"""
Configuration management for the API Test Analysis POC.
Loads settings from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


# ============================================================
# Load environment variables
# ============================================================

env_file = Path(__file__).parent / ".env"

if env_file.exists():
    load_dotenv(env_file)


# ============================================================
# Datadog Configuration
# ============================================================

DATADOG_API_KEY = os.getenv("DATADOG_API_KEY", "")
DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY", "")

DATADOG_SITE = os.getenv(
    "DATADOG_SITE",
    "datadoghq.com"
)

DATADOG_ENVIRONMENT = os.getenv(
    "DATADOG_ENVIRONMENT",
    "poc"
)

DATADOG_BASE_URL = f"https://api.{DATADOG_SITE}"


# ============================================================
# Jira Configuration
# ============================================================

JIRA_API_URL = os.getenv(
    "JIRA_API_URL",
    ""
)

JIRA_EMAIL = os.getenv(
    "JIRA_EMAIL",
    ""
)

JIRA_API_TOKEN = os.getenv(
    "JIRA_API_TOKEN",
    ""
)

JIRA_PROJECT_KEY = os.getenv(
    "JIRA_PROJECT_KEY",
    "PROJ"
)

DATADOG_DASHBOARD_ID = os.getenv(
    "DATADOG_DASHBOARD_ID",
    ""
)


# ============================================================
# Analysis Configuration
# ============================================================

# Number of days of historical Datadog data to analyze
HISTORICAL_LOOKBACK_DAYS = int(
    os.getenv(
        "HISTORICAL_LOOKBACK_DAYS",
        "10"
    )
)

# Failure rate at which a test is considered persistent
# Default = 70%
FAILURE_PERSISTENT_THRESHOLD = float(
    os.getenv(
        "FAILURE_PERSISTENT_THRESHOLD",
        "0.70"
    )
)

# Minimum PASS/FAIL alternations required for flaky classification
FAILURE_FLAKY_MIN_ALTERNATIONS = int(
    os.getenv(
        "FAILURE_FLAKY_MIN_ALTERNATIONS",
        "2"
    )
)

FAILURE_OCCURRENCE_THRESHOLD = int(
    os.getenv(
        "FAILURE_OCCURRENCE_THRESHOLD",
        "6"
    )
)

RESOLUTION_SUCCESS_THRESHOLD = int(
    os.getenv(
        "RESOLUTION_SUCCESS_THRESHOLD",
        "3"
    )
)

SLOW_RESPONSE_THRESHOLD_MS = float(
    os.getenv(
        "SLOW_RESPONSE_THRESHOLD_MS",
        "1000"
    )
)

# Dry-run mode
DRY_RUN = (
    os.getenv(
        "DRY_RUN",
        "False"
    ).lower() == "true"
)


# ============================================================
# Logging Configuration
# ============================================================

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO"
)

LOG_FILE = os.getenv(
    "LOG_FILE",
    "analysis.log"
)


# ============================================================
# Environment Configuration
# ============================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "poc"
)


# ============================================================
# Datadog Tags
# ============================================================

DATADOG_TAGS = [
    f"environment:{ENVIRONMENT}",
    "test_type:k6",
    "analyzer:poc",
]


# ============================================================
# Failure Pattern Classification
# ============================================================

FAILURE_CLASSIFICATIONS = {

    "healthy": {
        "description": (
            "Current test passes with minimal recent failures"
        ),
        "pass_threshold": 0.90,
        "max_failures": 1,
    },

    "new_failure": {
        "description": (
            "Test was previously passing and is now failing"
        ),
        "previous_pass_rate": 1.0,
    },

    "persistent_failure": {
        "description": (
            "Test is repeatedly failing"
        ),
        "failure_threshold": FAILURE_PERSISTENT_THRESHOLD,
    },

    "flaky_failure": {
        "description": (
            "Test alternates between PASS and FAIL"
        ),
        "min_alternations": FAILURE_FLAKY_MIN_ALTERNATIONS,
    },

    "resolved_failure": {
        "description": (
            "Test was previously failing and is now passing"
        ),
        "previous_failures": True,
        "current_status": "PASS",
    },
}


# ============================================================
# AI Failure Categories
# ============================================================
# Kept for future Ollama integration.
# Ollama itself is intentionally disabled for the current POC.

AI_FAILURE_CATEGORIES = [
    "Authentication",
    "Authorization",
    "Validation",
    "Timeout",
    "Network",
    "Server Error",
    "Database",
    "Dependency",
    "Configuration",
    "Unknown",
]


# ============================================================
# Configuration Validation
# ============================================================

if not DATADOG_API_KEY and not DRY_RUN:

    print(
        "WARNING: DATADOG_API_KEY not set. "
        "Datadog ingestion will fail."
    )

    print(
        "Set DATADOG_API_KEY environment variable "
        "or use --dry-run mode."
    )