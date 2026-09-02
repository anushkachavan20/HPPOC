"""
Summary Generator - Generate overall test execution summary.
"""

from typing import Any, Dict, List
from logger import get_logger

logger = get_logger('reporting.summary')


class SummaryGenerator:
    """Generates human-readable summary of test execution."""

    def __init__(self):
        self.logger = logger

    def generate_summary(
        self,
        aggregated_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate overall execution summary.

        Args:
            aggregated_results: Complete aggregated analysis results

        Returns:
            Formatted summary string
        """
        try:
            # Calculate statistics
            total_tests = len(aggregated_results)
            passed = sum(
                1 for r in aggregated_results
                if r.get('current_result', {}).get('status') == 'PASS'
            )
            failed = total_tests - passed
            pass_percentage = (passed / total_tests * 100) if total_tests > 0 else 0

            # Count by pattern
            patterns = {}
            for result in aggregated_results:
                pattern = result.get('failure_pattern', {}).get('pattern')
                if pattern:
                    patterns[pattern] = patterns.get(pattern, 0) + 1

            # Count Jira coverage
            jira_found = sum(
                1 for r in aggregated_results
                if r.get('jira_correlation', {}).get('jira_found', False)
            )

            # Unique services
            services = set(r.get('service') for r in aggregated_results)
            affected_services_failed = set(
                r.get('service') for r in aggregated_results
                if r.get('current_result', {}).get('status') == 'FAIL'
            )

            # Build summary
            summary = "=== API Test Analysis Summary ===\n\n"
            summary += f"Total Tests Executed: {total_tests}\n"
            summary += f"Passed: {passed} ({pass_percentage:.1f}%)\n"
            summary += f"Failed: {failed} ({100-pass_percentage:.1f}%)\n\n"

            if failed > 0:
                summary += "Failure Breakdown:\n"
                persistent = patterns.get('Persistent Failure', 0)
                flaky = patterns.get('Flaky Failure', 0)
                new_fail = patterns.get('New Failure', 0)

                if persistent > 0:
                    summary += f"  - Persistent Failures: {persistent}\n"
                if flaky > 0:
                    summary += f"  - Flaky Failures: {flaky}\n"
                if new_fail > 0:
                    summary += f"  - New Failures: {new_fail}\n"

                resolved = patterns.get('Resolved Failure', 0)
                if resolved > 0:
                    summary += f"  - Resolved Failures: {resolved}\n"

                summary += f"\nAffected Services: {len(affected_services_failed)}\n"
                for service in sorted(affected_services_failed):
                    service_failures = sum(
                        1 for r in aggregated_results
                        if r.get('service') == service
                        and r.get('current_result', {}).get('status') == 'FAIL'
                    )
                    summary += f"  - {service}: {service_failures} failures\n"

                summary += f"\nJira Coverage:\n"
                summary += f"  - Failures with Jira issues: {jira_found}\n"
                summary += f"  - Failures without Jira issues: {failed - jira_found}\n"

            summary += "\n" + "=" * 40 + "\n"

            return summary

        except Exception as e:
            self.logger.error(f"Failed to generate summary: {e}")
            return "Error generating summary."

    def generate_detailed_summary(
        self,
        aggregated_results: List[Dict[str, Any]]
    ) -> str:
        """
        Generate detailed summary with all test results.

        Args:
            aggregated_results: Complete aggregated analysis results

        Returns:
            Detailed formatted summary
        """
        try:
            summary = self.generate_summary(aggregated_results)

            # Add detailed results for failed tests
            failed_results = [
                r for r in aggregated_results
                if r.get('current_result', {}).get('status') == 'FAIL'
            ]

            if failed_results:
                summary += "\nFailed Test Details:\n"
                summary += "-" * 40 + "\n"

                for result in failed_results:
                    service = result.get('service')
                    test = result.get('test')
                    pattern = result.get('failure_pattern', {}).get('pattern')
                    http_status = result.get('current_result', {}).get('http_status')
                    error = result.get('current_result', {}).get('error_message', '')

                    summary += f"\n{service}/{test}\n"
                    summary += f"  Status: {pattern}\n"
                    summary += f"  HTTP: {http_status}\n"

                    if error:
                        summary += f"  Error: {error[:100]}...\n"

                    # Add Jira info
                    jira = result.get('jira_correlation', {})
                    if jira.get('jira_found'):
                        summary += f"  Jira: {jira.get('jira_id')} ({jira.get('jira_status')})\n"
                    else:
                        summary += f"  Jira: {jira.get('recommendation', 'No issue')}\n"

                    # Add AI analysis
                    ai = result.get('ai_analysis', {})
                    if ai:
                        summary += f"  AI Category: {ai.get('failure_category')}\n"
                        summary += f"  Reason: {ai.get('failure_reason', 'Unknown')[:80]}...\n"

            return summary

        except Exception as e:
            self.logger.error(f"Failed to generate detailed summary: {e}")
            return "Error generating detailed summary."

    def to_json(
        self,
        aggregated_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Convert results to JSON-serializable format.

        Args:
            aggregated_results: Aggregated results

        Returns:
            JSON-friendly dictionary
        """
        return {
            'timestamp': aggregated_results[0].get('timestamp') if aggregated_results else None,
            'total_tests': len(aggregated_results),
            'passed': sum(
                1 for r in aggregated_results
                if r.get('current_result', {}).get('status') == 'PASS'
            ),
            'failed': sum(
                1 for r in aggregated_results
                if r.get('current_result', {}).get('status') == 'FAIL'
            ),
            'results': aggregated_results,
        }
