import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class JiraCorrelation:
    """
    Correlates classified API test failures with existing Jira issues.

    The correlation is based primarily on the failure classification and
    the service/test information.
    """

    def __init__(self, jira_client):
        self.jira_client = jira_client

        logger.info("Jira correlation initialized")

    # ------------------------------------------------------------------
    # Main correlation method
    # ------------------------------------------------------------------

    def correlate_failure(
        self,
        test_result,
        classification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search Jira for issues related to the current failure.

        Args:
            test_result:
                Current K6TestResult.

            classification:
                Result produced by FailureClassifier.

        Returns:
            Jira correlation result.
        """

        classification = classification or {}

        service = test_result.service.lower()
        test_name = test_result.test_name.lower()
        status = test_result.status.upper()

        classification_name = str(
            classification.get(
                "classification",
                classification.get("pattern", ""),
            )
        )

        logger.debug(
            "Jira correlation for %s/%s: status=%s, classification=%s",
            service,
            test_name,
            status,
            classification_name,
        )

        # --------------------------------------------------------------
        # Healthy / passing tests do not need Jira correlation.
        # --------------------------------------------------------------

        if status == "PASS":
            return {
                "has_jira_issue": False,
                "issue_key": None,
                "issue_summary": None,
                "issue_url": None,
                "classification": classification_name,
                "reason": "Test passed",
            }

        # --------------------------------------------------------------
        # Only attempt Jira correlation for a failure.
        # --------------------------------------------------------------

        if status != "FAIL":
            return {
                "has_jira_issue": False,
                "issue_key": None,
                "issue_summary": None,
                "issue_url": None,
                "classification": classification_name,
                "reason": f"Unsupported status: {status}",
            }

        # --------------------------------------------------------------
        # Build search terms.
        # --------------------------------------------------------------

        search_terms = self._build_search_terms(
            service=service,
            test_name=test_name,
            classification=classification_name,
        )

        for search_term in search_terms:
            try:
                logger.debug(
                    "Searching Jira using: %s",
                    search_term,
                )

                issues = self._search_jira(
                    search_term
                )

                if issues:
                    issue = issues[0]

                    result = self._build_issue_result(
                        issue=issue,
                        classification=classification_name,
                    )

                    logger.info(
                        "Jira issue correlated for %s/%s: %s",
                        service,
                        test_name,
                        result.get("issue_key"),
                    )

                    return result

            except Exception as exc:
                logger.warning(
                    "Jira search failed for '%s': %s",
                    search_term,
                    exc,
                )

        # --------------------------------------------------------------
        # No matching Jira issue found.
        # --------------------------------------------------------------

        logger.info(
            "No Jira issue found for %s/%s",
            service,
            test_name,
        )

        return {
            "has_jira_issue": False,
            "issue_key": None,
            "issue_summary": None,
            "issue_url": None,
            "classification": classification_name,
            "reason": "No matching Jira issue found",
        }

    # ------------------------------------------------------------------
    # Search terms
    # ------------------------------------------------------------------

    def _build_search_terms(
        self,
        service: str,
        test_name: str,
        classification: str,
    ):
        """
        Build Jira search terms from the service, test and
        failure classification.

        Multiple search terms are tried from most specific to
        more general.
        """

        terms = []

        # Most specific search.
        if service and test_name and classification:
            terms.append(
                f'"{service}" AND '
                f'"{test_name}" AND '
                f'"{classification}"'
            )

        # Service + test.
        if service and test_name:
            terms.append(
                f'"{service}" AND "{test_name}"'
            )

        # Service + classification.
        if service and classification:
            terms.append(
                f'"{service}" AND "{classification}"'
            )

        # Test only.
        if test_name:
            terms.append(
                f'"{test_name}"'
            )

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(terms))

    # ------------------------------------------------------------------
    # Jira search
    # ------------------------------------------------------------------

    def _search_jira(
        self,
        search_term: str,
    ):
        """
        Execute a Jira search.

        Supports the common search method names used by the
        JiraClient implementation.
        """

        # Preferred method.
        if hasattr(self.jira_client, "search_issues"):
            return self.jira_client.search_issues(
                search_term
            )

        # Backward compatibility.
        if hasattr(self.jira_client, "search"):
            return self.jira_client.search(
                search_term
            )

        if hasattr(self.jira_client, "search_jira"):
            return self.jira_client.search_jira(
                search_term
            )

        raise AttributeError(
            "JiraClient does not provide a supported "
            "issue-search method"
        )

    # ------------------------------------------------------------------
    # Build Jira result
    # ------------------------------------------------------------------

    def _build_issue_result(
        self,
        issue,
        classification: str,
    ) -> Dict[str, Any]:
        """
        Normalize a Jira issue into the structure used by the
        reporting layer.
        """

        # --------------------------------------------------------------
        # JiraClient may return either:
        #
        # 1. A dictionary
        # 2. A Jira issue object
        # --------------------------------------------------------------

        if isinstance(issue, dict):
            issue_key = issue.get("key")

            fields = issue.get(
                "fields",
                {},
            )

            if not isinstance(fields, dict):
                fields = {}

            summary = fields.get(
                "summary"
            ) or issue.get(
                "summary"
            )

            issue_url = issue.get(
                "self"
            ) or issue.get(
                "url"
            )

        else:
            issue_key = getattr(
                issue,
                "key",
                None,
            )

            fields = getattr(
                issue,
                "fields",
                None,
            )

            summary = getattr(
                fields,
                "summary",
                None,
            )

            issue_url = getattr(
                issue,
                "self",
                None,
            )

        # --------------------------------------------------------------
        # Construct Jira URL when the client returned only the key.
        # --------------------------------------------------------------

        if issue_key and not issue_url:
            issue_url = self._build_issue_url(
                issue_key
            )

        return {
            "has_jira_issue": bool(issue_key),
            "issue_key": issue_key,
            "issue_summary": summary,
            "issue_url": issue_url,
            "classification": classification,
            "reason": (
                "Matching Jira issue found"
                if issue_key
                else "Jira issue returned without key"
            ),
        }

    # ------------------------------------------------------------------
    # Build Jira URL
    # ------------------------------------------------------------------

    def _build_issue_url(
        self,
        issue_key: str,
    ) -> Optional[str]:
        """
        Build a Jira browse URL using the Jira client's configured
        base URL, when available.
        """

        base_url = getattr(
            self.jira_client,
            "base_url",
            None,
        )

        if not base_url:
            base_url = getattr(
                self.jira_client,
                "url",
                None,
            )

        if not base_url:
            return None

        base_url = str(base_url).rstrip("/")

        # Avoid duplicating /browse when a Jira client happens
        # to expose a URL containing it.
        if base_url.endswith("/browse"):
            return f"{base_url}/{issue_key}"

        return f"{base_url}/browse/{issue_key}"