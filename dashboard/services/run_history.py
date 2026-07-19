"""Persistent history of dashboard-triggered runs (JSON file under reports/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = PROJECT_ROOT / "reports" / "run_history.json"
MAX_ENTRIES = 200


def load_history() -> list[dict[str, Any]]:
    """All recorded runs, newest first."""
    if not HISTORY_PATH.is_file():
        return []
    try:
        entries = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return entries if isinstance(entries, list) else []


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
) -> None:
    """Record one completed run (bounded to the newest MAX_ENTRIES)."""
    entries = load_history()
    entries.insert(
        0,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
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
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(entries[:MAX_ENTRIES], indent=2), encoding="utf-8")
