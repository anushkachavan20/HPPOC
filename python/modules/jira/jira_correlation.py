"""
Jira Correlation - Match failures to Jira issues using real Jira Cloud API.
"""

from typing import Any, Dict, Optional, List
from logger import get_logger
from config import JIRA_PROJECT_KEY
from .jira_client import JiraClient

logger = get_logger('jira.correlation')


class JiraCorrelation:
    """Correlates test failures with Jira issues using real Jira API."""

    def __init__(self, jira_client: Optional[JiraClient] = None):
        """
        Initialize Jira correlation.

        Args:
            jira_client: JiraClient instance (or None to create new)
        """
        self.jira_client = jira_client or JiraClient()
        self.logger = logger
        self.project_key = JIRA_PROJECT_KEY

        # Check Jira connectivity
        if not self.jira_client.health_check():
            self.logger.warning("Jira API not accessible - correlation will be limited")

    def find_matching_issue(
        self,
        service: str,
        test: str,
        failure_category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching Jira issue using real Jira API.

        Args:
            service: Service name
            test: Test name
            failure_category: Optional failure category for more precise matching

        Returns:
            Matching Jira issue or None
        """
        try:
            # Build search keywords
            keywords = [
                service.lower(),
                test.lower(),
            ]

            if failure_category:
                keywords.append(failure_category.lower())

            # Search for issue in Jira
            issue = self.jira_client.find_issue_by_summary(
                self.project_key,
                keywords
            )

            if issue:
                return self.jira_client.format_issue(issue)

            return None

        except Exception as e:
            self.logger.error(f"Error finding matching Jira issue: {e}")
            return None

    def correlate_failure(
        self,
        service: str,
        test: str,
        failure_pattern: str,
        failure_category: Optional[str] = None,
        error_message: Optional[str] = None,
        create_if_missing: bool = False
    ) -> Dict[str, Any]:
        """
        Correlate a failure with Jira issues.

        Args:
            service: Service name
            test: Test name
            failure_pattern: Failure pattern classification
            failure_category: Optional AI-detected failure category
            error_message: Error message from test
            create_if_missing: If True, create issue if not found (requires permissions)

        Returns:
            Correlation result dictionary
        """
        try:
            # Only correlate recurring failures (non-"Healthy" and non-"New Failure")
            if failure_pattern not in ['Persistent Failure', 'Flaky Failure', 'Resolved Failure']:
                return {
                    'jira_found': False,
                    'jira_id': None,
                    'jira_status': None,
                    'jira_summary': None,
                    'recommendation': f"No Jira correlation for {failure_pattern}",
                    'reason': 'Not a recurring failure',
                }

            # Search for matching issue
            issue = self.find_matching_issue(service, test, failure_category)

            if issue:
                return {
                    'jira_found': True,
                    'jira_id': issue.get('jira_id'),
                    'jira_status': issue.get('status'),
                    'jira_summary': issue.get('summary'),
                    'jira_url': issue.get('url'),
                    'recommendation': f"Existing Jira issue found: {issue.get('jira_id')}",
                    'reason': 'Matching issue in Jira',
                }

            # Optionally create new issue if not found
            if create_if_missing:
                summary = f"{service}/{test} - {failure_pattern}"
                description = f"Failure Pattern: {failure_pattern}\n"
                description += f"Service: {service}\n"
                description += f"Test: {test}\n"

                if failure_category:
                    description += f"Category: {failure_category}\n"

                if error_message:
                    description += f"\nError: {error_message}\n"

                labels = ['test-automation', 'api-test', service.lower()]

                issue_key = self.jira_client.create_issue(
                    project_key=self.project_key,
                    summary=summary,
                    description=description,
                    issue_type='Bug',
                    labels=labels
                )

                if issue_key:
                    return {
                        'jira_found': True,
                        'jira_id': issue_key,
                        'jira_status': 'To Do',
                        'jira_summary': summary,
                        'recommendation': f"Created new Jira issue: {issue_key}",
                        'reason': 'Issue auto-created',
                    }

            return {
                'jira_found': False,
                'jira_id': None,
                'jira_status': None,
                'jira_summary': None,
                'recommendation': f"No Jira issue found for {service}/{test}. Check project settings.",
                'reason': 'No matching issue in Jira',
            }

        except Exception as e:
            self.logger.error(f"Error correlating failure: {e}")
            return {
                'jira_found': False,
                'error': str(e),
            }
