"""
Jira Client - Real Jira Cloud API integration.
Uses personal Jira instance with API token authentication.
"""

import requests
import json
from typing import Any, Dict, Optional, List
from logger import get_logger
from config import JIRA_API_URL, JIRA_API_TOKEN, JIRA_EMAIL, DRY_RUN

logger = get_logger('jira.client')


class JiraClient:
    """Client for real Jira Cloud API."""

    def __init__(
        self,
        jira_url: str = JIRA_API_URL,
        email: str = JIRA_EMAIL,
        api_token: str = JIRA_API_TOKEN,
    ):
        """
        Initialize Jira Cloud client.

        Args:
            jira_url: Jira instance URL (e.g., https://yourname.atlassian.net)
            email: Email associated with Jira account
            api_token: API token from Jira (Settings → API Tokens)
        """
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.logger = logger
        self.session = requests.Session()

        # Set up basic auth with email:token
        self.session.auth = (email, api_token)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def health_check(self) -> bool:
        """
        Check if Jira API is accessible.

        Returns:
            True if Jira is accessible
        """
        try:
            url = f"{self.jira_url}/rest/api/3/myself"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                user = response.json()
                self.logger.info(f"Connected to Jira as: {user.get('displayName')}")
                return True
            elif response.status_code == 401:
                self.logger.error("Jira authentication failed - check email and API token")
                return False
            else:
                self.logger.error(f"Jira health check failed: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Jira health check error: {e}")
            return False

    def search_issues(
        self,
        jql: str,
        max_results: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for Jira issues using JQL (Jira Query Language).

        Args:
            jql: JQL query (e.g., 'project = PROJ AND summary ~ "customer"')
            max_results: Maximum results to return

        Returns:
            List of issues or None if error
        """
        try:
            url = f"{self.jira_url}/rest/api/3/search"
            params = {
                'jql': jql,
                'maxResults': max_results,
                'fields': ['key', 'summary', 'status', 'priority', 'labels']
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                issues = data.get('issues', [])
                self.logger.debug(f"Found {len(issues)} issues matching JQL")
                return issues
            else:
                self.logger.error(f"Jira search failed: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error searching Jira: {e}")
            return None

    def find_issue_by_summary(
        self,
        project_key: str,
        keywords: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Find Jira issue by keywords in summary.

        Args:
            project_key: Jira project key (e.g., 'PROJ')
            keywords: Keywords to search for in summary

        Returns:
            First matching issue or None
        """
        try:
            # Build JQL query
            keyword_conditions = ' OR '.join([f'summary ~ "{kw}"' for kw in keywords])
            jql = f'project = {project_key} AND ({keyword_conditions})'

            issues = self.search_issues(jql, max_results=5)

            if issues and len(issues) > 0:
                return issues[0]  # Return first match
            return None

        except Exception as e:
            self.logger.error(f"Error finding issue by summary: {e}")
            return None

    def find_issue_by_label(
        self,
        project_key: str,
        label: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find Jira issue by label.

        Args:
            project_key: Jira project key
            label: Label to search for

        Returns:
            First matching issue or None
        """
        try:
            jql = f'project = {project_key} AND labels = {label}'
            issues = self.search_issues(jql, max_results=5)

            if issues and len(issues) > 0:
                return issues[0]
            return None

        except Exception as e:
            self.logger.error(f"Error finding issue by label: {e}")
            return None

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = 'Bug',
        labels: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Create a new Jira issue.

        Args:
            project_key: Jira project key
            summary: Issue summary/title
            description: Issue description
            issue_type: Type of issue (Bug, Task, etc.)
            labels: Optional labels

        Returns:
            Issue key (e.g., 'PROJ-123') or None if error
        """
        try:
            if DRY_RUN:
                self.logger.info(f"[DRY RUN] Would create issue: {summary}")
                return None

            url = f"{self.jira_url}/rest/api/3/issue"

            payload = {
                'fields': {
                    'project': {'key': project_key},
                    'summary': summary,
                    'description': {
                        'version': 1,
                        'type': 'doc',
                        'content': [
                            {
                                'type': 'paragraph',
                                'content': [
                                    {'type': 'text', 'text': description}
                                ]
                            }
                        ]
                    },
                    'issuetype': {'name': issue_type},
                }
            }

            if labels:
                payload['fields']['labels'] = labels

            response = self.session.post(url, json=payload, timeout=30)

            if response.status_code in [200, 201]:
                issue_key = response.json().get('key')
                self.logger.info(f"Created Jira issue: {issue_key}")
                return issue_key
            else:
                self.logger.error(f"Failed to create issue: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error creating issue: {e}")
            return None

    def update_issue(
        self,
        issue_key: str,
        **fields
    ) -> bool:
        """
        Update a Jira issue.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
            **fields: Fields to update (e.g., summary='New summary')

        Returns:
            True if successful
        """
        try:
            if DRY_RUN:
                self.logger.info(f"[DRY RUN] Would update issue: {issue_key}")
                return True

            url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"

            # Map common field names to Jira API format
            payload = {'fields': fields}

            response = self.session.put(url, json=payload, timeout=30)

            if response.status_code in [200, 204]:
                self.logger.debug(f"Updated issue: {issue_key}")
                return True
            else:
                self.logger.error(f"Failed to update issue: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating issue: {e}")
            return False

    def get_issue(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific Jira issue.

        Args:
            issue_key: Issue key (e.g., 'PROJ-123')

        Returns:
            Issue data or None if error
        """
        try:
            url = f"{self.jira_url}/rest/api/3/issue/{issue_key}"
            params = {
                'fields': ['key', 'summary', 'status', 'priority', 'labels', 'description']
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Failed to get issue: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Error getting issue: {e}")
            return None

    def format_issue(self, issue: Dict[str, Any]) -> Dict[str, str]:
        """
        Format raw Jira issue data for display.

        Args:
            issue: Raw issue data from API

        Returns:
            Formatted issue dictionary
        """
        try:
            fields = issue.get('fields', {})
            status = fields.get('status', {})
            priority = fields.get('priority', {})

            return {
                'jira_id': issue.get('key'),
                'summary': fields.get('summary'),
                'status': status.get('name') if isinstance(status, dict) else str(status),
                'priority': priority.get('name') if isinstance(priority, dict) else str(priority),
                'labels': fields.get('labels', []),
                'url': f"{self.jira_url}/browse/{issue.get('key')}",
            }

        except Exception as e:
            self.logger.error(f"Error formatting issue: {e}")
            return {}
