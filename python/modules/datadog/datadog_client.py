import logging
import time
from typing import Any, Dict, List, Optional

import requests

from config import (
    DATADOG_API_KEY,
    DATADOG_APP_KEY,
    DATADOG_SITE,
    HISTORICAL_LOOKBACK_DAYS,
)

logger = logging.getLogger(__name__)


class DatadogClient:
    """
    Client for interacting with Datadog APIs.

    Supports:
    - Sending events
    - Sending metrics
    - Querying historical events
    - Querying logs
    - Retrieving previous test executions
    - Health checking Datadog connectivity
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        app_key: Optional[str] = None,
        site: Optional[str] = None,
    ):
        self.api_key = api_key or DATADOG_API_KEY
        self.app_key = app_key or DATADOG_APP_KEY
        self.site = site or DATADOG_SITE

        self.base_url = f"https://api.{self.site}"

        self.session = requests.Session()

        self.session.headers.update(
            {
                "DD-API-KEY": self.api_key,
                "DD-APPLICATION-KEY": self.app_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        logger.info("Datadog client initialized for site: %s", self.site)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def send_event(
        self,
        title: str,
        text: str,
        tags: Optional[List[str]] = None,
        alert_type: str = "info",
    ) -> bool:
        """
        Send an event to Datadog.
        """

        url = f"{self.base_url}/api/v1/events"

        payload = {
            "title": title,
            "text": text,
            "tags": tags or [],
            "alert_type": alert_type,
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 202):
                logger.debug("Datadog event sent successfully")
                return True

            logger.error(
                "Failed to send Datadog event: %s - %s",
                response.status_code,
                response.text,
            )
            return False

        except requests.RequestException as exc:
            logger.error("Error sending Datadog event: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def send_metrics(self, series: List[Dict[str, Any]]) -> bool:
        """
        Send metrics to Datadog.

        `series` should contain Datadog metric series payloads.
        """

        url = f"{self.base_url}/api/v1/series"

        payload = {
            "series": series,
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=30,
            )

            if response.status_code in (200, 202):
                logger.debug(
                    "Datadog metrics sent successfully: %d series",
                    len(series),
                )
                return True

            logger.error(
                "Failed to send Datadog metrics: %s - %s",
                response.status_code,
                response.text,
            )
            return False

        except requests.RequestException as exc:
            logger.error("Error sending Datadog metrics: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Dashboards
    # ------------------------------------------------------------------

    def create_dashboard(self, dashboard: Dict[str, Any]) -> Optional[str]:
        """Create a Datadog dashboard and return its ID."""
        url = f"{self.base_url}/api/v1/dashboard"

        try:
            response = self.session.post(url, json=dashboard, timeout=30)
            if response.status_code in (200, 201):
                return response.json().get("id")

            logger.error(
                "Failed to create Datadog dashboard: %s - %s",
                response.status_code,
                response.text,
            )
            return None
        except requests.RequestException as exc:
            logger.error("Error creating Datadog dashboard: %s", exc)
            return None

    def update_dashboard(
        self,
        dashboard_id: str,
        dashboard: Dict[str, Any],
    ) -> bool:
        """Update an existing Datadog dashboard."""
        url = f"{self.base_url}/api/v1/dashboard/{dashboard_id}"

        try:
            response = self.session.put(url, json=dashboard, timeout=30)
            if response.status_code == 200:
                return True

            logger.error(
                "Failed to update Datadog dashboard: %s - %s",
                response.status_code,
                response.text,
            )
            return False
        except requests.RequestException as exc:
            logger.error("Error updating Datadog dashboard: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Historical Events
    # ------------------------------------------------------------------

    def query_events(
        self,
        query: str,
        page_size: int = 100,
        sort: str = "timestamp_desc",
    ) -> List[Dict[str, Any]]:
        """
        Query historical Datadog events.

        Datadog requires `start` and `end` timestamps for the events API.
        The configured HISTORICAL_LOOKBACK_DAYS value controls how far
        back we search.
        """

        url = f"{self.base_url}/api/v1/events"

        end_time = int(time.time())

        start_time = end_time - (
            HISTORICAL_LOOKBACK_DAYS * 24 * 60 * 60
        )

        params = {
            "start": start_time,
            "end": end_time,
            "query": query,
            "page_size": page_size,
            "sort": sort,
        }

        logger.debug(
            "Querying Datadog events from %s to %s",
            start_time,
            end_time,
        )

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to query events: %s - %s",
                    response.status_code,
                    response.text,
                )
                return []

            data = response.json()

            events = data.get("events", [])

            logger.debug(
                "Retrieved %d Datadog events",
                len(events),
            )

            return events

        except requests.RequestException as exc:
            logger.error("Error querying Datadog events: %s", exc)
            return []

        except ValueError as exc:
            logger.error(
                "Invalid JSON returned from Datadog events API: %s",
                exc,
            )
            return []

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------

    def query_logs(
        self,
        query: str,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Query Datadog logs.

        `from_time` and `to_time` should be ISO-8601 timestamps.
        """

        url = f"{self.base_url}/api/v2/logs/events/search"

        payload: Dict[str, Any] = {
            "filter": {
                "query": query,
            },
            "page": {
                "limit": limit,
            },
        }

        if from_time:
            payload["filter"]["from"] = from_time

        if to_time:
            payload["filter"]["to"] = to_time

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to query logs: %s - %s",
                    response.status_code,
                    response.text,
                )
                return []

            data = response.json()

            return data.get("data", [])

        except requests.RequestException as exc:
            logger.error("Error querying Datadog logs: %s", exc)
            return []

        except ValueError as exc:
            logger.error(
                "Invalid JSON returned from Datadog logs API: %s",
                exc,
            )
            return []

    # ------------------------------------------------------------------
    # Previous Test Executions
    # ------------------------------------------------------------------

    def get_previous_executions(
        self,
        service: str,
        test: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve previous executions of a specific API test.

        Events are identified using the tags:
            service:<service>
            test:<test>
        """

        query = (
            f'tags:"service:{service.lower()}" '
            f'AND tags:"test:{test.lower()}"'
        )

        logger.debug(
            "Searching historical executions for service=%s, test=%s",
            service,
            test,
        )

        events = self.query_events(
            query=query,
            page_size=limit + 1,
            sort="timestamp_desc",
        )

        # The most recent event can represent the current execution,
        # depending on when the historical query is performed.
        #
        # Keep the existing behavior of ignoring the first result when
        # more than `limit` results are returned.
        if len(events) > limit:
            events = events[1:]

        return events[:limit]

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Check whether Datadog API credentials/connectivity are working.
        """

        url = f"{self.base_url}/api/v1/validate"

        try:
            response = self.session.get(
                url,
                timeout=15,
            )

            if response.status_code == 200:
                logger.info("Datadog health check successful")
                return True

            logger.error(
                "Datadog health check failed: %s - %s",
                response.status_code,
                response.text,
            )
            return False

        except requests.RequestException as exc:
            logger.error(
                "Datadog health check error: %s",
                exc,
            )
            return False