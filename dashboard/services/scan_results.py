"""Access to the Site Scanner's exported artifacts (written by tests/scanner)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = PROJECT_ROOT / "reports" / "scan_results.json"
VIDEO_PATH = PROJECT_ROOT / "reports" / "scan_video.webm"


def load() -> dict[str, Any] | None:
    """The latest scan, or None when there is none (or it is unreadable)."""
    if not RESULTS_PATH.is_file():
        return None
    try:
        data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "start_url" not in data:
        return None
    # Scans exported by older versions lack some fields; give them defaults.
    for result in data.setdefault("results", []):
        result.setdefault("error", None)
        result.setdefault("external", False)
    for issue in data.setdefault("console_issues", []):
        issue.setdefault("source_url", "")
        issue.setdefault("third_party", False)
    data.setdefault("visited_pages", [])
    data.setdefault("timing", {})
    data.setdefault("generated_at", "")
    data.setdefault("max_depth", 0)
    return data
