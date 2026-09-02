"""
Datadog Ingestion - Send k6 test results to Datadog.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from logger import get_logger
from config import DATADOG_TAGS, ENVIRONMENT, DRY_RUN

logger = get_logger('ingestion.datadog')


class DatadogIngestion:
    """Handles ingestion of test results into Datadog."""

    def __init__(self, datadog_client):
        """
        Initialize ingestion handler.

        Args:
            datadog_client: Instance of DatadogClient
        """
        self.datadog_client = datadog_client
        self.logger = logger

    def ingest_test_results(
        self,
        results: List[Dict[str, Any]],
        execution_id: str,
        dry_run: bool = False
    ) -> bool:
        """
        Ingest normalized test results into Datadog.

        Args:
            results: List of normalized test results
            execution_id: Execution ID
            dry_run: If True, don't actually send to Datadog

        Returns:
            True if successful, False otherwise
        """
        try:
            if dry_run or DRY_RUN:
                self.logger.info(f"[DRY RUN] Would ingest {len(results)} test results")
                return True

            # Send event for each test result
            for result in results:
                success = self._send_event(result, execution_id)
                if not success:
                    self.logger.error(f"Failed to send event for {result['service']}/{result['test']}")
                    return False

            # Send summary metrics
            self._send_metrics(results, execution_id)

            self.logger.info(f"Successfully ingested {len(results)} test results to Datadog")
            return True

        except Exception as e:
            self.logger.error(f"Failed to ingest test results: {e}")
            return False

    def _send_event(self, result: Dict[str, Any], execution_id: str) -> bool:
        """
        Send individual test result as Datadog event.

        Args:
            result: Normalized test result
            execution_id: Execution ID

        Returns:
            True if successful
        """
        try:
            # Prepare event
            service = result['service']
            test = result['test']
            status = result['status']
            http_status = result['http_status']
            error_msg = result['error_message']

            title = f"API Test: {service.upper()}/{test.upper()}"
            text = f"Status: {status}\nHTTP Status: {http_status}"
            if error_msg:
                text += f"\nError: {error_msg}"

            tags = DATADOG_TAGS + [
                f'service:{service}',
                f'test:{test}',
                f'status:{status.lower()}',
                f'http_status:{http_status}',
                f'execution_id:{execution_id}',
            ]

            event = {
                'title': title,
                'text': text,
                'timestamp': datetime.utcnow().timestamp(),
                'alert_type': 'error' if status == 'FAIL' else 'success',
                'tags': tags,
                'metadata': {
                    'execution_id': execution_id,
                    'service': service,
                    'test': test,
                    'status': status,
                    'http_status': http_status,
                    'duration_ms': result.get('duration_ms', 0),
                    'error_message': error_msg,
                }
            }

            # Send to Datadog
            return self.datadog_client.send_event(event)

        except Exception as e:
            self.logger.error(f"Failed to send event: {e}")
            return False

    def _send_metrics(self, results: List[Dict[str, Any]], execution_id: str) -> bool:
        """
        Send aggregated metrics to Datadog.

        Args:
            results: List of normalized test results
            execution_id: Execution ID

        Returns:
            True if successful
        """
        try:
            now = int(datetime.utcnow().timestamp())
            pass_count = sum(1 for r in results if r['status'] == 'PASS')
            fail_count = sum(1 for r in results if r['status'] == 'FAIL')

            metrics = []

            # Overall metrics
            metrics.append({
                'metric': 'test.total_count',
                'points': [(now, len(results))],
                'tags': DATADOG_TAGS + [f'execution_id:{execution_id}'],
            })

            metrics.append({
                'metric': 'test.pass_count',
                'points': [(now, pass_count)],
                'tags': DATADOG_TAGS + [f'execution_id:{execution_id}'],
            })

            metrics.append({
                'metric': 'test.fail_count',
                'points': [(now, fail_count)],
                'tags': DATADOG_TAGS + [f'execution_id:{execution_id}'],
            })

            # Per-service/test metrics
            for result in results:
                service = result['service']
                test = result['test']
                status_value = 1 if result['status'] == 'PASS' else 0

                tags = DATADOG_TAGS + [
                    f'service:{service}',
                    f'test:{test}',
                    f'execution_id:{execution_id}',
                ]

                metrics.append({
                    'metric': 'test.result',
                    'points': [(now, status_value)],
                    'tags': tags,
                })

                metrics.append({
                    'metric': 'test.duration_ms',
                    'points': [(now, result.get('duration_ms', 0))],
                    'tags': tags,
                })

            # Send all metrics
            return self.datadog_client.send_metrics(metrics)

        except Exception as e:
            self.logger.error(f"Failed to send metrics: {e}")
            return False
