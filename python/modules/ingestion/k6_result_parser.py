"""
K6 Result Parser - Parse and validate k6 test execution results.
"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field, validator
from logger import get_logger

logger = get_logger('ingestion.k6_parser')


class K6TestResult(BaseModel):
    """Model for a single k6 test result."""
    service: str
    test_name: str
    method: str  # HTTP method
    endpoint: str
    status: str  # PASS or FAIL
    http_status: int
    duration_ms: float
    error: Optional[str] = None
    response_body: Optional[str] = None
    timestamp: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v.upper() not in ['PASS', 'FAIL']:
            raise ValueError(f"Status must be PASS or FAIL, got {v}")
        return v.upper()

    class Config:
        allow_population_by_field_name = True


class K6Metadata(BaseModel):
    """Model for k6 execution metadata."""
    execution_id: str
    scenario: str
    duration: Optional[str] = None
    vus: Optional[int] = None
    timestamp: Optional[str] = None


class K6ExecutionResult(BaseModel):
    """Complete k6 execution result."""
    k6_meta: K6Metadata
    results: List[K6TestResult]


class K6ResultParser:
    """Parser for k6 JSON output."""

    def __init__(self):
        self.logger = logger

    def parse_k6_json(self, json_file: str) -> Optional[K6ExecutionResult]:
        """
        Parse k6 JSON output file.

        Args:
            json_file: Path to k6 results JSON file

        Returns:
            K6ExecutionResult or None if parsing fails
        """
        try:
            json_path = Path(json_file)
            if not json_path.exists():
                self.logger.error(f"K6 result file not found: {json_file}")
                return None

            with open(json_path, 'r') as f:
                data = json.load(f)

            # Validate and construct result object
            result = K6ExecutionResult(**data)
            self.logger.info(
                f"Parsed k6 results: {len(result.results)} test results "
                f"from execution {result.k6_meta.execution_id}"
            )
            return result

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in k6 result file: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to parse k6 results: {e}")
            return None

    def parse_k6_dict(self, data: Dict[str, Any]) -> Optional[K6ExecutionResult]:
        """
        Parse k6 result from dictionary.

        Args:
            data: Dictionary containing k6 results

        Returns:
            K6ExecutionResult or None if parsing fails
        """
        try:
            result = K6ExecutionResult(**data)
            self.logger.info(
                f"Parsed k6 results from dict: {len(result.results)} test results "
                f"from execution {result.k6_meta.execution_id}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Failed to parse k6 results from dict: {e}")
            return None

    def normalize_test_result(
        self,
        test: K6TestResult,
        execution_id: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Normalize a single test result for Datadog ingestion.

        Args:
            test: K6TestResult object
            execution_id: Execution ID
            timestamp: Optional timestamp override

        Returns:
            Normalized result dictionary
        """
        ts = timestamp or test.timestamp or datetime.utcnow().isoformat() + 'Z'

        return {
            'execution_id': execution_id,
            'service': test.service.lower(),
            'test': test.test_name.lower(),
            'method': test.method.upper(),
            'endpoint': test.endpoint,
            'status': test.status.upper(),
            'http_status': test.http_status,
            'duration_ms': test.duration_ms,
            'error_message': test.error or '',
            'response_body': test.response_body or '',
            'timestamp': ts,
        }

    def normalize_results(
        self,
        execution: K6ExecutionResult,
        timestamp: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Normalize all test results for Datadog ingestion.

        Args:
            execution: K6ExecutionResult object
            timestamp: Optional timestamp override

        Returns:
            List of normalized result dictionaries
        """
        normalized = []
        for test in execution.results:
            normalized.append(
                self.normalize_test_result(test, execution.k6_meta.execution_id, timestamp)
            )
        return normalized
