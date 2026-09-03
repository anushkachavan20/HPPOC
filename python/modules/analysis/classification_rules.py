"""
Rules for classifying API test failure patterns.

Classification types:
- Healthy
- New Failure
- Persistent Failure
- Flaky Failure
- Resolved Failure
- Unknown
"""

from config import (
    FAILURE_PERSISTENT_THRESHOLD,
    FAILURE_FLAKY_MIN_ALTERNATIONS,
    FAILURE_OCCURRENCE_THRESHOLD,
    RESOLUTION_SUCCESS_THRESHOLD,
)


class FailureClassifier:
    """
    Classifies the current test result using historical results.
    """

    def __init__(self):
        self.persistent_threshold = FAILURE_PERSISTENT_THRESHOLD
        self.flaky_min_alternations = FAILURE_FLAKY_MIN_ALTERNATIONS

    def classify(
        self,
        current_status,
        historical_data=None,
    ):
        """
        Classify a test based on its current status and history.

        Parameters
        ----------
        current_status : str
            Current test status: PASS or FAIL.

        historical_data : dict, optional
            Historical execution information.

        Returns
        -------
        str
            Failure classification.
        """

        current_status = str(
            current_status or "UNKNOWN"
        ).upper()

        history = self._normalize_history(
            historical_data
        )

        statuses = history["statuses"]
        total = history["total_executions"]
        failed = history["failed"]
        failure_rate = history["failure_rate"]

        # ----------------------------------------------------
        # No historical data
        # ----------------------------------------------------

        if total == 0:

            if current_status == "FAIL":
                return "New Failure"

            if current_status == "PASS":
                return "Healthy"

            return "Unknown"

        # ----------------------------------------------------
        # Current test is passing
        # ----------------------------------------------------

        if current_status == "PASS":
            recent_statuses = ["PASS"] + statuses

            # A resolution requires consecutive successful runs,
            # including the current run, after a previous failure.
            if (
                failed > 0
                and len(recent_statuses) >= RESOLUTION_SUCCESS_THRESHOLD
                and all(
                    status == "PASS"
                    for status in recent_statuses[:RESOLUTION_SUCCESS_THRESHOLD]
                )
            ):
                return "Resolved Failure"

            return "Healthy"

        # ----------------------------------------------------
        # Current test is failing
        # ----------------------------------------------------

        if current_status == "FAIL":

            consecutive_failures = 1
            for status in statuses:
                if status != "FAIL":
                    break
                consecutive_failures += 1

            # ------------------------------------------------
            # Persistent failure
            # ------------------------------------------------
            if consecutive_failures >= FAILURE_OCCURRENCE_THRESHOLD:
                return "Persistent Failure"

            # ------------------------------------------------
            # Flaky failure
            # ------------------------------------------------
            if self._count_alternations(statuses) >= (
                self.flaky_min_alternations
            ):
                return "Flaky Failure"

            # ------------------------------------------------
            # Previously passing -> new failure
            # ------------------------------------------------
            if statuses:

                previous_statuses = [
                    status
                    for status in statuses
                    if status in ("PASS", "FAIL")
                ]

                if previous_statuses and all(
                    status == "PASS"
                    for status in previous_statuses
                ):
                    return "New Failure"

            return "New Failure"

        return "Unknown"

    # ========================================================
    # History normalization
    # ========================================================

    def _normalize_history(self, historical_data):
        """
        Normalize historical analyzer output so the classifier
        can work with different historical-data structures.
        """

        if not historical_data:
            return {
                "total_executions": 0,
                "failed": 0,
                "failure_rate": 0.0,
                "statuses": [],
            }

        total = historical_data.get(
            "total_executions",
            historical_data.get("total", 0),
        )

        failed = historical_data.get(
            "failed",
            historical_data.get("failures", 0),
        )

        failure_rate = historical_data.get(
            "failure_rate"
        )

        statuses = historical_data.get(
            "statuses",
            [],
        )

        # ----------------------------------------------------
        # Convert values safely
        # ----------------------------------------------------

        try:
            total = int(total or 0)
        except (TypeError, ValueError):
            total = 0

        try:
            failed = int(failed or 0)
        except (TypeError, ValueError):
            failed = 0

        # ----------------------------------------------------
        # Calculate failure rate if not provided
        # ----------------------------------------------------

        if failure_rate is None:

            if total > 0:
                failure_rate = failed / total
            else:
                failure_rate = 0.0

        try:
            failure_rate = float(
                failure_rate
            )
        except (TypeError, ValueError):
            failure_rate = 0.0

        # ----------------------------------------------------
        # Normalize statuses
        # ----------------------------------------------------

        if not isinstance(statuses, list):
            statuses = []

        normalized_statuses = []

        for status in statuses:

            if isinstance(status, dict):
                status = status.get(
                    "status",
                    status.get("result", "")
                )

            status = str(
                status or ""
            ).upper()

            if status in ("PASS", "FAIL"):
                normalized_statuses.append(status)

        return {
            "total_executions": total,
            "failed": failed,
            "failure_rate": failure_rate,
            "statuses": normalized_statuses,
        }

    # ========================================================
    # Alternation calculation
    # ========================================================

    def _count_alternations(self, statuses):
        """
        Count PASS -> FAIL or FAIL -> PASS transitions.
        """

        if len(statuses) < 2:
            return 0

        alternations = 0

        for previous, current in zip(
            statuses,
            statuses[1:],
        ):
            if previous != current:
                alternations += 1

        return alternations


# ============================================================
# Backward-compatible function
# ============================================================

def classify_failure_pattern(
    current_status,
    historical_data=None,
):
    """
    Convenience function used by the rest of the POC.
    """

    classifier = FailureClassifier()

    return classifier.classify(
        current_status=current_status,
        historical_data=historical_data,
    )
