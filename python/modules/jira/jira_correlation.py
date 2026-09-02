"""
Jira correlation logic for the API Test Analysis POC.

Correlates failed API test results with existing Jira issues
using service, test name, HTTP status, and failure classification.
"""

import logging
from typing import Any, Dict, Optional

from modules.jira.jira_client import JiraClient


logger = logging.getLogger(__name__)


class JiraCorrelation:
    """
    Correlates API test failures with Jira issues.
    """

    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client

    def correlate_failure(
        self,
        test_result: Any,
        classification: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Correlate a k6 test result with an existing Jira issue.

        Parameters:
            test_result:
                K6TestResult object.

            classification:
                Failure classification returned by FailureClassifier.

        Returns:
            Dictionary consumed by ResultAggregator.
        """

        service = str(
            getattr(test_result, "service", "")
        ).strip().lower()

        test_name = str(
            getattr(test_result, "test_name", "")
        ).strip().lower()

        status = str(
            getattr(test_result, "status", "")
        ).strip().upper()

        http_status = getattr(
            test_result,
            "http_status",
            None,
        )

        error = getattr(
            test_result,
            "error",
            None,
        )

        # --------------------------------------------------------------
        # Passing APIs are checked only when five consecutive successes
        # qualify them for a Jira resolution recommendation.
        # --------------------------------------------------------------

        classification_name = self._extract_classification(
            classification
        )

        is_resolved = (
            status == "PASS"
            and (classification_name or "").lower() == "resolved failure"
        )

        if status == "PASS" and not is_resolved:
            logger.debug(
                "Skipping Jira correlation for passing test: %s/%s",
                service,
                test_name,
            )

            return {
                "has_issue": False,
                "issue_key": None,
                "issue_summary": None,
                "issue_url": None,
                "jira_action": "NONE",
                "jira_recommendation": "No Jira action required",
                "reason": "Test passed - Jira correlation not required",
            }

        # --------------------------------------------------------------
        # Extract classification
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # Build JQL
        # --------------------------------------------------------------

        jql = self._build_jql(
            service=service,
            test_name=test_name,
            http_status=http_status,
            classification=classification_name,
        )

        logger.info(
            "Searching Jira for failure: %s/%s",
            service,
            test_name,
        )

        logger.debug(
            "Jira JQL: %s",
            jql,
        )

        # --------------------------------------------------------------
        # Search Jira
        # --------------------------------------------------------------

        try:
            issues = self.jira_client.search_issues(
                jql=jql,
                max_results=10,
            )

        except Exception as exc:
            logger.warning(
                "Jira search failed for %s/%s: %s",
                service,
                test_name,
                exc,
            )

            return {
                "has_issue": False,
                "issue_key": None,
                "issue_summary": None,
                "issue_url": None,
                "jira_action": "SEARCH_FAILED",
                "jira_recommendation": "Check Jira credentials and search permissions",
                "reason": f"Jira search failed: {exc}",
            }

        # --------------------------------------------------------------
        # No matching issue
        # --------------------------------------------------------------

        if not issues:
            logger.info(
                "No Jira issue found for %s/%s",
                service,
                test_name,
            )

            is_persistent = (
                classification_name or ""
            ).strip().lower() == "persistent failure"

            if is_resolved:
                return {
                    "has_issue": False,
                    "issue_key": None,
                    "issue_summary": None,
                    "issue_url": None,
                    "jira_action": "NONE",
                    "jira_recommendation": "No existing Jira issue found to resolve",
                    "reason": "Five consecutive passes but no matching Jira issue",
                }

            jira_action = "CREATE" if is_persistent else "MONITOR"

            if is_persistent:
                recommendation = (
                    f"Create a Jira bug for {service}/{test_name} "
                    f"(HTTP {http_status}, persistent failure)"
                )
            else:
                recommendation = (
                    f"Monitor {service}/{test_name}; create a Jira bug "
                    "if the failure becomes persistent"
                )

            return {
                "has_issue": False,
                "issue_key": None,
                "issue_summary": None,
                "issue_url": None,
                "jira_action": jira_action,
                "jira_recommendation": recommendation,
                "reason": "No matching Jira issue found",
            }

        # --------------------------------------------------------------
        # Use the first matching issue
        # --------------------------------------------------------------

        issue = issues[0]

        issue_key = issue.get("key")

        fields = issue.get("fields", {})

        issue_summary = fields.get(
            "summary",
            "",
        )

        issue_url = self._build_issue_url(
            issue_key
        )

        logger.info(
            "Jira issue correlated: %s -> %s",
            f"{service}/{test_name}",
            issue_key,
        )

        return {
            "has_issue": True,
            "issue_key": issue_key,
            "issue_summary": issue_summary,
            "issue_url": issue_url,
            "jira_action": "RESOLVE" if is_resolved else "UPDATE",
            "jira_recommendation": (
                f"Recommend resolving existing Jira issue {issue_key}"
                if is_resolved
                else f"Review and update existing Jira issue {issue_key}"
            ),
            "reason": (
                "Matching Jira issue found"
            ),
        }

    # ------------------------------------------------------------------
    # JQL Builder
    # ------------------------------------------------------------------

    def _build_jql(
        self,
        service: str,
        test_name: str,
        http_status: Optional[int] = None,
        classification: Optional[str] = None,
    ) -> str:
        """
        Build a Jira JQL query.

        Jira does not support arbitrary fields such as `service`
        or `test`, so the search uses the issue summary.
        """

        service_value = self._escape_jql_value(
            service
        )

        test_value = self._escape_jql_value(
            test_name
        )

        clauses = [
            f'summary ~ "{service_value}"',
            f'summary ~ "{test_value}"',
        ]

        # HTTP status and classification are recorded in the result and
        # recommendation, but should not be required in the Jira summary.
        # Existing issues are commonly titled only with service and test.

        project_key = getattr(
            self.jira_client,
            "project_key",
            None,
        )

        if project_key:
            project_value = self._escape_jql_value(
                project_key
            )

            clauses.insert(
                0,
                f'project = "{project_value}"',
            )

        return " AND ".join(clauses)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_classification(
        classification: Optional[Any],
    ) -> Optional[str]:
        """
        Extract classification name from either a dictionary
        or a string.
        """

        if classification is None:
            return None

        if isinstance(
            classification,
            dict,
        ):
            value = (
                classification.get("classification")
                or classification.get("pattern")
                or classification.get("failure_classification")
            )

            if value:
                return str(value)

            return None

        return str(classification)

    @staticmethod
    def _escape_jql_value(
        value: str,
    ) -> str:
        """
        Escape characters that can interfere with JQL strings.
        """

        return (
            str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

    def _build_issue_url(
        self,
        issue_key: Optional[str],
    ) -> Optional[str]:
        """
        Build the Jira issue URL.
        """

        if not issue_key:
            return None

        base_url = getattr(
            self.jira_client,
            "base_url",
            None,
        )

        if not base_url:
            base_url = getattr(
                self.jira_client,
                "jira_url",
                None,
            )

        if not base_url:
            return None

        return (
            f"{str(base_url).rstrip('/')}"
            f"/browse/{issue_key}"
        )
