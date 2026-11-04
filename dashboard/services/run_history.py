"""Persistent history of dashboard-triggered runs (JSON file under reports/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = PROJECT_ROOT / "reports" / "run_history.json"
MAX_ENTRIES = 200

_DEFAULTS: dict[str, Any] = {
    "mode": "A",
    "target": "",
    "test_types": [],
    "browsers": [],
    "parallel": False,
    "duration_s": 0.0,
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "exit_code": -1,
}


def pass_rate(entry: dict[str, Any]) -> float | None:
    """Share of executed (non-skipped) tests that passed, or None if none ran."""
    executed = entry.get("passed", 0) + entry.get("failed", 0)
    return entry.get("passed", 0) / executed if executed else None


def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
    """Fill fields that older history files did not record."""
    normalized = {**_DEFAULTS, **entry}
    if "status" not in entry:
        normalized["status"] = "passed" if normalized["exit_code"] == 0 else "failed"
    normalized["pass_rate"] = pass_rate(normalized)
    return normalized


def load_history() -> list[dict[str, Any]]:
    """All recorded runs, newest first."""
    if not HISTORY_PATH.is_file():
        return []
    try:
        entries = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(entries, list):
        return []
    return [_normalize(entry) for entry in entries if isinstance(entry, dict)]


def append_entry(
    *,
    mode: str,
    target: str,
    test_types: list[str],
    browsers: list[str],
    parallel: bool,
    duration_s: float,
    passed: int,
    failed: int,
    skipped: int,
    exit_code: int,
    status: str | None = None,
) -> None:
    """Record one completed run (bounded to the newest MAX_ENTRIES)."""
    entries = load_history()
    entries.insert(
        0,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status or ("passed" if exit_code == 0 else "failed"),
            "mode": mode,
            "target": target,
            "test_types": test_types,
            "browsers": browsers,
            "parallel": parallel,
            "duration_s": round(duration_s, 1),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "exit_code": exit_code,
        },
    )
    stored = [{k: v for k, v in entry.items() if k != "pass_rate"} for entry in entries]
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(stored[:MAX_ENTRIES], indent=2), encoding="utf-8")
