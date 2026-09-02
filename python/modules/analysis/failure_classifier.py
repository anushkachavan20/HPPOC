"""
Failure Classifier - Classify failure patterns using deterministic rules.
"""

from typing import Any, Dict, Optional
from logger import get_logger
from .classification_rules import classify_failure_pattern

logger = get_logger('analysis.classifier')


class FailureClassifier:
    """Classifies failure patterns using deterministic rules."""

    def __init__(self):
        self.logger = logger

    def classify_test_result(
        self,
        service: str,
        test: str,
        current_status: str,
        historical_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Classify failure pattern for a test result.

        Args:
            service: Service name
            test: Test name
            current_status: Current execution status (PASS/FAIL)
            historical_analysis: Output from HistoricalAnalyzer

        Returns:
            Dictionary with classification result
        """
        try:
            # Extract historical statuses
            historical_statuses = historical_analysis.get('historical_analysis', {}).get(
                'historical_statuses', []
            )

            # Reverse for most-recent-first order (as expected by classifier)
            historical_statuses_rev = list(reversed(historical_statuses))

            # Classify
            classification = classify_failure_pattern(current_status, historical_statuses_rev)

            result = {
                'service': service,
                'test': test,
                'current_status': current_status,
                'failure_pattern': classification.pattern,
                'failure_percentage': round(classification.failure_percentage * 100, 1),
                'pass_count': classification.pass_count,
                'fail_count': classification.fail_count,
                'confidence': round(classification.confidence, 2),
                'reasoning': classification.reasoning,
            }

            self.logger.info(
                f"{service}/{test}: {classification.pattern} "
                f"(confidence: {classification.confidence*100:.0f}%)"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to classify failure pattern: {e}")
            return {
                'service': service,
                'test': test,
                'current_status': current_status,
                'failure_pattern': 'Unknown',
                'error': str(e),
            }

    def classify_batch(
        self,
        results: list[Dict[str, Any]],
        historical_data: Dict[str, Dict[str, Any]]
    ) -> list[Dict[str, Any]]:
        """
        Classify multiple test results.

        Args:
            results: List of current test results
            historical_data: Historical analysis data keyed by service/test

        Returns:
            List of classification results
        """
        classifications = []

        for result in results:
            service = result.get('service')
            test = result.get('test')
            status = result.get('status')

            # Get historical data for this test
            key = f"{service}/{test}"
            historical = historical_data.get(key, {})

            # Classify
            classification = self.classify_test_result(
                service, test, status, historical
            )
            classifications.append(classification)

        return classifications
