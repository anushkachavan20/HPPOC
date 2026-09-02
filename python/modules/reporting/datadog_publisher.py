import logging
import time
from typing import Any, Dict, List

from config import DATADOG_TAGS, DRY_RUN
from modules.datadog.datadog_client import DatadogClient

logger = logging.getLogger(__name__)


class DatadogPublisher:
    """
    Publishes the final API test analysis results to Datadog.

    Raw k6 results are handled by DatadogIngestion.
    This class publishes the enriched analysis:
      - failure classification
      - historical trend
      - Jira correlation
      - test result
    """

    def __init__(
        self,
        datadog_client: DatadogClient,
        dry_run: bool = None,
    ):
        self.datadog_client = datadog_client
        self.dry_run = DRY_RUN if dry_run is None else dry_run

    def publish(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish aggregated analysis results to Datadog.

        Args:
            results: List of aggregated API test analysis results.

        Returns:
            Dictionary containing publishing statistics.
        """

        if not results:
            logger.warning("No analysis results to publish")
            return {
                "success": True,
                "dry_run": self.dry_run,
                "results_published": 0,
                "events_published": 0,
                "metrics_published": 0,
            }

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would publish %d analysis results to Datadog",
                len(results),
            )

            for result in results:
                self._log_dry_run_result(result)

            return {
                "success": True,
                "dry_run": True,
                "results_published": len(results),
                "events_published": 0,
                "metrics_published": 0,
            }

        events_published = 0
        metrics: List[Dict[str, Any]] = []

        for result in results:
            try:
                event = self._build_analysis_event(result)

                response = self.datadog_client.send_event(
                    title=event["title"],
                    text=event["text"],
                    tags=event["tags"],
                    alert_type=event["alert_type"],
                )

                if response:
                    events_published += 1

                test_metrics = self._build_analysis_metrics(result)
                metrics.extend(test_metrics)

            except Exception as exc:
                logger.exception(
                    "Failed to publish analysis result for %s/%s: %s",
                    result.get("service"),
                    result.get("test"),
                    exc,
                )

        metrics_published = 0

        if metrics:
            try:
                response = self.datadog_client.send_metrics(metrics)

                if response:
                    metrics_published = len(metrics)

            except Exception as exc:
                logger.exception(
                    "Failed to publish analysis metrics to Datadog: %s",
                    exc,
                )

        success = (
            events_published == len(results)
            and metrics_published == len(metrics)
        )

        logger.info(
            "Published analysis results: %d/%d events, %d/%d metrics",
            events_published,
            len(results),
            metrics_published,
            len(metrics),
        )

        return {
            "success": success,
            "dry_run": False,
            "results_published": len(results),
            "events_published": events_published,
            "metrics_published": metrics_published,
        }

    def _build_analysis_event(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a Datadog event for one analyzed API test.
        """

        service = result.get("service", "unknown")
        test_name = result.get("test", "unknown")
        status = str(result.get("status", "UNKNOWN")).upper()

        classification = self._get_classification(result)
        historical = result.get("historical") or {}
        jira = result.get("jira") or {}

        execution_id = result.get(
            "execution_id",
            "unknown",
        )

        http_status = result.get("http_status", 0)
        duration_ms = result.get("duration_ms", 0)

        error_message = result.get(
            "error_message",
            "",
        )

        historical_executions = historical.get(
            "total_executions",
            0,
        )

        historical_pass_rate = historical.get(
            "pass_rate",
            0,
        )

        historical_failure_rate = historical.get(
            "failure_rate",
            0,
        )

        historical_trend = historical.get(
            "trend",
            "NO_HISTORY",
        )

        jira_issue = jira.get(
            "issue_key",
            "",
        )

        jira_summary = jira.get(
            "issue_summary",
            "",
        )

        jira_url = jira.get(
            "issue_url",
            "",
        )

        if status == "PASS":
            alert_type = "success"
        else:
            alert_type = "error"

        title = (
            f"API Test Analysis: "
            f"{status} - {service}/{test_name}"
        )

        text_lines = [
            "API Test Analysis Result",
            "",
            f"Service: {service}",
            f"Test: {test_name}",
            f"Status: {status}",
            f"HTTP Status: {http_status}",
            f"Duration: {duration_ms} ms",
            f"Classification: {classification}",
            f"Execution ID: {execution_id}",
            "",
            "Historical Analysis:",
            f"  Executions: {historical_executions}",
            f"  Pass Rate: {historical_pass_rate:.2f}%",
            f"  Failure Rate: {historical_failure_rate:.2f}%",
            f"  Trend: {historical_trend}",
        ]

        if error_message:
            text_lines.extend(
                [
                    "",
                    "Error:",
                    str(error_message),
                ]
            )

        if jira_issue:
            text_lines.extend(
                [
                    "",
                    "Jira:",
                    f"  Issue: {jira_issue}",
                ]
            )

            if jira_summary:
                text_lines.append(
                    f"  Summary: {jira_summary}"
                )

            if jira_url:
                text_lines.append(
                    f"  URL: {jira_url}"
                )
        else:
            text_lines.extend(
                [
                    "",
                    "Jira:",
                    "  No correlated Jira issue found",
                ]
            )

        tags = self._build_tags(result)

        return {
            "title": title,
            "text": "\n".join(text_lines),
            "tags": tags,
            "alert_type": alert_type,
        }

    def _build_analysis_metrics(
        self,
        result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Build Datadog metrics for the analyzed test.
        """

        service = result.get("service", "unknown")
        test_name = result.get("test", "unknown")
        execution_id = result.get(
            "execution_id",
            "unknown",
        )

        status = str(
            result.get("status", "UNKNOWN")
        ).upper()

        classification = self._get_classification(result)

        historical = result.get("historical") or {}

        timestamp = int(time.time())

        tags = self._build_tags(result)

        metrics = [
            {
                "metric": "api_test.analysis_result",
                "type": "gauge",
                "points": [
                    {
                        "timestamp": timestamp,
                        "value": 1 if status == "PASS" else 0,
                    }
                ],
                "tags": tags,
            },
            {
                "metric": "api_test.failure_classification",
                "type": "gauge",
                "points": [
                    {
                        "timestamp": timestamp,
                        "value": 1 if status == "FAIL" else 0,
                    }
                ],
                "tags": tags,
            },
            {
                "metric": "api_test.historical_failure_rate",
                "type": "gauge",
                "points": [
                    {
                        "timestamp": timestamp,
                        "value": historical.get(
                            "failure_rate",
                            0,
                        ),
                    }
                ],
                "tags": tags,
            },
        ]

        return metrics

    def _build_tags(
        self,
        result: Dict[str, Any],
    ) -> List[str]:
        """
        Build common Datadog tags for an analysis result.
        """

        service = result.get("service", "unknown")
        test_name = result.get("test", "unknown")

        status = str(
            result.get("status", "UNKNOWN")
        ).lower()

        execution_id = result.get(
            "execution_id",
            "unknown",
        )

        classification = self._get_classification(result)

        historical = result.get("historical") or {}

        trend = historical.get(
            "trend",
            "NO_HISTORY",
        )

        jira = result.get("jira") or {}

        has_jira = jira.get(
            "has_issue",
            False,
        )

        tags = list(DATADOG_TAGS)

        tags.extend(
            [
                f"service:{service}",
                f"test:{test_name}",
                f"status:{status}",
                f"execution_id:{execution_id}",
                f"classification:{self._normalize_tag_value(classification)}",
                f"historical_trend:{self._normalize_tag_value(trend)}",
                f"jira_issue:{str(has_jira).lower()}",
            ]
        )

        return tags

    def _get_classification(
        self,
        result: Dict[str, Any],
    ) -> str:
        """
        Support both the current nested classification format
        and the older flat format.
        """

        classification = result.get("classification")

        if isinstance(classification, dict):
            value = classification.get(
                "pattern",
                classification.get(
                    "classification",
                    "Unknown",
                ),
            )

            return str(value)

        if classification:
            return str(classification)

        return "Unknown"

    def _normalize_tag_value(
        self,
        value: Any,
    ) -> str:
        """
        Make values safe for use as Datadog tag values.
        """

        value = str(value).strip().lower()

        value = value.replace(" ", "_")
        value = value.replace("/", "_")
        value = value.replace(":", "_")

        return value

    def _log_dry_run_result(
        self,
        result: Dict[str, Any],
    ) -> None:
        """
        Log what would be published without contacting Datadog.
        """

        service = result.get(
            "service",
            "unknown",
        )

        test_name = result.get(
            "test",
            "unknown",
        )

        status = str(
            result.get("status", "UNKNOWN")
        ).upper()

        classification = self._get_classification(
            result
        )

        historical = result.get(
            "historical"
        ) or {}

        jira = result.get(
            "jira"
        ) or {}

        logger.info(
            "[DRY RUN] %s/%s -> status=%s, "
            "classification=%s, trend=%s, jira=%s",
            service,
            test_name,
            status,
            classification,
            historical.get(
                "trend",
                "NO_HISTORY",
            ),
            jira.get(
                "issue_key",
                "none",
            ),
        )