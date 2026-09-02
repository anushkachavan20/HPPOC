"""
Result Aggregator - Combine all analysis components into final results.
"""

from typing import Any, Dict, List, Optional
from logger import get_logger

logger = get_logger('reporting.aggregator')


class ResultAggregator:
    """Aggregates all analysis results into comprehensive output."""

    def __init__(self):
        self.logger = logger

    def aggregate_analysis(
        self,
        current_results: List[Dict[str, Any]],
        historical_analysis: List[Dict[str, Any]],
        failure_classifications: List[Dict[str, Any]],
        jira_correlations: List[Dict[str, Any]],
        ai_analyses: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Aggregate all analysis components into final results.

        Args:
            current_results: Current test execution results
            historical_analysis: Historical comparison analysis
            failure_classifications: Failure pattern classifications
            jira_correlations: Jira correlation results
            ai_analyses: AI-powered failure analyses (for failed tests only)

        Returns:
            List of comprehensive analysis results for each test
        """
        try:
            aggregated = []

            # Create lookup dictionaries for easier correlation
            historical_map = {
                f"{h.get('service')}/{h.get('test')}": h
                for h in historical_analysis
            }
            classification_map = {
                f"{c.get('service')}/{c.get('test')}": c
                for c in failure_classifications
            }
            jira_map = {
                f"{j.get('service')}/{j.get('test')}": j
                for j in jira_correlations
            }
            ai_map = {}
            if ai_analyses:
                ai_map = {
                    f"{a.get('service')}/{a.get('test')}": a
                    for a in ai_analyses
                }

            # Combine results
            for result in current_results:
                service = result.get('service')
                test = result.get('test')
                status = result.get('status')
                key = f"{service}/{test}"

                # Get related analysis
                historical = historical_map.get(key, {})
                classification = classification_map.get(key, {})
                jira = jira_map.get(key, {})
                ai = ai_map.get(key, {}) if status == 'FAIL' else None

                # Build comprehensive result
                aggregated_result = {
                    'service': service,
                    'test': test,
                    'execution_id': result.get('execution_id'),
                    'timestamp': result.get('timestamp'),
                    'current_result': {
                        'status': status,
                        'http_status': result.get('http_status'),
                        'duration_ms': result.get('duration_ms'),
                        'error_message': result.get('error_message'),
                    },
                    'historical_analysis': historical.get('historical_analysis', {}),
                    'failure_pattern': {
                        'pattern': classification.get('failure_pattern'),
                        'percentage': classification.get('failure_percentage'),
                        'confidence': classification.get('confidence'),
                        'reasoning': classification.get('reasoning'),
                    },
                    'jira_correlation': jira,
                }

                # Add AI analysis only for failed tests
                if status == 'FAIL' and ai:
                    aggregated_result['ai_analysis'] = ai

                aggregated.append(aggregated_result)

            self.logger.info(f"Aggregated analysis for {len(aggregated)} tests")
            return aggregated

        except Exception as e:
            self.logger.error(f"Failed to aggregate analysis: {e}")
            return []

    def get_failed_tests(
        self,
        aggregated_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract only failed test results.

        Args:
            aggregated_results: Complete aggregated results

        Returns:
            List of failed test results
        """
        return [
            r for r in aggregated_results
            if r.get('current_result', {}).get('status') == 'FAIL'
        ]

    def get_by_pattern(
        self,
        aggregated_results: List[Dict[str, Any]],
        pattern: str
    ) -> List[Dict[str, Any]]:
        """
        Filter results by failure pattern.

        Args:
            aggregated_results: Complete aggregated results
            pattern: Failure pattern (e.g., 'Persistent Failure')

        Returns:
            List of results matching the pattern
        """
        return [
            r for r in aggregated_results
            if r.get('failure_pattern', {}).get('pattern') == pattern
        ]

    def get_by_service(
        self,
        aggregated_results: List[Dict[str, Any]],
        service: str
    ) -> List[Dict[str, Any]]:
        """
        Filter results by service.

        Args:
            aggregated_results: Complete aggregated results
            service: Service name

        Returns:
            List of results for the service
        """
        return [
            r for r in aggregated_results
            if r.get('service').lower() == service.lower()
        ]

    def format_result_summary(
        self,
        result: Dict[str, Any]
    ) -> str:
        """
        Format a single result as human-readable summary.

        Args:
            result: Aggregated result for single test

        Returns:
            Formatted summary string
        """
        service = result.get('service')
        test = result.get('test')
        status = result.get('current_result', {}).get('status')
        pattern = result.get('failure_pattern', {}).get('pattern')
        jira = result.get('jira_correlation', {})
        ai = result.get('ai_analysis', {})

        summary = f"{service}/{test}: {status}"
        summary += f"\n  Pattern: {pattern}"

        if status == 'FAIL':
            http_status = result.get('current_result', {}).get('http_status')
            error = result.get('current_result', {}).get('error_message')
            summary += f"\n  HTTP Status: {http_status}"
            if error:
                summary += f"\n  Error: {error[:100]}"

            if jira.get('jira_found'):
                summary += f"\n  Jira: {jira.get('jira_id')} ({jira.get('jira_status')})"
            else:
                summary += f"\n  Jira: {jira.get('recommendation', 'No issue found')}"

            if ai:
                summary += f"\n  AI Analysis: {ai.get('failure_category')}"
                summary += f"\n  Reason: {ai.get('failure_reason')[:100]}"

        return summary
