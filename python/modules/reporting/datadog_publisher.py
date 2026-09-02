"""
Datadog Publisher - Publish analysis results back to Datadog.
"""

from typing import Any, Dict, List
from datetime import datetime
from logger import get_logger
from config import DATADOG_TAGS, DRY_RUN

logger = get_logger('reporting.publisher')


class DatadogPublisher:
    """Publishes analysis results back to Datadog."""

    def __init__(self, datadog_client):
        """
        Initialize publisher.

        Args:
            datadog_client: Instance of DatadogClient
        """
        self.datadog_client = datadog_client
        self.logger = logger

    def publish_analysis(
        self,
        aggregated_results: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> bool:
        """
        Publish analysis results to Datadog.

        Args:
            aggregated_results: Aggregated analysis results
            dry_run: If True, don't actually send to Datadog

        Returns:
            True if successful
        """
        try:
            if dry_run or DRY_RUN:
                self.logger.info(
                    f"[DRY RUN] Would publish {len(aggregated_results)} "
                    f"analysis results to Datadog"
                )
                return True

            # Publish individual result events
            for result in aggregated_results:
                self._publish_result_event(result)

            # Send summary metrics
            self._publish_summary_metrics(aggregated_results)

            self.logger.info(
                f"Published {len(aggregated_results)} analysis results to Datadog"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to publish analysis: {e}")
            return False

    def _publish_result_event(self, result: Dict[str, Any]) -> bool:
        """
        Publish single analysis result as Datadog event.

        Args:
            result: Aggregated result for single test

        Returns:
            True if successful
        """
        try:
            service = result.get('service')
            test = result.get('test')
            status = result.get('current_result', {}).get('status')
            pattern = result.get('failure_pattern', {}).get('pattern')
            jira = result.get('jira_correlation', {})
            ai = result.get('ai_analysis')

            title = f"Analysis: {service}/{test} - {pattern}"
            text = f"Status: {status}\nPattern: {pattern}\n"

            if jira:
                if jira.get('jira_found'):
                    text += f"Jira: {jira.get('jira_id')} ({jira.get('jira_status')})\n"
                else:
                    text += f"Jira: {jira.get('recommendation')}\n"

            if ai:
                text += f"AI Category: {ai.get('failure_category')}\n"
                text += f"Reason: {ai.get('failure_reason')}\n"

            tags = DATADOG_TAGS + [
                f'service:{service}',
                f'test:{test}',
                f'analysis:true',
                f'pattern:{pattern}',
            ]

            if jira and jira.get('jira_found'):
                tags.append(f'jira_id:{jira.get("jira_id")}')

            event = {
                'title': title,
                'text': text,
                'tags': tags,
                'alert_type': 'error' if status == 'FAIL' else 'success',
            }

            return self.datadog_client.send_event(event)

        except Exception as e:
            self.logger.error(f"Failed to publish result event: {e}")
            return False

    def _publish_summary_metrics(
        self,
        results: List[Dict[str, Any]]
    ) -> bool:
        """
        Publish summary metrics to Datadog.

        Args:
            results: Aggregated results

        Returns:
            True if successful
        """
        try:
            now = int(datetime.utcnow().timestamp())

            # Calculate summary statistics
            total = len(results)
            passed = sum(
                1 for r in results
                if r.get('current_result', {}).get('status') == 'PASS'
            )
            failed = total - passed

            # Count by pattern
            patterns = {}
            for r in results:
                pattern = r.get('failure_pattern', {}).get('pattern')
                if pattern:
                    patterns[pattern] = patterns.get(pattern, 0) + 1

            # Build metrics
            metrics = []

            # Overall metrics
            metrics.append({
                'metric': 'test.analysis.total_tests',
                'points': [(now, total)],
                'tags': DATADOG_TAGS,
            })

            metrics.append({
                'metric': 'test.analysis.passed_tests',
                'points': [(now, passed)],
                'tags': DATADOG_TAGS,
            })

            metrics.append({
                'metric': 'test.analysis.failed_tests',
                'points': [(now, failed)],
                'tags': DATADOG_TAGS,
            })

            # Pattern metrics
            for pattern, count in patterns.items():
                metrics.append({
                    'metric': 'test.analysis.pattern_count',
                    'points': [(now, count)],
                    'tags': DATADOG_TAGS + [f'pattern:{pattern}'],
                })

            # Send metrics
            return self.datadog_client.send_metrics(metrics)

        except Exception as e:
            self.logger.error(f"Failed to publish summary metrics: {e}")
            return False
