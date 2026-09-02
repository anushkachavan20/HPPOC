"""
Jira Client - Real Jira Cloud API integration.

Uses Jira Cloud REST API v3 with API-token authentication.
"""

import requests
from typing import Any, Dict, Optional, List

from logger import get_logger
from config import (
    JIRA_API_URL,
    JIRA_API_TOKEN,
    JIRA_EMAIL,
    DRY_RUN,
)

logger = get_logger("jira.client")


class JiraClient:
    """Client for Jira Cloud REST API."""

    def __init__(
        self,
        jira_url: str = JIRA_API_URL,
        email: str = JIRA_EMAIL,
        api_token: str = JIRA_API_TOKEN,
    ):
        """
        Initialize Jira Cloud client.

        Args:
            jira_url: Jira instance URL.
            email: Email associated with Jira account.
            api_token: Jira API token.
        """

        self.jira_url = jira_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.logger = logger

        self.session = requests.Session()

        # Jira Cloud API-token authentication
        self.session.auth = (
            email,
            api_token,
        )

        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    # ========================================================
    # Health Check
    # ========================================================

    def health_check(self) -> bool:
        """
        Check whether Jira Cloud authentication works.

        Returns:
            True if Jira is accessible.
        """

        try:

            url = (
                f"{self.jira_url}"
                "/rest/api/3/myself"
            )

            response = self.session.get(
                url,
                timeout=10,
            )

            if response.status_code == 200:

                user = response.json()

                self.logger.info(
                    "Connected to Jira as: %s",
                    user.get("displayName"),
                )

                return True

            if response.status_code == 401:

                self.logger.error(
                    "Jira authentication failed. "
                    "Check JIRA_EMAIL and JIRA_API_TOKEN."
                )

                return False

            self.logger.error(
                "Jira health check failed: %s - %s",
                response.status_code,
                response.text[:500],
            )

            return False

        except requests.RequestException as exc:

            self.logger.error(
                "Jira health check error: %s",
                exc,
            )

            return False

    # ========================================================
    # Search Issues
    # ========================================================

    def search_issues(
        self,
        jql: str,
        max_results: int = 10,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search Jira issues using JQL.

        Uses Jira Cloud's enhanced JQL search endpoint.

        Args:
            jql:
                Jira Query Language query.

            max_results:
                Maximum number of issues to return.

        Returns:
            List of Jira issues or None if the request fails.
        """

        try:

            # ------------------------------------------------
            # Jira Cloud enhanced JQL search endpoint
            # ------------------------------------------------

            url = (
                f"{self.jira_url}"
                "/rest/api/3/search/jql"
            )

            params = {
                "jql": jql,
                "maxResults": max_results,
                "fields": "key,summary,status,priority,labels",
            }

            response = self.session.get(
                url,
                params=params,
                timeout=30,
            )

            if response.status_code == 200:

                data = response.json()

                issues = data.get(
                    "issues",
                    [],
                )

                self.logger.debug(
                    "Found %d Jira issues matching JQL",
                    len(issues),
                )

                return issues

            # ------------------------------------------------
            # Authentication error
            # ------------------------------------------------

            if response.status_code == 401:

                self.logger.error(
                    "Jira authentication failed while "
                    "searching issues."
                )

                return None

            # ------------------------------------------------
            # Permission error
            # ------------------------------------------------

            if response.status_code == 403:

                self.logger.error(
                    "Jira permission denied while searching issues. "
                    "Check whether the Jira account can browse "
                    "the requested project."
                )

                return None

            # ------------------------------------------------
            # Bad JQL
            # ------------------------------------------------

            if response.status_code == 400:

                self.logger.error(
                    "Invalid Jira JQL: %s",
                    response.text[:1000],
                )

                return None

            # ------------------------------------------------
            # Endpoint unavailable
            # ------------------------------------------------

            if response.status_code == 410:

                self.logger.error(
                    "Jira search endpoint returned 410 Gone. "
                    "The Jira Cloud search API may require the "
                    "enhanced JQL endpoint."
                )

                return None

            # ------------------------------------------------
            # Other errors
            # ------------------------------------------------

            self.logger.error(
                "Jira search failed: %s - %s",
                response.status_code,
                response.text[:1000],
            )

            return None

        except requests.RequestException as exc:

            self.logger.error(
                "Error searching Jira: %s",
                exc,
            )

            return None

    # ========================================================
    # Find Issue By Summary
    # ========================================================

    def find_issue_by_summary(
        self,
        project_key: str,
        keywords: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first Jira issue matching summary keywords.
        """

        try:

            if not keywords:
                return None

            keyword_conditions = " OR ".join(
                [
                    f'summary ~ "{keyword}"'
                    for keyword in keywords
                ]
            )

            jql = (
                f"project = {project_key} "
                f"AND ({keyword_conditions})"
            )

            issues = self.search_issues(
                jql,
                max_results=5,
            )

            if issues:
                return issues[0]

            return None

        except Exception as exc:

            self.logger.error(
                "Error finding issue by summary: %s",
                exc,
            )

            return None

    # ========================================================
    # Find Issue By Label
    # ========================================================

    def find_issue_by_label(
        self,
        project_key: str,
        label: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the first Jira issue matching a label.
        """

        try:

            jql = (
                f"project = {project_key} "
                f"AND labels = {label}"
            )

            issues = self.search_issues(
                jql,
                max_results=5,
            )

            if issues:
                return issues[0]

            return None

        except Exception as exc:

            self.logger.error(
                "Error finding issue by label: %s",
                exc,
            )

            return None

    # ========================================================
    # Create Issue
    # ========================================================

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Create a Jira issue.

        Returns:
            Jira issue key or None.
        """

        try:

            if DRY_RUN:

                self.logger.info(
                    "[DRY RUN] Would create Jira issue: %s",
                    summary,
                )

                return None

            url = (
                f"{self.jira_url}"
                "/rest/api/3/issue"
            )

            payload = {
                "fields": {
                    "project": {
                        "key": project_key,
                    },
                    "summary": summary,
                    "description": {
                        "version": 1,
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description,
                                    }
                                ],
                            }
                        ],
                    },
                    "issuetype": {
                        "name": issue_type,
                    },
                }
            }

            if labels:
                payload["fields"]["labels"] = labels

            response = self.session.post(
                url,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 201):

                issue_key = response.json().get(
                    "key"
                )

                self.logger.info(
                    "Created Jira issue: %s",
                    issue_key,
                )

                return issue_key

            self.logger.error(
                "Failed to create Jira issue: %s - %s",
                response.status_code,
                response.text[:1000],
            )

            return None

        except requests.RequestException as exc:

            self.logger.error(
                "Error creating Jira issue: %s",
                exc,
            )

            return None

    # ========================================================
    # Update Issue
    # ========================================================

    def update_issue(
        self,
        issue_key: str,
        **fields,
    ) -> bool:
        """
        Update a Jira issue.
        """

        try:

            if DRY_RUN:

                self.logger.info(
                    "[DRY RUN] Would update Jira issue: %s",
                    issue_key,
                )

                return True

            url = (
                f"{self.jira_url}"
                f"/rest/api/3/issue/{issue_key}"
            )

            payload = {
                "fields": fields
            }

            response = self.session.put(
                url,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 204):

                self.logger.debug(
                    "Updated Jira issue: %s",
                    issue_key,
                )

                return True

            self.logger.error(
                "Failed to update Jira issue %s: %s - %s",
                issue_key,
                response.status_code,
                response.text[:1000],
            )

            return False

        except requests.RequestException as exc:

            self.logger.error(
                "Error updating Jira issue %s: %s",
                issue_key,
                exc,
            )

            return False

    # ========================================================
    # Get Issue
    # ========================================================

    def get_issue(
        self,
        issue_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a Jira issue by key.
        """

        try:

            url = (
                f"{self.jira_url}"
                f"/rest/api/3/issue/{issue_key}"
            )

            params = {
                "fields": (
                    "key,summary,status,"
                    "priority,labels,description"
                )
            }

            response = self.session.get(
                url,
                params=params,
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()

            self.logger.error(
                "Failed to get Jira issue %s: %s - %s",
                issue_key,
                response.status_code,
                response.text[:500],
            )

            return None

        except requests.RequestException as exc:

            self.logger.error(
                "Error getting Jira issue %s: %s",
                issue_key,
                exc,
            )

            return None

    # ========================================================
    # Format Issue
    # ========================================================

    def format_issue(
        self,
        issue: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert raw Jira issue data into a simpler structure.
        """

        try:

            fields = issue.get(
                "fields",
                {},
            )

            status = fields.get(
                "status",
                {},
            )

            priority = fields.get(
                "priority",
                {},
            )

            return {
                "jira_id": issue.get(
                    "key"
                ),

                "summary": fields.get(
                    "summary"
                ),

                "status": (
                    status.get("name")
                    if isinstance(status, dict)
                    else str(status)
                ),

                "priority": (
                    priority.get("name")
                    if isinstance(priority, dict)
                    else str(priority)
                ),

                "labels": fields.get(
                    "labels",
                    [],
                ),

                "url": (
                    f"{self.jira_url}"
                    f"/browse/{issue.get('key')}"
                ),
            }

        except Exception as exc:

            self.logger.error(
                "Error formatting Jira issue: %s",
                exc,
            )

            return {}
