import logging
import time
from typing import Any, Dict, List

from config import DATADOG_TAGS

logger = logging.getLogger(__name__)


class DatadogIngestion:
    """
    Handles ingestion of k6 test results into Datadog.

    Each test result is published as:
    - A Datadog event
    - A test result metric
    - A duration metric

    An execution summary is also published.
    """

    def __init__(
        self,
        datadog_client,
        dry_run: bool = False,
    ):
        self.datadog_client = datadog_client
        self.dry_run = dry_run

    # ------------------------------------------------------------------
    # Main ingestion method
    # ------------------------------------------------------------------

    def ingest_execution(self, k6_execution) -> Dict[str, Any]:
        """
        Ingest a complete k6 execution into Datadog.

        Args:
            k6_execution:
                Parsed K6ExecutionResult object.

        Returns:
            Dictionary containing ingestion statistics.
        """

        results = k6_execution.results
        metadata = k6_execution.k6_meta

        execution_id = metadata.execution_id

        logger.info(
            "Starting Datadog ingestion for execution: %s",
            execution_id,
        )

        if self.dry_run:
            logger.info(
                "[DRY RUN] Would ingest %d test results",
                len(results),
            )

            return {
                "success": True,
                "dry_run": True,
                "execution_id": execution_id,
                "tests_processed": len(results),
                "events_sent": 0,
                "metrics_sent": 0,
            }

        events_sent = 0
        metrics_sent = 0

        # --------------------------------------------------------------
        # Send individual test results
        # --------------------------------------------------------------

        for test_result in results:
            try:
                event_sent = self._send_test_event(
                    test_result=test_result,
                    execution_id=execution_id,
                )

                if event_sent:
                    events_sent += 1

            except Exception as exc:
                logger.error(
                    "Failed to ingest event for %s/%s: %s",
                    test_result.service,
                    test_result.test_name,
                    exc,
                )

        # --------------------------------------------------------------
        # Send metrics
        # --------------------------------------------------------------

        try:
            metrics = self._build_test_metrics(
                results=results,
                execution_id=execution_id,
            )

            if metrics:
                metrics_sent = len(metrics)

                success = self.datadog_client.send_metrics(
                    metrics
                )

                if not success:
                    logger.error(
                        "Failed to send test metrics to Datadog"
                    )
                    metrics_sent = 0

        except Exception as exc:
            logger.error(
                "Failed to ingest test metrics: %s",
                exc,
            )

        # --------------------------------------------------------------
        # Send execution summary
        # --------------------------------------------------------------

        try:
            summary_event = self._send_execution_summary(
                k6_execution=k6_execution,
            )

            if summary_event:
                events_sent += 1

        except Exception as exc:
            logger.error(
                "Failed to send execution summary: %s",
                exc,
            )

        logger.info(
            "Datadog ingestion completed: "
            "%d events, %d metrics",
            events_sent,
            metrics_sent,
        )

        return {
            "success": True,
            "dry_run": False,
            "execution_id": execution_id,
            "tests_processed": len(results),
            "events_sent": events_sent,
            "metrics_sent": metrics_sent,
        }

    # ------------------------------------------------------------------
    # Individual test event
    # ------------------------------------------------------------------

    def _send_test_event(
        self,
        test_result,
        execution_id: str,
    ) -> bool:
        """
        Send one test result as a Datadog event.
        """

        service = test_result.service.lower()
        test_name = test_result.test_name.lower()
        status = test_result.status.upper()

        http_status = test_result.http_status
        duration_ms = test_result.duration_ms

        if status == "PASS":
            alert_type = "success"
        else:
            alert_type = "error"

        title = (
            f"API Test {status}: "
            f"{service}/{test_name}"
        )

        error_message = (
            test_result.error
            if test_result.error
            else ""
        )

        text_lines = [
            f"Service: {service}",
            f"Test: {test_name}",
            f"Method: {test_result.method}",
            f"Endpoint: {test_result.endpoint}",
            f"HTTP Status: {http_status}",
            f"Duration: {duration_ms:.2f} ms",
            f"Execution ID: {execution_id}",
        ]

        if error_message:
            text_lines.append(
                f"Error: {error_message}"
            )

        tags = list(DATADOG_TAGS)

        tags.extend(
            [
                f"service:{service}",
                f"test:{test_name}",
                f"status:{status.lower()}",
                f"http_status:{http_status}",
                f"execution_id:{execution_id}",
            ]
        )

        return self.datadog_client.send_event(
            title=title,
            text="\n".join(text_lines),
            tags=tags,
            alert_type=alert_type,
        )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def _build_test_metrics(
        self,
        results,
        execution_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Build Datadog metric payloads for individual tests.
        """

        timestamp = int(time.time())

        metrics = []

        for test_result in results:
            service = test_result.service.lower()
            test_name = test_result.test_name.lower()

            status = test_result.status.upper()

            tags = list(DATADOG_TAGS)

            tags.extend(
                [
                    f"service:{service}",
                    f"test:{test_name}",
                    f"status:{status.lower()}",
                    f"http_status:{test_result.http_status}",
                    f"execution_id:{execution_id}",
                ]
            )

            # ----------------------------------------------------------
            # Test result metric
            #
            # PASS = 1
            # FAIL = 0
            # ----------------------------------------------------------

            result_value = (
                1 if status == "PASS" else 0
            )

            metrics.append(
                {
                    "metric": "api_test.result",
                    "type": "gauge",
                    "points": [
                        [
                            timestamp,
                            result_value,
                        ]
                    ],
                    "tags": tags,
                }
            )

            # ----------------------------------------------------------
            # Test duration metric
            # ----------------------------------------------------------

            metrics.append(
                {
                    "metric": "api_test.duration_ms",
                    "type": "gauge",
                    "points": [
                        [
                            timestamp,
                            test_result.duration_ms,
                        ]
                    ],
                    "tags": tags,
                }
            )

        return metrics

    # ------------------------------------------------------------------
    # Execution summary
    # ------------------------------------------------------------------

    def _send_execution_summary(
        self,
        k6_execution,
    ) -> bool:
        """
        Send a summary event for the complete k6 execution.
        """

        metadata = k6_execution.k6_meta
        results = k6_execution.results

        execution_id = metadata.execution_id

        total = len(results)

        passed = sum(
            1
            for result in results
            if result.status.upper() == "PASS"
        )

        failed = total - passed

        pass_rate = (
            (passed / total) * 100
            if total > 0
            else 0
        )

        fail_rate = (
            (failed / total) * 100
            if total > 0
            else 0
        )

        services = {}

        for result in results:
            service = result.service.lower()

            if service not in services:
                services[service] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                }

            services[service]["total"] += 1

            if result.status.upper() == "PASS":
                services[service]["passed"] += 1
            else:
                services[service]["failed"] += 1

        text_lines = [
            f"Execution ID: {execution_id}",
            f"Total Tests: {total}",
            f"Passed: {passed}",
            f"Failed: {failed}",
            f"Pass Rate: {pass_rate:.2f}%",
            f"Failure Rate: {fail_rate:.2f}%",
        ]

        if metadata.scenario:
            text_lines.append(
                f"Scenario: {metadata.scenario}"
            )

        if metadata.duration:
            text_lines.append(
                f"Duration: {metadata.duration}"
            )

        if metadata.vus is not None:
            text_lines.append(
                f"VUs: {metadata.vus}"
            )

        text_lines.append("")
        text_lines.append("Service Breakdown:")

        for service, service_data in sorted(
            services.items()
        ):
            text_lines.append(
                f"- {service}: "
                f"{service_data['passed']} passed, "
                f"{service_data['failed']} failed, "
                f"{service_data['total']} total"
            )

        tags = list(DATADOG_TAGS)

        tags.extend(
            [
                "event_type:api_test_execution",
                f"execution_id:{execution_id}",
            ]
        )

        alert_type = (
            "error"
            if failed > 0
            else "success"
        )

        return self.datadog_client.send_event(
            title=(
                f"API Test Execution "
                f"{'FAILED' if failed > 0 else 'PASSED'}: "
                f"{execution_id}"
            ),
            text="\n".join(text_lines),
            tags=tags,
            alert_type=alert_type,
        )