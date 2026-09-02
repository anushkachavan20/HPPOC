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

        return self._generate_clean_report(results)

    def _generate_clean_report(
        self,
        results: List[Dict[str, Any]],
    ) -> str:
        """Generate the compact tables intended for users and artifacts."""
        services = {}
        failed_results = []
        jira_results = []

        for result in results:
            service = str(result.get("service", "unknown")).lower()
            status = str(result.get("status", "UNKNOWN")).upper()
            services.setdefault(service, {"PASS": 0, "FAIL": 0})[status] = (
                services.setdefault(service, {"PASS": 0, "FAIL": 0}).get(status, 0) + 1
            )

            classification = self._get_classification(result)

            if status == "FAIL":
                failed_results.append(result)
                jira_results.append(result)
            elif (
                classification == "Resolved Failure"
                and (result.get("jira") or {}).get("jira_action") == "RESOLVE"
            ):
                jira_results.append(result)

        total_services = len(services)
        passed_services = sum(
            1
            for counts in services.values()
            if counts.get("FAIL", 0) == 0
        )
        failed_services = total_services - passed_services

        lines = [
            "# API Automation Health Report",
            "",
            "## Overall Service Summary",
            "| Measure | Count |",
            "|---|---:|",
            f"| Total services | {total_services} |",
            f"| Passing services | {passed_services} |",
            f"| Failing services | {failed_services} |",
            "",
            "## Service Results",
            "| Service | Total APIs | Passed | Failed | Result |",
            "|---|---:|---:|---:|---|",
        ]
        for service, counts in sorted(services.items()):
            service_status = "FAIL" if counts.get("FAIL", 0) else "PASS"
            total_apis = counts.get("PASS", 0) + counts.get("FAIL", 0)
            lines.append(f"| {service} | {total_apis} | {counts.get('PASS', 0)} | {counts.get('FAIL', 0)} | {service_status} |")

        lines.extend([
            "",
            "## Failed API Results",
            "| Service | API path | Failure type |",
            "|---|---|---|",
        ])
        if failed_results:
            for result in failed_results:
                api_path = f"{result.get('method', '')} {result.get('endpoint', '')}"
                lines.append(f"| {result.get('service', '')} | {api_path} | {self._get_classification(result)} |")
        else:
            lines.append("| None |  |  |")

        lines.extend([
            "",
            "## Jira Actions",
            "Only failed APIs and APIs eligible for resolution are shown.",
            "| Service | API | Action | Existing Jira | Recommendation |",
            "|---|---|---|---|---|",
        ])
        if jira_results:
            for result in jira_results:
                jira = result.get("jira") or {}
                action = jira.get("jira_action", "NONE")
                issue = jira.get("issue_key") or "None"
                recommendation = jira.get("jira_recommendation", "")
                lines.append(f"| {result.get('service', '')} | {result.get('test', '')} | {action} | {issue} | {recommendation} |")
        else:
            lines.append("| None |  |  |  | No Jira action required |")

        return "\n".join(lines)

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