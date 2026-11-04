"""Write a Markdown summary of raw Allure results to the GitHub job summary.

Reads ``*-result.json`` files directly (no Allure CLI or Java needed), so it
works in any job that has the results artifact. Usage::

    python .github/scripts/allure_summary.py reports/allure-results "Smoke on dev"

Appends to ``$GITHUB_STEP_SUMMARY`` when set, otherwise prints to stdout.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

_ORDER = ("passed", "failed", "broken", "skipped", "unknown")
_ICONS = {"passed": "✅", "failed": "❌", "broken": "💥", "skipped": "⏭️", "unknown": "❔"}
_MAX_LISTED = 25


def summarize(results_dir: Path, title: str) -> str:
    counts: Counter[str] = Counter()
    problems: list[str] = []
    for path in sorted(results_dir.glob("*-result.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        status = result.get("status", "unknown")
        counts[status] += 1
        if status in ("failed", "broken"):
            name = result.get("fullName") or result.get("name", path.stem)
            message = (result.get("statusDetails") or {}).get("message", "").strip()
            first_line = message.splitlines()[0][:160] if message else ""
            problems.append(f"| {_ICONS[status]} | `{name}` | {first_line} |")

    total = sum(counts.values())
    lines = [f"## {title}", ""]
    if not total:
        lines.append("_No Allure results found._")
        return "\n".join(lines) + "\n"
    passed = counts.get("passed", 0)
    lines += [
        f"**{passed}/{total} passed** ({passed / total:.0%})",
        "",
        "| " + " | ".join(f"{_ICONS[s]} {s}" for s in _ORDER if counts.get(s)) + " |",
        "|" + "---|" * sum(1 for s in _ORDER if counts.get(s)),
        "| " + " | ".join(str(counts[s]) for s in _ORDER if counts.get(s)) + " |",
    ]
    if problems:
        lines += ["", "| | Test | Message |", "|---|---|---|", *problems[:_MAX_LISTED]]
        if len(problems) > _MAX_LISTED:
            lines.append(f"\n_…and {len(problems) - _MAX_LISTED} more._")
    return "\n".join(lines) + "\n"


def main() -> None:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("reports/allure-results")
    title = sys.argv[2] if len(sys.argv) > 2 else "Test results"
    markdown = summarize(results_dir, title)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    else:
        sys.stdout.reconfigure(encoding="utf-8")  # emoji on e.g. a cp1252 Windows console
        print(markdown)


if __name__ == "__main__":
    main()
