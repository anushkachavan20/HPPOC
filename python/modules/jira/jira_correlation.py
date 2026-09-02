"""
Jira correlation logic.

Searches Jira for existing issues related to failed API tests.
"""

from typing import Any, Dict, List, Optional

from logger import get_logger

logger = get_logger("jira.correlation")


class JiraCorrelation:
    """
    Correlates failed API test results with existing Jira issues.
    """

    def __init__(
        self,
        jira_client,
        project_key: Optional[str] = None,
    ):
        self.jira_client = jira_client
        self.project_key = project_key
        self.logger = logger

    # ========================================================
    # Public API
    # ========================================================

    def correlate_failures(
        self,
        test_results: List[Dict[str, Any]],
        classifications: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Correlate failed tests with Jira issues.

        Args:
            test_results:
                Current k6 test results.

            classifications:
                Failure classification information.

        Returns:
            Dictionary keyed by test identifier.
        """

        correlations = {}

        if not test_results:
            return correlations

        for result in test_results:

            status = str(
                result.get("status", "")
            ).upper()

            # Only failed tests need Jira correlation.
            if status != "FAIL":
                continue

            service = str(
                result.get("service", "")
            ).strip()

            test_name = str(
                result.get("test")
                or result.get("test_name")
                or ""
            ).strip()

            classification = self._get_classification(
                classifications,
                service,
                test_name,
            )

            correlation = self.correlate_failure(
                result=result,
                classification=classification,
            )

            test_id = self._build_test_id(
                service,
                test_name,
            )

            correlations[test_id] = correlation

        return correlations

    def correlate_failure(
        self,
        result: Dict[str, Any],
        classification: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search Jira for an issue related to one failed test.
        """

        service = str(
            result.get("service", "")
        ).strip()

        test_name = str(
            result.get("test")
            or result.get("test_name")
            or ""
        ).strip()

        endpoint = str(
            result.get("endpoint", "")
        ).strip()

        http_status = result.get(
            "http_status"
        )

        if not classification:
            classification = "Failure"

        self.logger.info(
            "Searching Jira for failure: "
            "service=%s, test=%s, classification=%s",
            service,
            test_name,
            classification,
        )

        # ----------------------------------------------------
        # Build several valid JQL queries.
        #
        # We deliberately use summary ~ because the POC is
        # trying to find existing bugs/tasks related to the
        # failing API test.
        # ----------------------------------------------------

        queries = self._build_search_queries(
            service=service,
            test_name=test_name,
            classification=classification,
            endpoint=endpoint,
            http_status=http_status,
        )

        for jql in queries:

            self.logger.debug(
                "Jira JQL: %s",
                jql,
            )

            issues = self._search_jira(
                jql,
                max_results=5,
            )

            if issues:
                issue = issues[0]

                formatted = self._format_issue(
                    issue
                )

                self.logger.info(
                    "Found Jira issue %s for %s/%s",
                    formatted.get("jira_id"),
                    service,
                    test_name,
                )

                return {
                    "has_issue": True,
                    "issue_key": formatted.get(
                        "jira_id"
                    ),
                    "issue_summary": formatted.get(
                        "summary"
                    ),
                    "issue_url": formatted.get(
                        "url"
                    ),
                    "reason": (
                        "Matching Jira issue found"
                    ),
                }

        self.logger.info(
            "No Jira issue found for %s/%s",
            service,
            test_name,
        )

        return {
            "has_issue": False,
            "issue_key": None,
            "issue_summary": None,
            "issue_url": None,
            "reason": "No matching Jira issue found",
        }

    # ========================================================
    # Build JQL
    # ========================================================

    def _build_search_queries(
        self,
        service: str,
        test_name: str,
        classification: str,
        endpoint: str = "",
        http_status: Any = None,
    ) -> List[str]:
        """
        Build valid Jira JQL queries from the failure data.

        Queries are ordered from most specific to least specific.
        """

        queries = []

        service_value = self._escape_jql_text(
            service
        )

        test_value = self._escape_jql_text(
            test_name
        )

        classification_value = self._escape_jql_text(
            classification
        )

        endpoint_value = self._escape_jql_text(
            endpoint
        )

        # ----------------------------------------------------
        # Query 1:
        # Service + test + classification
        # ----------------------------------------------------

        if service_value and test_value and classification_value:

            queries.append(
                'summary ~ "%s" AND '
                'summary ~ "%s" AND '
                'summary ~ "%s"'
                % (
                    service_value,
                    test_value,
                    classification_value,
                )
            )

        # ----------------------------------------------------
        # Query 2:
        # Service + test
        # ----------------------------------------------------

        if service_value and test_value:

            queries.append(
                'summary ~ "%s" AND '
                'summary ~ "%s"'
                % (
                    service_value,
                    test_value,
                )
            )

        # ----------------------------------------------------
        # Query 3:
        # Service + classification
        # ----------------------------------------------------

        if service_value and classification_value:

            queries.append(
                'summary ~ "%s" AND '
                'summary ~ "%s"'
                % (
                    service_value,
                    classification_value,
                )
            )

        # ----------------------------------------------------
        # Query 4:
        # Test name only
        # ----------------------------------------------------

        if test_value:

            queries.append(
                'summary ~ "%s"'
                % test_value
            )

        # ----------------------------------------------------
        # Query 5:
        # Endpoint
        # ----------------------------------------------------

        if endpoint_value:

            queries.append(
                'summary ~ "%s"'
                % endpoint_value
            )

        # ----------------------------------------------------
        # Add project restriction when configured.
        #
        # Example:
        #
        # project = ABC AND summary ~ "GetPost"
        # ----------------------------------------------------

        if self.project_key:

            project = self._escape_jql_identifier(
                self.project_key
            )

            queries = [
                f"project = {project} AND ({query})"
                for query in queries
            ]

        # Remove duplicates while preserving order.
        unique_queries = []

        for query in queries:

            if query not in unique_queries:
                unique_queries.append(query)

        return unique_queries

    # ========================================================
    # Jira Search
    # ========================================================

    def _search_jira(
        self,
        jql: str,
        max_results: int = 5,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Call the Jira client's search method.
        """

        try:

            # Preferred method used by our JiraClient.
            if hasattr(
                self.jira_client,
                "search_issues",
            ):

                result = self.jira_client.search_issues(
                    jql=jql,
                    max_results=max_results,
                )

                return result or []

            # Backward compatibility.
            if hasattr(
                self.jira_client,
                "search",
            ):

                result = self.jira_client.search(
                    jql,
                    max_results=max_results,
                )

                return result or []

            # Additional backward compatibility.
            if hasattr(
                self.jira_client,
                "search_jira",
            ):

                result = self.jira_client.search_jira(
                    jql,
                    max_results=max_results,
                )

                return result or []

            self.logger.error(
                "Jira client does not expose a search method."
            )

            return []

        except Exception as exc:

            self.logger.error(
                "Jira search error: %s",
                exc,
            )

            return []

    # ========================================================
    # Formatting
    # ========================================================

    def _format_issue(
        self,
        issue: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format a Jira issue.
        """

        if hasattr(
            self.jira_client,
            "format_issue",
        ):

            try:
                return self.jira_client.format_issue(
                    issue
                )

            except Exception:
                pass

        fields = issue.get(
            "fields",
            {},
        )

        return {
            "jira_id": issue.get(
                "key"
            ),
            "summary": fields.get(
                "summary"
            ),
            "status": self._get_status_name(
                fields.get("status")
            ),
            "priority": self._get_status_name(
                fields.get("priority")
            ),
            "labels": fields.get(
                "labels",
                [],
            ),
            "url": self._build_issue_url(
                issue.get("key")
            ),
        }

    # ========================================================
    # Helpers
    # ========================================================

    def _get_classification(
        self,
        classifications: Optional[Dict[str, Any]],
        service: str,
        test_name: str,
    ) -> str:
        """
        Extract classification for a test.
        """

        if not classifications:
            return "Failure"

        test_id = self._build_test_id(
            service,
            test_name,
        )

        classification = classifications.get(
            test_id
        )

        if isinstance(
            classification,
            dict,
        ):

            return str(
                classification.get(
                    "classification"
                )
                or classification.get(
                    "pattern"
                )
                or "Failure"
            )

        if classification:
            return str(
                classification
            )

        return "Failure"

    def _build_test_id(
        self,
        service: str,
        test_name: str,
    ) -> str:
        """
        Build a consistent test identifier.
        """

        return (
            f"{service}:{test_name}"
        )

    @staticmethod
    def _escape_jql_text(
        value: str,
    ) -> str:
        """
        Escape text used inside a JQL quoted string.
        """

        if not value:
            return ""

        return (
            str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

    @staticmethod
    def _escape_jql_identifier(
        value: str,
    ) -> str:
        """
        Escape a JQL identifier such as a project key.

        Normal Jira project keys such as ABC or PROJ are already
        safe, so this mainly protects unusual values.
        """

        value = str(value).strip()

        if (
            value.isalnum()
            and "-" not in value
            and " " not in value
        ):
            return value

        return (
            '"'
            + value.replace('"', '\\"')
            + '"'
        )

    def _build_issue_url(
        self,
        issue_key: Optional[str],
    ) -> Optional[str]:
        """
        Build Jira browse URL.
        """

        if not issue_key:
            return None

        jira_url = getattr(
            self.jira_client,
            "jira_url",
            "",
        )

        if not jira_url:
            return None

        return (
            f"{jira_url.rstrip('/')}"
            f"/browse/{issue_key}"
        )

    @staticmethod
    def _get_status_name(
        value: Any,
    ) -> str:
        """
        Extract a Jira status/priority name.
        """

        if isinstance(
            value,
            dict,
        ):

            return str(
                value.get(
                    "name",
                    "",
                )
            )

        return str(
            value or ""
        )
