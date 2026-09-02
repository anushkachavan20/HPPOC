import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Combines current k6 results with:

    - Historical Datadog analysis
    - Failure classification
    - Jira correlation
    - Optional AI analysis

    The output of this class is the common structure consumed by
    the summary generator and Datadog publisher.
    """

    def __init__(self):
        logger.info("Result aggregator initialized")

    # ------------------------------------------------------------------
    # Main aggregation method
    # ------------------------------------------------------------------

    def aggregate(
        self,
        k6_execution,
        historical_data: Optional[Dict[str, Any]] = None,
        classifications: Optional[Dict[str, Any]] = None,
        jira_results: Optional[Dict[str, Any]] = None,
        ai_analyses: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate all analysis information for every k6 test result.

        Args:
            k6_execution:
                Parsed K6ExecutionResult.

            historical_data:
                Historical Datadog analysis keyed by:
                    service:test

            classifications:
                Failure classifications keyed by:
                    service:test

            jira_results:
                Jira correlation results keyed by:
                    service:test

            ai_analyses:
                Optional AI analysis results.

        Returns:
            List of aggregated test-analysis dictionaries.
        """

        historical_data = historical_data or {}
        classifications = classifications or {}
        jira_results = jira_results or {}

        if ai_analyses is None:
            ai_analyses = []

        aggregated_results = []

        for test_result in k6_execution.results:
            service = test_result.service.lower()
            test_name = test_result.test_name.lower()

            key = f"{service}:{test_name}"

            historical = historical_data.get(key)
            classification = classifications.get(key)
            jira = jira_results.get(key)

            ai_analysis = self._find_ai_analysis(
                ai_analyses=ai_analyses,
                service=service,
                test_name=test_name,
            )

            result = self._build_result(
                test_result=test_result,
                historical=historical,
                classification=classification,
                jira=jira,
                ai_analysis=ai_analysis,
                execution_id=k6_execution.k6_meta.execution_id,
            )

            aggregated_results.append(result)

        logger.info(
            "Aggregated %d test results",
            len(aggregated_results),
        )

        return aggregated_results

    # ------------------------------------------------------------------
    # Build individual result
    # ------------------------------------------------------------------

    def _build_result(
        self,
        test_result,
        historical: Optional[Dict[str, Any]],
        classification: Optional[Dict[str, Any]],
        jira: Optional[Dict[str, Any]],
        ai_analysis: Optional[Dict[str, Any]],
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Build the final normalized representation of one test.
        """

        service = test_result.service.lower()
        test_name = test_result.test_name.lower()
        status = test_result.status.upper()

        historical = historical or {}
        classification = classification or {}
        jira = jira or {}

        # --------------------------------------------------------------
        # Historical information
        # --------------------------------------------------------------

        historical_executions = historical.get(
            "total_executions",
            0,
        )

        historical_passed = historical.get(
            "passed",
            0,
        )

        historical_failed = historical.get(
            "failed",
            0,
        )

        historical_pass_rate = historical.get(
            "pass_rate",
            0.0,
        )

        historical_failure_rate = historical.get(
            "failure_rate",
            0.0,
        )

        historical_trend = historical.get(
            "trend",
            "NO_HISTORY",
        )

        historical_statuses = historical.get(
            "statuses",
            [],
        )

        # --------------------------------------------------------------
        # Classification
        # --------------------------------------------------------------

        classification_name = classification.get(
            "classification",
            classification.get(
                "pattern",
                "Unknown",
            ),
        )

        # --------------------------------------------------------------
        # Jira
        # --------------------------------------------------------------

        has_jira_issue = bool(
            jira.get(
                "has_jira_issue",
                jira.get("has_issue", False),
            )
        )

        issue_key = jira.get(
            "issue_key"
        )

        issue_summary = jira.get(
            "issue_summary"
        )

        issue_url = jira.get(
            "issue_url"
        )

        # --------------------------------------------------------------
        # AI
        # --------------------------------------------------------------

        ai_present = bool(ai_analysis)

        # --------------------------------------------------------------
        # Final structure
        # --------------------------------------------------------------

        result = {
            # ----------------------------------------------------------
            # Current test information
            # ----------------------------------------------------------

            "execution_id": execution_id,
            "service": service,
            "test": test_name,
            "method": test_result.method.upper(),
            "endpoint": test_result.endpoint,
            "status": status,
            "http_status": test_result.http_status,
            "duration_ms": test_result.duration_ms,
            "error_message": test_result.error or "",
            "response_body": test_result.response_body or "",
            "timestamp": test_result.timestamp,

            # ----------------------------------------------------------
            # Historical information
            # ----------------------------------------------------------

            "historical": {
                "total_executions": historical_executions,
                "passed": historical_passed,
                "failed": historical_failed,
                "pass_rate": historical_pass_rate,
                "failure_rate": historical_failure_rate,
                "trend": historical_trend,
                "statuses": historical_statuses,
                "has_history": bool(
                    historical.get(
                        "has_history",
                        False,
                    )
                ),
            },

            # ----------------------------------------------------------
            # Classification
            # ----------------------------------------------------------

            "classification": {
                "pattern": classification_name,
                "current_status": classification.get(
                    "current_status",
                    status,
                ),
                "historical_executions": classification.get(
                    "historical_executions",
                    historical_executions,
                ),
                "historical_passed": classification.get(
                    "historical_passed",
                    historical_passed,
                ),
                "historical_failed": classification.get(
                    "historical_failed",
                    historical_failed,
                ),
                "historical_failure_rate": classification.get(
                    "historical_failure_rate",
                    historical_failure_rate,
                ),
                "historical_trend": classification.get(
                    "historical_trend",
                    historical_trend,
                ),
            },

            # ----------------------------------------------------------
            # Jira
            # ----------------------------------------------------------

            "jira": {
                "has_issue": has_jira_issue,
                "issue_key": issue_key,
                "issue_summary": issue_summary,
                "issue_url": issue_url,
                "jira_action": jira.get(
                    "jira_action",
                    "NONE" if status == "PASS" else "MONITOR",
                ),
                "jira_recommendation": jira.get(
                    "jira_recommendation",
                    "",
                ),
                "reason": jira.get(
                    "reason"
                ),
            },

            # ----------------------------------------------------------
            # AI
            # ----------------------------------------------------------

            "ai_analysis": (
                ai_analysis
                if ai_present
                else None
            ),
        }

        return result

    # ------------------------------------------------------------------
    # AI lookup
    # ------------------------------------------------------------------

    def _find_ai_analysis(
        self,
        ai_analyses: Any,
        service: str,
        test_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find an AI analysis for a specific service/test.

        AI is disabled in the current POC, so this normally returns
        None. The method remains here so AI can be reintroduced later
        without changing the aggregation interface.
        """

        if not ai_analyses:
            return None

        # --------------------------------------------------------------
        # Dictionary format
        # --------------------------------------------------------------

        if isinstance(ai_analyses, dict):
            key = f"{service}:{test_name}"

            if key in ai_analyses:
                return ai_analyses[key]

            # Try service/test nested format.
            service_data = ai_analyses.get(service)

            if isinstance(service_data, dict):
                analysis = service_data.get(test_name)

                if isinstance(analysis, dict):
                    return analysis

        # --------------------------------------------------------------
        # List format
        # --------------------------------------------------------------

        if isinstance(ai_analyses, list):
            for analysis in ai_analyses:
                if not isinstance(analysis, dict):
                    continue

                analysis_service = str(
                    analysis.get(
                        "service",
                        "",
                    )
                ).lower()

                analysis_test = str(
                    analysis.get(
                        "test",
                        analysis.get(
                            "test_name",
                            "",
                        ),
                    )
                ).lower()

                if (
                    analysis_service == service
                    and analysis_test == test_name
                ):
                    return analysis

        return None