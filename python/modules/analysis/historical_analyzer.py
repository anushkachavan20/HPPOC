"""
Historical Analyzer - Compare current test execution with historical data.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from logger import get_logger

logger = get_logger('analysis.historical')


class HistoricalAnalyzer:
    """Analyzes current execution against historical data from Datadog."""

    def __init__(self, datadog_client):
        """
        Initialize historical analyzer.

        Args:
            datadog_client: Instance of DatadogClient
        """
        self.datadog_client = datadog_client
        self.logger = logger

    def get_historical_data(
        self,
        service: str,
        test: str,
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve historical execution data from Datadog.

        Args:
            service: Service name
            test: Test name
            limit: Number of previous executions to retrieve

        Returns:
            List of historical executions (most recent first) or None
        """
        try:
            executions = self.datadog_client.get_previous_executions(
                service, test, limit
            )
            if executions is None:
                self.logger.warning(
                    f"No historical data found for {service}/{test}"
                )
                return []
            return executions
        except Exception as e:
            self.logger.error(f"Failed to get historical data: {e}")
            return None

    def extract_status_sequence(
        self,
        executions: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract status sequence from historical executions.

        Args:
            executions: List of execution records (most recent first)

        Returns:
            List of statuses in chronological order (oldest first)
        """
        statuses = []
        for execution in reversed(executions):  # Reverse to get oldest first
            # Extract status from execution metadata/tags
            if 'metadata' in execution and 'status' in execution['metadata']:
                statuses.append(execution['metadata']['status'])
            elif 'tags' in execution:
                # Try to extract from tags
                for tag in execution['tags']:
                    if tag.startswith('status:'):
                        status = tag.split(':', 1)[1].upper()
                        if status in ['PASS', 'FAIL']:
                            statuses.append(status)
                            break

        return statuses

    def calculate_statistics(
        self,
        current_result: Dict[str, Any],
        historical_executions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate comparison statistics between current and historical data.

        Args:
            current_result: Current test execution result
            historical_executions: List of previous executions

        Returns:
            Dictionary with analysis statistics
        """
        try:
            current_status = current_result.get('status', 'UNKNOWN')

            # Extract historical statuses
            historical_statuses = self.extract_status_sequence(
                historical_executions
            )

            # Calculate counts
            total_historical = len(historical_statuses)
            historical_pass = sum(1 for s in historical_statuses if s == 'PASS')
            historical_fail = sum(1 for s in historical_statuses if s == 'FAIL')

            # Calculate rates
            if total_historical > 0:
                historical_pass_rate = historical_pass / total_historical
                historical_fail_rate = historical_fail / total_historical
            else:
                historical_pass_rate = 0.0
                historical_fail_rate = 0.0

            # Detect trends
            recent_5_statuses = historical_statuses[-5:] if total_historical >= 5 else historical_statuses
            recent_trend = 'deteriorating' if recent_5_statuses and recent_5_statuses[-1] == 'FAIL' else 'improving'

            # Last pass/fail dates
            last_pass_idx = None
            last_fail_idx = None
            for i, status in enumerate(reversed(historical_statuses)):
                if status == 'PASS' and last_pass_idx is None:
                    last_pass_idx = total_historical - i - 1
                if status == 'FAIL' and last_fail_idx is None:
                    last_fail_idx = total_historical - i - 1

            return {
                'current_status': current_status,
                'total_historical': total_historical,
                'historical_pass_count': historical_pass,
                'historical_fail_count': historical_fail,
                'historical_pass_rate': round(historical_pass_rate, 3),
                'historical_fail_rate': round(historical_fail_rate, 3),
                'historical_statuses': historical_statuses,
                'recent_trend': recent_trend,
                'recent_5_statuses': recent_5_statuses,
                'last_pass_execution_ago': last_pass_idx,
                'last_fail_execution_ago': last_fail_idx,
            }

        except Exception as e:
            self.logger.error(f"Failed to calculate statistics: {e}")
            return {
                'error': str(e),
                'current_status': current_result.get('status', 'UNKNOWN'),
            }

    def analyze_historical_comparison(
        self,
        service: str,
        test: str,
        current_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Perform full historical comparison for a test.

        Args:
            service: Service name
            test: Test name
            current_result: Current execution result

        Returns:
            Dictionary with complete historical analysis or None if error
        """
        try:
            self.logger.info(f"Analyzing historical data for {service}/{test}")

            # Get historical data
            historical = self.get_historical_data(service, test, limit=10)
            if historical is None:
                return None

            # Calculate statistics
            stats = self.calculate_statistics(current_result, historical)

            return {
                'service': service,
                'test': test,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'historical_analysis': stats,
                'historical_executions': historical,
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze historical comparison: {e}")
            return None
