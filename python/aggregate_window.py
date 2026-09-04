"""Build one combined report from independently scheduled service workflows."""

import argparse
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from config import DATADOG_SITE, DATADOG_TAGS
from logger import setup_logger
from modules.datadog.datadog_client import DatadogClient
from modules.reporting.summary_generator import SummaryGenerator

logger = logging.getLogger(__name__)


def tags_to_dict(tags: Any) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if isinstance(tags, str):
        tags = tags.split(",")
    for tag in tags or []:
        if isinstance(tag, str) and ":" in tag:
            key, value = tag.split(":", 1)
            values[key] = value
    return values


def has_tag(tags: Any, expected: str) -> bool:
    return expected in tags if isinstance(tags, list) else expected in str(tags).split(",")


def event_is_in_window(event: Dict[str, Any], window_id: str) -> bool:
    if has_tag(event.get("tags", []), f"window_id:{window_id}"):
        return True

    try:
        window_start = datetime.strptime(window_id, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
        event_time = event.get("timestamp")
        if isinstance(event_time, (int, float)):
            event_date = datetime.fromtimestamp(
                event_time / 1000 if event_time > 10_000_000_000 else event_time,
                tz=timezone.utc,
            )
        else:
            event_date = datetime.fromisoformat(str(event_time).replace("Z", "+00:00"))
        return window_start <= event_date < window_start + timedelta(minutes=30)
    except (TypeError, ValueError, OSError):
        return False


def event_to_result(event: Dict[str, Any], window_id: str) -> Dict[str, Any]:
    tags = tags_to_dict(event.get("tags", []))
    title = str(event.get("title", ""))
    identity, _, classification = title.partition(":")
    service, _, test = identity.strip().partition("/")
    text = str(event.get("text", ""))
    fields: Dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower()] = value.strip()

    status = fields.get("status", tags.get("status", "UNKNOWN")).upper()
    jira_action = fields.get("jira action", "NONE").upper()
    jira_key = fields.get("jira issue")
    jira_url = fields.get("jira url")

    return {
        "window_id": window_id,
        "execution_id": tags.get("execution_id", "unknown"),
        "idempotency_key": tags.get("idempotency_key"),
        "service": service.lower(),
        "test": test.lower(),
        "status": status,
        "http_status": int(fields.get("http status", "0") or 0),
        "classification": {"pattern": classification.strip() or "Unknown"},
        "jira": {
            "has_issue": bool(jira_key),
            "issue_key": jira_key,
            "issue_url": jira_url,
            "jira_action": jira_action,
        },
        "timestamp": event.get("timestamp", ""),
    }


def publish_summary_metrics(
    client: DatadogClient,
    results: List[Dict[str, Any]],
    window_id: str,
) -> bool:
    timestamp = int(time.time())
    total_apis = len(results)
    passed_apis = sum(1 for result in results if result.get("status") == "PASS")
    failed_apis = total_apis - passed_apis
    services: Dict[str, Dict[str, int]] = {}
    for result in results:
        service = str(result.get("service", "unknown"))
        counts = services.setdefault(service, {"pass": 0, "fail": 0})
        counts["pass" if result.get("status") == "PASS" else "fail"] += 1

    base_tags = list(DATADOG_TAGS) + [f"window_id:{window_id}"]
    metrics = [
        ("run_total_apis", total_apis, base_tags),
        ("run_passed_apis", passed_apis, base_tags),
        ("run_failed_apis", failed_apis, base_tags),
        ("run_total_services", len(services), base_tags),
        ("run_passed_services", sum(1 for counts in services.values() if not counts["fail"]), base_tags),
        ("run_failed_services", sum(1 for counts in services.values() if counts["fail"]), base_tags),
    ]
    for service, counts in services.items():
        service_tags = base_tags + [f"service:{service}"]
        metrics.extend([
            ("run_service_total_apis_v2", counts["pass"] + counts["fail"], service_tags),
            ("run_service_passed_apis_v2", counts["pass"], service_tags),
            ("run_service_failed_apis_v2", counts["fail"], service_tags),
        ])

    return client.send_metrics([
        {
            "metric": f"api_test.{name}",
            "type": "gauge",
            "points": [[timestamp, value]],
            "tags": tags,
        }
        for name, value, tags in metrics
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate one Datadog analysis window")
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    setup_logger(log_level="INFO")
    client = DatadogClient()
    query = 'tags:"event_type:analysis"'
    analysis_events = client.query_events(query=query, page_size=1000)
    events = [
        event for event in analysis_events
        if event_is_in_window(event, args.window_id)
    ]

    unique: Dict[str, Dict[str, Any]] = {}
    for event in events:
        result = event_to_result(event, args.window_id)
        key = result.get("idempotency_key") or ":".join(
            str(result.get(field, ""))
            for field in ("window_id", "service", "test", "execution_id")
        )
        existing = unique.get(key)
        if existing is None or str(result.get("timestamp", "")) > str(existing.get("timestamp", "")):
            unique[key] = result

    results: List[Dict[str, Any]] = list(unique.values())
    summary = SummaryGenerator().generate(
        results,
        empty_message=(
            f"No API test results available for window {args.window_id}. "
            "No Datadog analysis events were returned for this window."
        ),
    )
    if results and not publish_summary_metrics(client, results, args.window_id):
        logger.warning("Combined summary metrics could not be published")
    output = args.output or f"reports/combined_{args.window_id.replace(':', '-')}.txt"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary + "\n", encoding="utf-8")
    output_path.with_suffix(".json").write_text(
        json.dumps(results, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    logger.info("Aggregated %d unique results from Datadog site %s", len(results), DATADOG_SITE)
    logger.info("Combined report written to %s", output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
