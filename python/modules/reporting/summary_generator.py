import logging
from collections import Counter
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    Generates a human-readable summary from the aggregated
    API test analysis results.
    """

    def __init__(self):
        logger.info("Summary generator initialized")

    # ------------------------------------------------------------------
    # Main summary method
    # ------------------------------------------------------------------

    def generate(
        self,
        results: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a readable analysis summary.

        Args:
            results:
                Aggregated test results from ResultAggregator.

        Returns:
            Multi-line human-readable summary.
        """

        if not results:
            return "No API test results available."

        total = len(results)

        passed = sum(
            1
            for result in results
            if str(
                result.get("status", "")
            ).upper() == "PASS"
        )

        failed = total - passed

        pass_rate = (
            (passed / total) * 100
            if total > 0
            else 0.0
        )

        fail_rate = (
            (failed / total) * 100
            if total > 0
            else 0.0
        )

        # --------------------------------------------------------------
        # Failure classifications
        # --------------------------------------------------------------

        classification_counts = Counter()

        for result in results:
            classification = self._get_classification(
                result
            )

            if classification:
                classification_counts[
                    classification
                ] += 1

        # --------------------------------------------------------------
        # Affected services
        # --------------------------------------------------------------

        service_failures = Counter()

        for result in results:
            status = str(
                result.get("status", "")
            ).upper()

            if status == "FAIL":
                service = str(
                    result.get(
                        "service",
                        "unknown",
                    )
                ).lower()

                service_failures[service] += 1

        # --------------------------------------------------------------
        # Jira coverage
        # --------------------------------------------------------------

        failed_results = [
            result
            for result in results
            if str(
                result.get("status", "")
            ).upper() == "FAIL"
        ]

        jira_issues = sum(
            1
            for result in failed_results
            if self._has_jira_issue(result)
        )

        jira_without_issue = (
            len(failed_results) - jira_issues
        )

        jira_create = sum(
            1
            for result in failed_results
            if (result.get("jira") or {}).get("jira_action") == "CREATE"
        )

        jira_update = sum(
            1
            for result in failed_results
            if (result.get("jira") or {}).get("jira_action") == "UPDATE"
        )

        # --------------------------------------------------------------
        # Build summary
        # --------------------------------------------------------------

        lines = []

        lines.append(
            "API TEST ANALYSIS SUMMARY"
        )

        lines.append(
            "-" * 50
        )

        # --------------------------------------------------------------
        # Execution statistics
        # --------------------------------------------------------------

        lines.append(
            f"Total Tests Executed: {total}"
        )

        lines.append(
            f"Passed: {passed} ({pass_rate:.1f}%)"
        )

        lines.append(
            f"Failed: {failed} ({fail_rate:.1f}%)"
        )

        # --------------------------------------------------------------
        # Failure breakdown
        # --------------------------------------------------------------

        lines.append("")

        lines.append(
            "Failure Breakdown:"
        )

        if classification_counts:
            for classification, count in sorted(
                classification_counts.items()
            ):
                lines.append(
                    f" - {classification}: {count}"
                )
        else:
            lines.append(
                " - None"
            )

        # --------------------------------------------------------------
        # Affected services
        # --------------------------------------------------------------

        lines.append("")

        lines.append(
            "Affected Services:"
        )

        if service_failures:
            for service, count in sorted(
                service_failures.items()
            ):
                lines.append(
                    f" - {service}: {count} failure"
                    f"{'s' if count != 1 else ''}"
                )
        else:
            lines.append(
                " - None"
            )

        # --------------------------------------------------------------
        # Jira coverage
        # --------------------------------------------------------------

        lines.append("")

        lines.append(
            "Jira Coverage:"
        )

        lines.append(
            f" - Failures with Jira issues: {jira_issues}"
        )

        lines.append(
            f" - Failures without Jira issues: "
            f"{jira_without_issue}"
        )

        lines.append(
            f" - Jira issues to create: {jira_create}"
        )

        lines.append(
            f" - Jira issues to update: {jira_update}"
        )

        # --------------------------------------------------------------
        # Detailed failures
        # --------------------------------------------------------------

        lines.append("")

        lines.append(
            "Failure Details:"
        )

        if not failed_results:
            lines.append(
                " - No failures detected"
            )

        else:
            for result in failed_results:
                lines.extend(
                    self._format_failure(
                        result
                    )
                )

        # --------------------------------------------------------------
        # Overall status
        # --------------------------------------------------------------

        lines.append("")

        lines.append(
            "Overall Status: "
            + (
                "FAILED"
                if failed > 0
                else "PASSED"
            )
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Classification extraction
    # ------------------------------------------------------------------

    def _get_classification(
        self,
        result: Dict[str, Any],
    ) -> str:
        """
        Extract the classification name from an aggregated result.
        """

        classification = result.get(
            "classification"
        )

        if isinstance(classification, dict):
            value = classification.get(
                "pattern"
            )

            if value:
                return str(value)

            value = classification.get(
                "classification"
            )

            if value:
                return str(value)

        elif classification:
            return str(classification)

        return "Unknown"

    # ------------------------------------------------------------------
    # Jira check
    # ------------------------------------------------------------------

    def _has_jira_issue(
        self,
        result: Dict[str, Any],
    ) -> bool:
        """
        Determine whether an aggregated result has a Jira issue.
        """

        jira = result.get(
            "jira"
        )

        if not isinstance(jira, dict):
            return False

        return bool(
            jira.get(
                "has_issue",
                jira.get(
                    "has_jira_issue",
                    False,
                ),
            )
        )

    # ------------------------------------------------------------------
    # Failure formatting
    # ------------------------------------------------------------------

    def _format_failure(
        self,
        result: Dict[str, Any],
    ) -> List[str]:
        """
        Format one failed test for the summary.
        """

        service = result.get(
            "service",
            "unknown",
        )

        test = result.get(
            "test",
            "unknown",
        )

        method = result.get(
            "method",
            "",
        )

        endpoint = result.get(
            "endpoint",
            "",
        )

        http_status = result.get(
            "http_status",
            "",
        )

        duration_ms = result.get(
            "duration_ms",
            0,
        )

        error_message = result.get(
            "error_message",
            "",
        )

        classification = self._get_classification(
            result
        )

        jira = result.get(
            "jira",
            {},
        )

        if not isinstance(jira, dict):
            jira = {}

        issue_key = jira.get(
            "issue_key"
        )

        jira_action = jira.get(
            "jira_action",
            "CREATE",
        )

        jira_recommendation = jira.get(
            "jira_recommendation",
            "",
        )

        lines = []

        lines.append(
            f" - {service}/{test}"
        )

        if method or endpoint:
            lines.append(
                f"   Request: {method} {endpoint}"
            )

        if http_status != "":
            lines.append(
                f"   HTTP Status: {http_status}"
            )

        if duration_ms != "":
            try:
                lines.append(
                    f"   Duration: "
                    f"{float(duration_ms):.2f} ms"
                )
            except (
                TypeError,
                ValueError,
            ):
                lines.append(
                    f"   Duration: {duration_ms}"
                )

        lines.append(
            f"   Classification: {classification}"
        )

        lines.append(
            f"   Jira Action: {jira_action}"
        )

        if jira_recommendation:
            lines.append(
                f"   Jira Recommendation: {jira_recommendation}"
            )

        if error_message:
            lines.append(
                f"   Error: {error_message}"
            )

        if issue_key:
            lines.append(
                f"   Jira Issue: {issue_key}"
            )

        return lines