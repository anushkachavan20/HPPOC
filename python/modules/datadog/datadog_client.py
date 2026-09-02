"""
Datadog Client - Wrapper for Datadog API interactions.
"""

import requests
import json
from typing import Any, Dict, List, Optional
from logger import get_logger
from config import DATADOG_API_KEY, DATADOG_APP_KEY, DATADOG_BASE_URL, DRY_RUN

logger = get_logger('datadog.client')


class DatadogClient:
    """Client for interacting with Datadog API."""

    def __init__(self, api_key: str = DATADOG_API_KEY, app_key: str = DATADOG_APP_KEY):
        """
        Initialize Datadog client.

        Args:
            api_key: Datadog API key
            app_key: Datadog app key
        """
        self.api_key = api_key
        self.app_key = app_key
        self.base_url = DATADOG_BASE_URL
        self.logger = logger
        self.session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        """Get headers for Datadog API requests."""
        return {
            'DD-API-KEY': self.api_key,
            'DD-APPLICATION-KEY': self.app_key,
            'Content-Type': 'application/json',
        }

    def send_event(self, event: Dict[str, Any]) -> bool:
        """
        Send an event to Datadog.

        Args:
            event: Event dictionary with title, text, tags, etc.

        Returns:
            True if successful
        """
        try:
            if DRY_RUN:
                self.logger.info(f"[DRY RUN] Would send event: {event['title']}")
                return True

            url = f"{self.base_url}/api/v1/events"
            payload = {
                'title': event.get('title', ''),
                'text': event.get('text', ''),
                'tags': event.get('tags', []),
                'alert_type': event.get('alert_type', 'info'),
            }

            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                self.logger.debug(f"Event sent successfully: {event['title']}")
                return True
            else:
                self.logger.error(
                    f"Failed to send event: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error sending event: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending event: {e}")
            return False

    def send_metrics(self, metrics: List[Dict[str, Any]]) -> bool:
        """
        Send multiple metrics to Datadog.

        Args:
            metrics: List of metric dictionaries

        Returns:
            True if successful
        """
        try:
            if DRY_RUN:
                self.logger.info(f"[DRY RUN] Would send {len(metrics)} metrics")
                return True

            url = f"{self.base_url}/api/v1/series"
            payload = {'series': metrics}

            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            if response.status_code in [200, 201]:
                self.logger.debug(f"Sent {len(metrics)} metrics successfully")
                return True
            else:
                self.logger.error(
                    f"Failed to send metrics: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error sending metrics: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending metrics: {e}")
            return False

    def query_events(
        self,
        query: str,
        page_size: int = 10,
        sort: str = 'timestamp_desc'
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query events from Datadog.

        Args:
            query: Datadog query string (e.g., 'tags:"service:customer"')
            page_size: Number of events to retrieve
            sort: Sort order (e.g., 'timestamp_desc')

        Returns:
            List of events or None if error
        """
        try:
            url = f"{self.base_url}/api/v1/events"
            params = {
                'query': query,
                'page_size': page_size,
                'sort': sort,
            }

            response = self.session.get(
                url,
                headers=self._headers(),
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                self.logger.debug(f"Retrieved {len(events)} events")
                return events
            else:
                self.logger.error(
                    f"Failed to query events: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error querying events: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error querying events: {e}")
            return None

    def query_logs(
        self,
        query: str,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Query logs from Datadog.

        Args:
            query: Datadog logs query
            limit: Maximum number of logs to retrieve

        Returns:
            List of logs or None if error
        """
        try:
            url = f"{self.base_url}/api/v2/logs/events/search"
            payload = {
                'filter': {
                    'query': query,
                },
                'page': {
                    'limit': limit,
                },
                'sort': 'timestamp',
            }

            response = self.session.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                logs = data.get('data', [])
                self.logger.debug(f"Retrieved {len(logs)} logs")
                return logs
            else:
                self.logger.error(
                    f"Failed to query logs: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error querying logs: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error querying logs: {e}")
            return None

    def get_previous_executions(
        self,
        service: str,
        test: str,
        limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get previous executions for a specific service/test.

        Args:
            service: Service name
            test: Test name
            limit: Number of previous executions to retrieve

        Returns:
            List of previous execution events or None if error
        """
        try:
            query = f'tags:"service:{service.lower()}" AND tags:"test:{test.lower()}"'
            events = self.query_events(query, page_size=limit + 1, sort='timestamp_desc')

            if events is None:
                return None

            # Skip the first event (current execution) if we have more than limit
            if len(events) > limit:
                events = events[1:]

            return events[:limit]

        except Exception as e:
            self.logger.error(f"Error getting previous executions: {e}")
            return None

    def health_check(self) -> bool:
        """
        Check if Datadog API is accessible.

        Returns:
            True if API is accessible
        """
        try:
            url = f"{self.base_url}/api/v1/validate"
            response = self.session.get(
                url,
                headers=self._headers(),
                timeout=10
            )
            return response.status_code == 200

        except Exception as e:
            self.logger.error(f"Datadog health check failed: {e}")
            return False
