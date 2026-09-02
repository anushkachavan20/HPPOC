"""
Failure Analyzer - AI-powered failure reason detection using Ollama.
"""

import json
import re
from typing import Any, Dict, Optional, List
from logger import get_logger
from config import AI_FAILURE_CATEGORIES

logger = get_logger('ai.failure_analyzer')


class FailureAnalyzer:
    """Analyzes failures using local LLM to detect likely reasons."""

    def __init__(self, ollama_client):
        """
        Initialize failure analyzer.

        Args:
            ollama_client: Instance of OllamaClient
        """
        self.ollama_client = ollama_client
        self.logger = logger

    def _build_prompt(
        self,
        service: str,
        test: str,
        http_status: int,
        error_message: str,
        response_body: Optional[str] = None,
        k6_logs: Optional[str] = None,
        historical_failures: Optional[List[str]] = None
    ) -> str:
        """
        Build structured prompt for LLM analysis.

        Args:
            service: Service name
            test: Test name
            http_status: HTTP status code
            error_message: Error message
            response_body: Response body (truncated)
            k6_logs: k6 execution logs
            historical_failures: List of previous failure reasons

        Returns:
            Formatted prompt for LLM
        """

        prompt = f"""Analyze this API test failure and identify the most likely failure reason.

Service: {service}
Test: {test}
HTTP Status: {http_status}
Error Message: {error_message}

Response Body (truncated):
{response_body or "No response body"}

K6 Logs:
{k6_logs or "No logs available"}

"""

        if historical_failures:
            prompt += f"""Historical Failure Patterns:
{chr(10).join(f"- {f}" for f in historical_failures[:3])}

"""

        prompt += f"""Based on the information above, provide your analysis in the following JSON format:
{{
  "failure_reason": "Brief explanation of the failure",
  "failure_category": "One of: {', '.join(AI_FAILURE_CATEGORIES)}",
  "evidence": "Evidence from logs that supports this conclusion",
  "confidence": "High/Medium/Low",
  "recommendation": "Suggested investigation or fix"
}}

If there is insufficient evidence, respond with:
{{"failure_reason": "Unknown / Insufficient evidence", "failure_category": "Unknown", "evidence": "", "confidence": "Low"}}

Respond with ONLY the JSON object, no other text."""

        return prompt

    def analyze_failure(
        self,
        service: str,
        test: str,
        http_status: int,
        error_message: str,
        response_body: Optional[str] = None,
        k6_logs: Optional[str] = None,
        historical_failures: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a failed test using LLM.

        Args:
            service: Service name
            test: Test name
            http_status: HTTP status code
            error_message: Error message
            response_body: Response body
            k6_logs: K6 logs
            historical_failures: Previous failure reasons

        Returns:
            Dictionary with failure analysis
        """
        try:
            # Build prompt
            prompt = self._build_prompt(
                service, test, http_status, error_message,
                response_body, k6_logs, historical_failures
            )

            # Get response from LLM
            response = self.ollama_client.generate_response(prompt)

            if not response:
                return self._default_analysis(
                    service, test, error_message, http_status
                )

            # Parse JSON response
            analysis = self._parse_response(response)

            if not analysis:
                return self._default_analysis(
                    service, test, error_message, http_status
                )

            # Validate and sanitize
            analysis = self._validate_analysis(analysis)

            self.logger.info(
                f"AI Analysis for {service}/{test}: "
                f"{analysis.get('failure_category')} "
                f"({analysis.get('confidence')})"
            )

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing failure: {e}")
            return self._default_analysis(
                service, test, error_message, http_status
            )

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response as JSON.

        Args:
            response: LLM response text

        Returns:
            Parsed JSON or None
        """
        try:
            # Try to extract JSON from response
            # In case LLM adds surrounding text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                return json.loads(response)
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse LLM response as JSON: {response[:100]}")
            return None

    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize analysis output.

        Args:
            analysis: Raw analysis dict from LLM

        Returns:
            Validated analysis dict
        """
        # Ensure required fields
        if 'failure_reason' not in analysis:
            analysis['failure_reason'] = 'Unknown'

        if 'failure_category' not in analysis:
            analysis['failure_category'] = 'Unknown'
        elif analysis['failure_category'] not in AI_FAILURE_CATEGORIES:
            # Map to closest category or Unknown
            analysis['failure_category'] = 'Unknown'

        if 'evidence' not in analysis:
            analysis['evidence'] = ''

        if 'confidence' not in analysis:
            analysis['confidence'] = 'Low'
        elif analysis['confidence'] not in ['High', 'Medium', 'Low']:
            analysis['confidence'] = 'Low'

        # Truncate long fields
        analysis['failure_reason'] = analysis['failure_reason'][:500]
        analysis['evidence'] = analysis['evidence'][:1000]

        return analysis

    def _default_analysis(
        self,
        service: str,
        test: str,
        error_message: str,
        http_status: int
    ) -> Dict[str, Any]:
        """
        Generate default analysis based on HTTP status and error message.

        Args:
            service: Service name
            test: Test name
            error_message: Error message
            http_status: HTTP status

        Returns:
            Default analysis dict
        """
        # Simple heuristic-based classification
        category = 'Unknown'
        reason = f"HTTP {http_status}: {error_message}"

        if http_status == 401:
            category = 'Authentication'
            reason = 'Authentication failed (HTTP 401)'
        elif http_status == 403:
            category = 'Authorization'
            reason = 'Authorization failed (HTTP 403)'
        elif http_status == 400:
            category = 'Validation'
            reason = 'Request validation failed (HTTP 400)'
        elif http_status == 408 or 'timeout' in error_message.lower():
            category = 'Timeout'
            reason = 'Request timeout'
        elif http_status == 500:
            category = 'Server Error'
            reason = 'Server error (HTTP 500)'
        elif http_status == 502 or http_status == 503:
            category = 'Dependency'
            reason = f'Service unavailable (HTTP {http_status})'
        elif http_status == 0 or 'connection' in error_message.lower():
            category = 'Network'
            reason = 'Network connection error'

        return {
            'failure_reason': reason,
            'failure_category': category,
            'evidence': error_message,
            'confidence': 'Medium',
            'recommendation': f'Investigate {category} issue for {service}/{test}',
        }

    def analyze_batch(
        self,
        failures: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple failures.

        Args:
            failures: List of failed test results

        Returns:
            List of analysis results
        """
        analyses = []

        for failure in failures:
            analysis = self.analyze_failure(
                service=failure.get('service'),
                test=failure.get('test'),
                http_status=failure.get('http_status'),
                error_message=failure.get('error_message'),
                response_body=failure.get('response_body'),
                k6_logs=failure.get('k6_logs'),
            )
            analyses.append(analysis)

        return analyses
