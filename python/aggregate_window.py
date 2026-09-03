"""Build one combined report from independently scheduled service workflows."""

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from config import DATADOG_SITE
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate one Datadog analysis window")
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    setup_logger(log_level="INFO")
    client = DatadogClient()
    query = (
        f'tags:"window_id:{args.window_id}" '
        'AND tags:"event_type:analysis"'
    )
    events = client.query_events(query=query, page_size=1000)

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
    summary = SummaryGenerator().generate(results)
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
