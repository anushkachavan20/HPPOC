#!/usr/bin/env python3
"""
Main entry point for the API Test Analysis POC.

Usage:
    python main.py --k6-result <path-to-k6-results.json>
    python main.py --k6-result results.json --dry-run
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from logger import get_logger
from config import DRY_RUN
from modules.ingestion.k6_result_parser import K6ResultParser
from modules.ingestion.datadog_ingestion import DatadogIngestion
from modules.datadog.datadog_client import DatadogClient
from modules.analysis.historical_analyzer import HistoricalAnalyzer
from modules.analysis.failure_classifier import FailureClassifier
from modules.jira.jira_correlation import JiraCorrelation
from modules.jira.jira_client import JiraClient
from modules.ai.ollama_client import OllamaClient
from modules.ai.failure_analyzer import FailureAnalyzer
from modules.reporting.result_aggregator import ResultAggregator
from modules.reporting.summary_generator import SummaryGenerator
from modules.reporting.datadog_publisher import DatadogPublisher

logger = get_logger('main')


class AnalysisEngine:
    """Main analysis engine orchestrator."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize analysis engine.

        Args:
            dry_run: If True, don't send results to Datadog
        """
        self.dry_run = dry_run

        # Initialize clients
        self.datadog_client = DatadogClient()
        self.ollama_client = OllamaClient()
        self.jira_client = JiraClient()  # Real Jira Cloud API

        # Initialize components
        self.k6_parser = K6ResultParser()
        self.datadog_ingestion = DatadogIngestion(self.datadog_client)
        self.historical_analyzer = HistoricalAnalyzer(self.datadog_client)
        self.failure_classifier = FailureClassifier()
        self.jira_correlation = JiraCorrelation(self.jira_client)  # Pass JiraClient
        self.failure_analyzer = FailureAnalyzer(self.ollama_client)
        self.result_aggregator = ResultAggregator()
        self.summary_generator = SummaryGenerator()
        self.datadog_publisher = DatadogPublisher(self.datadog_client)

        logger.info("Analysis engine initialized")

    def run_analysis(self, k6_result_file: str) -> bool:
        """
        Run complete analysis pipeline.

        Args:
            k6_result_file: Path to k6 results JSON file

        Returns:
            True if successful
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting API Test Analysis Pipeline")
            logger.info("=" * 60)

            # Step 1: Parse k6 results
            logger.info("\n[Step 1/8] Parsing k6 test results...")
            k6_result = self.k6_parser.parse_k6_json(k6_result_file)
            if not k6_result:
                logger.error("Failed to parse k6 results")
                return False

            execution_id = k6_result.k6_meta.execution_id
            logger.info(f"Parsed {len(k6_result.results)} test results (ID: {execution_id})")

            # Normalize results
            normalized_results = self.k6_parser.normalize_results(k6_result)

            # Step 2: Ingest into Datadog
            logger.info("\n[Step 2/8] Ingesting results into Datadog...")
            success = self.datadog_ingestion.ingest_test_results(
                normalized_results, execution_id, dry_run=self.dry_run
            )
            if not success:
                logger.error("Failed to ingest results")
                return False

            # Step 3: Retrieve historical data
            logger.info("\n[Step 3/8] Querying historical data from Datadog...")
            historical_analyses = []
            for test_result in normalized_results:
                service = test_result['service']
                test = test_result['test']
                historical = self.historical_analyzer.analyze_historical_comparison(
                    service, test, test_result
                )
                if historical:
                    historical_analyses.append(historical)

            logger.info(f"Retrieved historical data for {len(historical_analyses)} tests")

            # Step 4: Classify failures
            logger.info("\n[Step 4/8] Classifying failure patterns...")
            historical_data = {
                f"{h['service']}/{h['test']}": h
                for h in historical_analyses
            }
            classifications = self.failure_classifier.classify_batch(
                normalized_results, historical_data
            )
            logger.info(f"Classified {len(classifications)} failures")

            # Step 5: Correlate with Jira
            logger.info("\n[Step 5/8] Correlating with Jira issues...")
            jira_correlations = []
            for classification in classifications:
                jira = self.jira_correlation.correlate_failure(
                    service=classification['service'],
                    test=classification['test'],
                    failure_pattern=classification['failure_pattern'],
                )
                jira_correlations.append(jira)
            logger.info(f"Correlated {len(jira_correlations)} failures with Jira")

            # Step 6: AI failure analysis (only for failed tests)
            logger.info("\n[Step 6/8] Analyzing failure reasons with AI...")
            ai_analyses = []
            failed_results = [r for r in normalized_results if r['status'] == 'FAIL']

            if failed_results:
                # Check Ollama health
                if not self.ollama_client.health_check():
                    logger.warning("Ollama is not accessible - skipping AI analysis")
                else:
                    for failure in failed_results:
                        ai_analysis = self.failure_analyzer.analyze_failure(
                            service=failure['service'],
                            test=failure['test'],
                            http_status=failure['http_status'],
                            error_message=failure['error_message'],
                            response_body=failure.get('response_body'),
                        )
                        ai_analyses.append({
                            'service': failure['service'],
                            'test': failure['test'],
                            **ai_analysis
                        })

            logger.info(f"Performed AI analysis on {len(ai_analyses)} failures")

            # Step 7: Aggregate results
            logger.info("\n[Step 7/8] Aggregating analysis results...")
            aggregated = self.result_aggregator.aggregate_analysis(
                normalized_results,
                historical_analyses,
                classifications,
                jira_correlations,
                ai_analyses
            )
            logger.info(f"Aggregated results for {len(aggregated)} tests")

            # Step 8: Generate summary and publish
            logger.info("\n[Step 8/8] Publishing results and generating summary...")
            summary = self.summary_generator.generate_detailed_summary(aggregated)
            logger.info("\n" + summary)

            # Publish to Datadog
            success = self.datadog_publisher.publish_analysis(
                aggregated, dry_run=self.dry_run
            )
            if not success:
                logger.warning("Failed to publish analysis results")

            logger.info("\n" + "=" * 60)
            logger.info("Analysis Complete!")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"Unexpected error in analysis pipeline: {e}", exc_info=True)
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='API Test Result Analysis POC'
    )
    parser.add_argument(
        '--k6-result',
        required=True,
        help='Path to k6 test results JSON file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without sending results to Datadog'
    )
    parser.add_argument(
        '--execution-id',
        help='Override execution ID (default: from k6 meta)'
    )

    args = parser.parse_args()

    # Validate input file
    if not Path(args.k6_result).exists():
        logger.error(f"K6 result file not found: {args.k6_result}")
        sys.exit(1)

    # Run analysis
    engine = AnalysisEngine(dry_run=args.dry_run or DRY_RUN)
    success = engine.run_analysis(args.k6_result)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
