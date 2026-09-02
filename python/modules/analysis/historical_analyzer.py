import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HistoricalAnalyzer:
    """
    Analyzes historical API test executions stored in Datadog.

    The analyzer retrieves previous executions for a service/test
    combination and calculates:
    - Historical pass/fail counts
    - Failure rate
    - Pass rate
    - Status trend
    - Whether the current failure has historical context
    """

    def __init__(self, datadog_client):
        self.datadog_client = datadog_client

    # ------------------------------------------------------------------
    # Main historical analysis
    # ------------------------------------------------------------------

    def analyze_test_history(
        self,
        service: str,
        test: str,
        limit: int = 10,
        exclude_execution_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze historical executions for one API test.

        Args:
            service:
                Service name, for example "order".

            test:
                Test name, for example "createorder".

            limit:
                Maximum number of previous executions to retrieve.

        Returns:
            Dictionary containing historical statistics and status trend.
        """

        logger.debug(
            "Analyzing history for service=%s, test=%s",
            service,
            test,
        )

        try:
            events = self.datadog_client.get_previous_executions(
                service=service,
                test=test,
                limit=limit,
                exclude_execution_id=exclude_execution_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to retrieve historical data for "
                "%s/%s: %s",
                service,
                test,
                exc,
            )

            return self._empty_analysis(
                service=service,
                test=test,
            )

        statuses = []

        for event in events:
            status = self._extract_status(event)

            if status:
                statuses.append(status)

        total_executions = len(statuses)

        passed = sum(
            1
            for status in statuses
            if status == "PASS"
        )

        failed = sum(
            1
            for status in statuses
            if status == "FAIL"
        )

        pass_rate = (
            passed / total_executions
            if total_executions > 0
            else 0.0
        )

        failure_rate = (
            failed / total_executions
            if total_executions > 0
            else 0.0
        )

        trend = self._calculate_trend(statuses)

        logger.info(
            "Historical data for %s/%s: "
            "%d executions, %d passed, %d failed",
            service,
            test,
            total_executions,
            passed,
            failed,
        )

        return {
            "service": service.lower(),
            "test": test.lower(),
            "total_executions": total_executions,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "failure_rate": failure_rate,
            "statuses": statuses,
            "trend": trend,
            "has_history": total_executions > 0,
            "events": events,
        }

    # ------------------------------------------------------------------
    # Extract status
    # ------------------------------------------------------------------

    def _extract_status(
        self,
        event: Dict[str, Any],
    ) -> Optional[str]:
        """
        Extract PASS/FAIL status from a Datadog event.

        The ingestion layer stores status as a tag:

            status:pass
            status:fail

        Some existing events may also contain status in metadata,
        so both formats are supported.
        """

        # --------------------------------------------------------------
        # 1. Check metadata
        # --------------------------------------------------------------

        metadata = event.get("metadata")

        if isinstance(metadata, dict):
            status = metadata.get("status")

            if status:
                normalized = str(status).upper()

                if normalized in ("PASS", "FAIL"):
                    return normalized

        # --------------------------------------------------------------
        # 2. Check top-level status
        # --------------------------------------------------------------

        status = event.get("status")

        if status:
            normalized = str(status).upper()

            if normalized in ("PASS", "FAIL"):
                return normalized

        # --------------------------------------------------------------
        # 3. Check tags
        # --------------------------------------------------------------

        tags = event.get("tags", [])

        if isinstance(tags, str):
            tags = tags.split(",")

        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, str):
                    continue

                tag = tag.strip()

                if tag.startswith("status:"):
                    value = tag.split(":", 1)[1].upper()

                    if value in ("PASS", "FAIL"):
                        return value

        # --------------------------------------------------------------
        # 4. Check event title/text
        # --------------------------------------------------------------

        title = str(
            event.get("title", "")
        ).upper()

        text = str(
            event.get("text", "")
        ).upper()

        combined = f"{title} {text}"

        if "API TEST PASS" in combined:
            return "PASS"

        if "API TEST FAIL" in combined:
            return "FAIL"

        return None

    # ------------------------------------------------------------------
    # Calculate trend
    # ------------------------------------------------------------------

    def _calculate_trend(
        self,
        statuses: List[str],
    ) -> str:
        """
        Calculate a simple historical trend.

        Datadog returns the newest events first.

        Examples:

            [PASS, PASS, PASS] -> STABLE_PASS
            [FAIL, FAIL, FAIL] -> STABLE_FAIL
            [PASS, FAIL, PASS] -> FLAKY
            [FAIL, PASS, PASS] -> IMPROVING
            [PASS, PASS, FAIL] -> DEGRADING
        """

        if not statuses:
            return "NO_HISTORY"

        if len(statuses) == 1:
            if statuses[0] == "PASS":
                return "STABLE_PASS"

            return "STABLE_FAIL"

        pass_count = statuses.count("PASS")
        fail_count = statuses.count("FAIL")

        # All executions have the same result.
        if fail_count == 0:
            return "STABLE_PASS"

        if pass_count == 0:
            return "STABLE_FAIL"

        # Count transitions between PASS and FAIL.
        transitions = 0

        for index in range(1, len(statuses)):
            if statuses[index] != statuses[index - 1]:
                transitions += 1

        if transitions >= 2:
            return "FLAKY"

        # Because statuses are newest -> oldest:
        #
        # [FAIL, PASS, PASS]
        #
        # means the newest result failed while older results passed.
        # Therefore the test is degrading.
        if statuses[0] == "FAIL" and statuses[-1] == "PASS":
            return "DEGRADING"

        # [PASS, FAIL, FAIL]
        #
        # means the newest result passed while older results failed.
        # Therefore the test is improving.
        if statuses[0] == "PASS" and statuses[-1] == "FAIL":
            return "IMPROVING"

        return "MIXED"

    # ------------------------------------------------------------------
    # Empty analysis
    # ------------------------------------------------------------------

    def _empty_analysis(
        self,
        service: str,
        test: str,
    ) -> Dict[str, Any]:
        """
        Return a consistent empty historical-analysis structure
        when Datadog history is unavailable.
        """

        return {
            "service": service.lower(),
            "test": test.lower(),
            "total_executions": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "failure_rate": 0.0,
            "statuses": [],
            "trend": "NO_HISTORY",
            "has_history": False,
            "events": [],
        }