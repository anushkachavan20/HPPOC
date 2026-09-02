import logging
from typing import Any, Dict, List

from config import (
    FLAKY_THRESHOLD,
    PERSISTENT_FAILURE_THRESHOLD,
)

logger = logging.getLogger(__name__)


def classify_failure_pattern(
    current_status: str,
    historical_data: Any = None,
) -> Dict[str, Any]:
    """
    Classify the current API test result based on its current
    status and historical execution pattern.

    Classification priority:

    1. Persistent Failure
    2. Flaky
    3. Resolved Failure
    4. New Failure
    5. Healthy
    6. Unknown
    """

    current_status = str(
        current_status or "UNKNOWN"
    ).upper()

    history = _normalize_history(
        historical_data
    )

    statuses = history["statuses"]
    total_executions = history["total_executions"]
    passed = history["passed"]
    failed = history["failed"]
    failure_rate = history["failure_rate"]

    logger.debug(
        "Classifying test: current=%s, total=%d, "
        "passed=%d, failed=%d, failure_rate=%.2f",
        current_status,
        total_executions,
        passed,
        failed,
        failure_rate,
    )

    # ---------------------------------------------------------
    # No historical data
    # ---------------------------------------------------------

    if total_executions == 0:
        if current_status == "FAIL":
            return _classification(
                "New Failure",
                "The test is currently failing and there is no "
                "historical execution data available.",
                current_status,
                history,
            )

        if current_status == "PASS":
            return _classification(
                "Healthy",
                "The test is passing and there is no historical "
                "failure pattern.",
                current_status,
                history,
            )

        return _classification(
            "Unknown",
            "The current test status could not be classified.",
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # Persistent failure
    # ---------------------------------------------------------

    if (
        current_status == "FAIL"
        and failure_rate >= PERSISTENT_FAILURE_THRESHOLD
    ):
        return _classification(
            "Persistent Failure",
            (
                "The test has a consistently high historical "
                "failure rate."
            ),
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # Flaky test
    # ---------------------------------------------------------

    if _is_flaky(statuses):
        return _classification(
            "Flaky",
            (
                "The test has repeatedly changed between PASS "
                "and FAIL across historical executions."
            ),
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # Resolved failure
    # ---------------------------------------------------------

    if (
        current_status == "PASS"
        and failed > 0
    ):
        return _classification(
            "Resolved Failure",
            (
                "The test is currently passing after having "
                "failed in previous executions."
            ),
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # New failure
    # ---------------------------------------------------------

    if (
        current_status == "FAIL"
        and passed >= 5
    ):
        return _classification(
            "New Failure",
            (
                "The test is currently failing after a history "
                "dominated by successful executions."
            ),
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # Healthy
    # ---------------------------------------------------------

    if (
        current_status == "PASS"
        and failure_rate < 0.10
    ):
        return _classification(
            "Healthy",
            (
                "The test is passing and has a low historical "
                "failure rate."
            ),
            current_status,
            history,
        )

    # ---------------------------------------------------------
    # Current failure without enough evidence for another type
    # ---------------------------------------------------------

    if current_status == "FAIL":
        return _classification(
            "New Failure",
            (
                "The test is currently failing, but the available "
                "history does not indicate a persistent or flaky "
                "pattern."
            ),
            current_status,
            history,
        )

    if current_status == "PASS":
        return _classification(
            "Healthy",
            (
                "The test is currently passing, but the historical "
                "data does not meet the criteria for another pattern."
            ),
            current_status,
            history,
        )

    return _classification(
        "Unknown",
        "Unable to determine a failure pattern.",
        current_status,
        history,
    )


def _normalize_history(
    historical_data: Any,
) -> Dict[str, Any]:
    """
    Normalize historical data coming from HistoricalAnalyzer.

    Supports both:
      - dictionary-based history
      - simple list of statuses
      - None
    """

    if historical_data is None:
        statuses: List[str] = []

    elif isinstance(historical_data, list):
        statuses = [
            _normalize_status(status)
            for status in historical_data
        ]

    elif isinstance(historical_data, dict):
        raw_statuses = historical_data.get(
            "statuses",
            [],
        )

        if isinstance(raw_statuses, list):
            statuses = [
                _normalize_status(status)
                for status in raw_statuses
            ]
        else:
            statuses = []

    else:
        statuses = []

    statuses = [
        status
        for status in statuses
        if status in {"PASS", "FAIL"}
    ]

    total_executions = len(statuses)
    passed = statuses.count("PASS")
    failed = statuses.count("FAIL")

    if total_executions > 0:
        failure_rate = failed / total_executions
        pass_rate = passed / total_executions
    else:
        failure_rate = 0.0
        pass_rate = 0.0

    return {
        "statuses": statuses,
        "total_executions": total_executions,
        "passed": passed,
        "failed": failed,
        "failure_rate": failure_rate,
        "pass_rate": pass_rate,
    }


def _normalize_status(
    status: Any,
) -> str:
    """
    Normalize PASS/FAIL values.
    """

    value = str(
        status or ""
    ).strip().upper()

    if value in {
        "PASS",
        "PASSED",
        "SUCCESS",
        "SUCCEEDED",
        "OK",
    }:
        return "PASS"

    if value in {
        "FAIL",
        "FAILED",
        "ERROR",
        "FAILURE",
    }:
        return "FAIL"

    return value


def _is_flaky(
    statuses: List[str],
) -> bool:
    """
    Determine whether the historical sequence is flaky.

    A test is considered flaky when it has at least
    FLAKY_THRESHOLD status transitions.

    Example:

        PASS -> FAIL -> PASS

    has two transitions and is therefore flaky when
    FLAKY_THRESHOLD is 2.
    """

    if len(statuses) < 2:
        return False

    transitions = 0

    for index in range(1, len(statuses)):
        if statuses[index] != statuses[index - 1]:
            transitions += 1

    return transitions >= FLAKY_THRESHOLD


def _classification(
    name: str,
    reason: str,
    current_status: str,
    history: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a consistent classification response.
    """

    return {
        "classification": name,
        "reason": reason,
        "current_status": current_status,
        "historical_executions": history[
            "total_executions"
        ],
        "historical_passed": history[
            "passed"
        ],
        "historical_failed": history[
            "failed"
        ],
        "historical_failure_rate": history[
            "failure_rate"
        ],
        "historical_pass_rate": history[
            "pass_rate"
        ],
        "statuses": history[
            "statuses"
        ],
    }