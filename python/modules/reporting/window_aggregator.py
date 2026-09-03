"""Combine independently produced analysis artifacts for one time window."""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from modules.reporting.summary_generator import SummaryGenerator


class WindowAggregator:
    """Deduplicate per-job results and generate one combined report."""

    def aggregate_files(self, paths: Iterable[str]) -> List[Dict[str, Any]]:
        unique_results: Dict[str, Dict[str, Any]] = {}

        for path in paths:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            results = payload if isinstance(payload, list) else payload.get("results", [])

            for result in results:
                key = result.get("idempotency_key")
                if not key:
                    key = ":".join(
                        str(result.get(field, ""))
                        for field in ("window_id", "service", "test", "execution_id")
                    )

                existing = unique_results.get(key)
                if existing is None or str(result.get("timestamp", "")) > str(existing.get("timestamp", "")):
                    unique_results[key] = result

        return list(unique_results.values())

    def write_report(self, paths: Iterable[str], output_path: str) -> List[Dict[str, Any]]:
        results = self.aggregate_files(paths)
        summary = SummaryGenerator().generate(results)
        Path(output_path).write_text(summary + "\n", encoding="utf-8")
        return results
