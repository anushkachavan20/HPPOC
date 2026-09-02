"""
Failure Pattern Classification Rules - Configurable thresholds for classification.
"""

from dataclasses import dataclass
from typing import List, Tuple
from config import (
    FAILURE_PERSISTENT_THRESHOLD,
    FAILURE_FLAKY_MIN_ALTERNATIONS,
)

# Classification thresholds (all deterministic, configurable)

PERSISTENT_FAILURE_THRESHOLD = FAILURE_PERSISTENT_THRESHOLD
"""Failure rate threshold for persistent failures (default: 70%)"""

FLAKY_MIN_ALTERNATIONS = FAILURE_FLAKY_MIN_ALTERNATIONS
"""Minimum alternations between PASS/FAIL for flaky classification (default: 2)"""

NEW_FAILURE_LOOKBACK = 5
"""Number of previous executions to check for baseline when detecting new failures"""

HEALTHY_THRESHOLD = 0.90
"""Pass rate threshold for healthy classification (default: 90%)"""

RESOLVED_LOOKBACK = 10
"""Recent failure threshold for resolved classification"""


@dataclass
class ClassificationResult:
    """Result of failure pattern classification."""
    pattern: str  # Healthy, New Failure, Persistent, Flaky, Resolved
    failure_percentage: float
    pass_count: int
    fail_count: int
    confidence: float  # 0.0 to 1.0
    reasoning: str


def calculate_failure_percentage(pass_count: int, fail_count: int) -> float:
    """Calculate failure percentage."""
    total = pass_count + fail_count
    if total == 0:
        return 0.0
    return fail_count / total


def count_alternations(statuses: List[str]) -> int:
    """Count alternations between PASS and FAIL in a sequence."""
    if len(statuses) <= 1:
        return 0
    alternations = 0
    for i in range(len(statuses) - 1):
        if statuses[i] != statuses[i + 1]:
            alternations += 1
    return alternations


def classify_failure_pattern(
    current_status: str,
    historical_statuses: List[str],  # Previous executions in reverse chronological order
) -> ClassificationResult:
    """
    Classify failure pattern using deterministic rules.

    Args:
        current_status: Current execution status (PASS or FAIL)
        historical_statuses: List of previous execution statuses (most recent first)

    Returns:
        ClassificationResult with pattern and reasoning
    """

    if not historical_statuses:
        # No history, classify based on current status
        if current_status == 'PASS':
            return ClassificationResult(
                pattern='Healthy',
                failure_percentage=0.0,
                pass_count=1,
                fail_count=0,
                confidence=0.5,
                reasoning='No historical data; current status is PASS'
            )
        else:
            return ClassificationResult(
                pattern='New Failure',
                failure_percentage=1.0,
                pass_count=0,
                fail_count=1,
                confidence=0.5,
                reasoning='No historical data; current status is FAIL'
            )

    # Calculate statistics
    total_historical = len(historical_statuses)
    fail_count = sum(1 for s in historical_statuses if s == 'FAIL')
    pass_count = total_historical - fail_count
    failure_percentage = calculate_failure_percentage(pass_count, fail_count)
    alternations = count_alternations(historical_statuses)

    # Rule 1: Persistent Failure (high failure rate)
    if failure_percentage >= PERSISTENT_FAILURE_THRESHOLD:
        return ClassificationResult(
            pattern='Persistent Failure',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.95,
            reasoning=(
                f"High failure rate: {fail_count}/{total_historical} "
                f"({failure_percentage*100:.1f}%)"
            )
        )

    # Rule 2: Flaky Failure (multiple alternations)
    if alternations >= FLAKY_MIN_ALTERNATIONS:
        return ClassificationResult(
            pattern='Flaky Failure',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.85,
            reasoning=(
                f"Multiple alternations between PASS/FAIL "
                f"({alternations} alternations in {total_historical} executions)"
            )
        )

    # Rule 3: Resolved Failure (was failing, now passing)
    if current_status == 'PASS' and fail_count > 0:
        return ClassificationResult(
            pattern='Resolved Failure',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.90,
            reasoning=(
                f"Previously had failures ({fail_count} in history), "
                f"but current execution passed"
            )
        )

    # Rule 4: New Failure (was passing, now failing)
    if current_status == 'FAIL' and pass_count >= NEW_FAILURE_LOOKBACK:
        # Check if baseline was healthy (mostly passing)
        return ClassificationResult(
            pattern='New Failure',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.90,
            reasoning=(
                f"Most recent executions were passing "
                f"({pass_count} passes, {fail_count} failures), "
                f"but current execution failed"
            )
        )

    # Rule 5: Healthy (currently passing, low failure rate)
    if current_status == 'PASS' and failure_percentage < (1 - HEALTHY_THRESHOLD):
        return ClassificationResult(
            pattern='Healthy',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.95,
            reasoning=(
                f"Low failure rate ({failure_percentage*100:.1f}%), "
                f"current status is PASS"
            )
        )

    # Default: Healthy if mostly passing
    if failure_percentage < (1 - HEALTHY_THRESHOLD):
        return ClassificationResult(
            pattern='Healthy',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.80,
            reasoning=(
                f"Overall pass rate is acceptable "
                f"({pass_count}/{total_historical}, {(1-failure_percentage)*100:.1f}%)"
            )
        )

    # If we get here and current is failing, it's a new failure
    if current_status == 'FAIL':
        return ClassificationResult(
            pattern='New Failure',
            failure_percentage=failure_percentage,
            pass_count=pass_count,
            fail_count=fail_count,
            confidence=0.70,
            reasoning=(
                f"Current execution failed with moderate historical failure rate "
                f"({failure_percentage*100:.1f}%)"
            )
        )

    # Otherwise healthy
    return ClassificationResult(
        pattern='Healthy',
        failure_percentage=failure_percentage,
        pass_count=pass_count,
        fail_count=fail_count,
        confidence=0.70,
        reasoning='Current status is PASS with acceptable historical failure rate'
    )
