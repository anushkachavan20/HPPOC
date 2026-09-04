import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import AGGREGATION_WINDOW_MINUTES, DRY_RUN, LOG_LEVEL
from logger import setup_logger

from modules.ingestion.k6_result_parser import K6ResultParser
from modules.ingestion.datadog_ingestion import DatadogIngestion

from modules.datadog.datadog_client import DatadogClient

from modules.analysis.historical_analyzer import HistoricalAnalyzer
from modules.analysis.failure_classifier import FailureClassifier

from modules.jira.jira_client import JiraClient
from modules.jira.jira_correlation import JiraCorrelation

from modules.reporting.result_aggregator import ResultAggregator
from modules.reporting.summary_generator import SummaryGenerator
from modules.reporting.datadog_publisher import DatadogPublisher


logger = logging.getLogger(__name__)


class APIAnalysisEngine:
    """
    Main orchestration engine for the API test analysis POC.

    Pipeline:

        k6 results
            ↓
        Parse results
            ↓
        Datadog ingestion
            ↓
        Historical analysis
            ↓
        Failure classification
            ↓
        Jira correlation
            ↓
        Reporting
            ↓
        Datadog publishing

    Ollama / LLM analysis is intentionally disabled for the
    current POC phase.
    """

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

        logger.info("Initializing API Analysis Engine")

        # --------------------------------------------------------------
        # k6
        # --------------------------------------------------------------

        self.k6_parser = K6ResultParser()

        # --------------------------------------------------------------
        # Datadog
        # --------------------------------------------------------------

        self.datadog_client = DatadogClient()

        self.datadog_ingestion = DatadogIngestion(
            self.datadog_client,
            dry_run=self.dry_run,
        )

        self.historical_analyzer = HistoricalAnalyzer(
            self.datadog_client
        )

        # --------------------------------------------------------------
        # Failure classification
        # --------------------------------------------------------------

        self.failure_classifier = FailureClassifier()

        # --------------------------------------------------------------
        # Jira
        # --------------------------------------------------------------

        self.jira_client = JiraClient()

        self.jira_correlation = JiraCorrelation(
            self.jira_client
        )

        # --------------------------------------------------------------
        # Reporting
        # --------------------------------------------------------------

        self.result_aggregator = ResultAggregator()

        self.summary_generator = SummaryGenerator()

        self.datadog_publisher = DatadogPublisher(
            self.datadog_client,
            dry_run=self.dry_run,
        )

        logger.info("Analysis engine initialized")

    # ------------------------------------------------------------------
    # Main Analysis Pipeline
    # ------------------------------------------------------------------

    def run_analysis(
        self,
        k6_result_file: str,
        execution_id: Optional[str] = None,
        window_id: Optional[str] = None,
    ) -> bool:
        """
        Execute the complete API test analysis pipeline.

        Args:
            k6_result_file:
                Path to the k6 JSON/JSONL result file.

            execution_id:
                Optional execution ID. In GitHub Actions this is normally
                passed as gh_run_<github_run_id>.

            window_id:
                Shared UTC aggregation window ID for split workflows.

        Returns:
            True if the analysis completed successfully.
            False if a fatal error occurred.
        """

        logger.info("=" * 80)
        logger.info("Starting API Test Analysis")
        logger.info("=" * 80)

        try:
            # ==========================================================
            # STEP 1 - Parse k6 Results
            # ==========================================================

            logger.info(
                "\n[Step 1/8] Parsing k6 test results..."
            )

            k6_execution = self.k6_parser.parse_k6_json(
                k6_result_file,
                execution_id=execution_id,
            )

            logger.info(
                "Parsed %d test results (ID: %s)",
                len(k6_execution.results),
                k6_execution.k6_meta.execution_id,
            )

            if not k6_execution.results:
                logger.error(
                    "No test results were found in the k6 result file"
                )
                return False

            # ==========================================================
            # STEP 2 - Ingest Results into Datadog
            # ==========================================================

            logger.info(
                "\n[Step 2/8] Ingesting results into Datadog..."
            )

            ingestion_result = (
                self.datadog_ingestion.ingest_execution(
                    k6_execution
                )
            )

            logger.info(
                "Datadog ingestion completed: %s",
                ingestion_result,
            )

            # ==========================================================
            # STEP 3 - Query Historical Data
            # ==========================================================

            logger.info(
                "\n[Step 3/8] Querying historical data from Datadog..."
            )

            historical_data = {}

            for test_result in k6_execution.results:
                service = test_result.service.lower()
                test_name = test_result.test_name.lower()

                try:
                    history = (
                        self.historical_analyzer.analyze_test_history(
                            service=service,
                            test=test_name,
                            exclude_execution_id=k6_execution.k6_meta.execution_id,
                        )
                    )

                    historical_data[
                        f"{service}:{test_name}"
                    ] = history

                except Exception as exc:
                    logger.warning(
                        "Historical analysis failed for %s/%s: %s",
                        service,
                        test_name,
                        exc,
                    )

                    historical_data[
                        f"{service}:{test_name}"
                    ] = None

            logger.info(
                "Retrieved historical data for %d tests",
                len(historical_data),
            )

            # ==========================================================
            # STEP 4 - Classify Failure Patterns
            # ==========================================================

            logger.info(
                "\n[Step 4/8] Classifying failure patterns..."
            )

            classifications = {}

            for test_result in k6_execution.results:
                service = test_result.service.lower()
                test_name = test_result.test_name.lower()

                key = f"{service}:{test_name}"

                history = historical_data.get(key)

                try:
                    classification = (
                        self.failure_classifier.classify(
                            current_result=test_result,
                            historical_data=history,
                        )
                    )

                    classifications[key] = classification

                except Exception as exc:
                    logger.warning(
                        "Failure classification failed for %s/%s: %s",
                        service,
                        test_name,
                        exc,
                    )

                    classifications[key] = None

            logger.info(
                "Classified %d test results",
                len(classifications),
            )

            # ==========================================================
            # STEP 5 - Correlate with Jira
            # ==========================================================

            logger.info(
                "\n[Step 5/8] Correlating failure patterns with Jira..."
            )

            jira_results = {}

            for test_result in k6_execution.results:
                service = test_result.service.lower()
                test_name = test_result.test_name.lower()

                key = f"{service}:{test_name}"

                classification = classifications.get(key)

                try:
                    jira_result = (
                        self.jira_correlation.correlate_failure(
                            test_result=test_result,
                            classification=classification,
                        )
                    )

                    jira_results[key] = jira_result

                except Exception as exc:
                    logger.warning(
                        "Jira correlation failed for %s/%s: %s",
                        service,
                        test_name,
                        exc,
                    )

                    jira_results[key] = None

            logger.info(
                "Correlated %d failures with Jira",
                len(jira_results),
            )

            # ==========================================================
            # STEP 6 - AI Analysis
            # ==========================================================

            logger.info(
                "\n[Step 6/8] AI failure analysis skipped"
            )

            logger.info(
                "Ollama/LLM integration is disabled for the "
                "current POC phase"
            )

            ai_analyses = []

            # ==========================================================
            # STEP 7 - Aggregate Results
            # ==========================================================

            logger.info(
                "\n[Step 7/8] Aggregating analysis results..."
            )

            aggregated_results = (
                self.result_aggregator.aggregate(
                    k6_execution=k6_execution,
                    historical_data=historical_data,
                    classifications=classifications,
                    jira_results=jira_results,
                    ai_analyses=ai_analyses,
                    window_id=window_id or self._current_window_id(),
                )
            )

            logger.info(
                "Aggregated %d analysis results",
                len(aggregated_results),
            )

            # ==========================================================
            # Generate Human-readable Summary
            # ==========================================================

            logger.info(
                "\nGenerating analysis summary..."
            )

            summary = (
                self.summary_generator.generate(
                    aggregated_results
                )
            )

            report_path = Path(__file__).parent / "reports" / "analysis_report.txt"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                summary + "\n",
                encoding="utf-8",
            )
            logger.info("Full analysis report written to %s", report_path)

            results_path = Path(__file__).parent / "reports" / "analysis_results.json"
            results_path.write_text(
                json.dumps(aggregated_results, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            logger.info("Analysis results written to %s", results_path)

            print("\n")
            print("=" * 80)
            print("API TEST ANALYSIS SUMMARY")
            print("=" * 80)
            print(summary)
            print("=" * 80)

            # ==========================================================
            # STEP 8 - Publish Analysis to Datadog
            # ==========================================================

            logger.info(
                "\n[Step 8/8] Publishing analysis results to Datadog..."
            )

            publish_result = (
                self.datadog_publisher.publish(
                    aggregated_results
                )
            )

            logger.info(
                "Datadog publishing completed: %s",
                publish_result,
            )
            print(
                "DATADOG_PUBLISH_RESULT="
                + str(publish_result)
            )

            logger.info("=" * 80)
            logger.info("Analysis Complete!")
            logger.info("=" * 80)

            return True

        except FileNotFoundError as exc:
            logger.error(
                "k6 result file not found: %s",
                exc,
            )
            return False

        except ValueError as exc:
            logger.error(
                "Invalid k6 result data: %s",
                exc,
            )
            return False

        except Exception as exc:
            logger.exception(
                "Fatal error during API analysis: %s",
                exc,
            )
            return False

    @staticmethod
    def _current_window_id() -> str:
        now = datetime.now(timezone.utc)
        window_minute = (
            now.minute // AGGREGATION_WINDOW_MINUTES
        ) * AGGREGATION_WINDOW_MINUTES
        return now.replace(
            minute=window_minute,
            second=0,
            microsecond=0,
        ).strftime("%Y-%m-%dT%H:%MZ")

# ----------------------------------------------------------------------
# Command Line Interface
# ----------------------------------------------------------------------

def parse_arguments():
    """
    Parse command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description=(
            "AI-assisted API test analysis pipeline "
            "using k6, Datadog and Jira"
        )
    )

    parser.add_argument(
        "--k6-result",
        required=True,
        help="Path to the k6 result JSON/JSONL file",
    )

    parser.add_argument(
        "--execution-id",
        required=False,
        default=None,
        help=(
            "Execution ID used to identify this test run. "
            "Example: gh_run_12345"
        ),
    )

    parser.add_argument(
        "--window-id",
        required=False,
        default=None,
        help="Shared UTC aggregation window ID; defaults to the current 30-minute window",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Run without sending data to Datadog. "
            "This overrides the DRY_RUN configuration."
        ),
    )

    return parser.parse_args()


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    """
    Application entry point.
    """

    args = parse_arguments()

    # Configure logging.
    setup_logger(
        log_level=LOG_LEVEL,
    )

    logger.info("=" * 80)
    logger.info("API Test Analysis POC")
    logger.info("=" * 80)

    # CLI --dry-run takes precedence over environment configuration.
    dry_run = args.dry_run or DRY_RUN

    logger.info(
        "Dry run mode: %s",
        dry_run,
    )

    if args.execution_id:
        logger.info(
            "Execution ID: %s",
            args.execution_id,
        )

    engine = APIAnalysisEngine(
        dry_run=dry_run,
    )

    success = engine.run_analysis(
        k6_result_file=args.k6_result,
        execution_id=args.execution_id,
        window_id=args.window_id,
    )

    if success:
        logger.info(
            "Application finished successfully"
        )
        sys.exit(0)

    logger.error(
        "Application finished with errors"
    )
    sys.exit(1)


if __name__ == "__main__":
    main()