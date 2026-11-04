"""k6 load-test execution and JSON summary parsing.

Triggered from the Streamlit dashboard and from pytest performance checks
(``tests/performance/``). k6 runs as a subprocess with ``--summary-export``;
the parsed metrics land in ``reports/k6_summary.json`` for the Performance
Results tab, and every run is appended to ``reports/k6_history.json`` so the
dashboard can chart trends.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from dashboard.utils.log_streamer import LogStreamer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "performance" / "k6-scripts"
PERF_CONFIG_PATH = PROJECT_ROOT / "performance" / "perf_config.yaml"
SUMMARY_PATH = PROJECT_ROOT / "reports" / "k6_summary.json"
HISTORY_PATH = PROJECT_ROOT / "reports" / "k6_history.json"
RAW_EXPORT_PATH = PROJECT_ROOT / "reports" / "k6_summary_raw.json"


def k6_available() -> bool:
    """Whether the k6 binary is on PATH."""
    return shutil.which("k6") is not None


def load_perf_config() -> dict[str, Any]:
    """Defaults and thresholds from performance/perf_config.yaml."""
    if not PERF_CONFIG_PATH.is_file():
        return {}
    return yaml.safe_load(PERF_CONFIG_PATH.read_text(encoding="utf-8")) or {}


@dataclass(frozen=True)
class K6Config:
    """One k6 invocation."""

    target_url: str
    script: str = "homepage_load.js"
    vus: int = 5
    duration_s: int = 30


@dataclass(frozen=True)
class K6Summary:
    """Parsed headline metrics of one k6 run."""

    target_url: str
    script: str
    vus: int
    duration_s: int
    started_at: str
    requests: int
    rps: float
    error_rate: float
    latency_avg_ms: float
    latency_med_ms: float
    latency_p90_ms: float
    latency_p95_ms: float
    latency_max_ms: float
    thresholds_passed: bool


def _parse_summary(raw: dict[str, Any], config: K6Config, passed: bool) -> K6Summary:
    metrics = raw.get("metrics", {})
    duration = metrics.get("http_req_duration", {})
    reqs = metrics.get("http_reqs", {})
    failed = metrics.get("http_req_failed", {})
    return K6Summary(
        target_url=config.target_url,
        script=config.script,
        vus=config.vus,
        duration_s=config.duration_s,
        started_at=datetime.now().isoformat(timespec="seconds"),
        requests=int(reqs.get("count", 0)),
        rps=float(reqs.get("rate", 0.0)),
        error_rate=float(failed.get("value", failed.get("rate", 0.0)) or 0.0),
        latency_avg_ms=float(duration.get("avg", 0.0)),
        latency_med_ms=float(duration.get("med", 0.0)),
        latency_p90_ms=float(duration.get("p(90)", 0.0)),
        latency_p95_ms=float(duration.get("p(95)", 0.0)),
        latency_max_ms=float(duration.get("max", 0.0)),
        thresholds_passed=passed,
    )


def available_scripts() -> dict[str, str]:
    """Selectable scripts as ``{label: file}``: perf_config.yaml's ``scripts``
    map first, then any other ``*.js`` in the scripts folder."""
    configured = load_perf_config().get("scripts") or {}
    scripts = {
        str(label): str(file)
        for label, file in configured.items()
        if (SCRIPTS_DIR / str(file)).is_file()
    }
    known = set(scripts.values())
    for path in sorted(SCRIPTS_DIR.glob("*.js")):
        if path.name not in known:
            scripts[path.stem] = path.name
    return scripts


def default_settings() -> K6Config:
    """The ``defaults`` block of perf_config.yaml (target URL left empty)."""
    defaults = load_perf_config().get("defaults") or {}
    return K6Config(
        target_url="",
        script=str(defaults.get("script", K6Config.script)),
        vus=int(defaults.get("vus", K6Config.vus)),
        duration_s=int(defaults.get("duration_s", K6Config.duration_s)),
    )


def run_k6(
    config: K6Config,
    on_line: Callable[[str], None] | None = None,
    on_start: Callable[[LogStreamer], None] | None = None,
) -> tuple[K6Summary | None, int, str]:
    """Run k6; returns (summary, exit_code, message).

    Exit code 99 from k6 means "thresholds crossed" — the run still produced
    a valid summary, so it is parsed and flagged rather than discarded.
    ``on_start`` receives the streamer so another thread can stop the run.
    """
    executable = shutil.which("k6")
    if executable is None:
        return None, -1, "k6 is not installed or not on PATH (https://k6.io)"
    script_path = SCRIPTS_DIR / config.script
    if not script_path.is_file():
        return None, -1, f"k6 script not found: {script_path}"

    RAW_EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    # A leftover export from an earlier run would otherwise be parsed and
    # recorded as this run's result if k6 dies before writing a new one.
    RAW_EXPORT_PATH.unlink(missing_ok=True)
    perf_config = load_perf_config()
    thresholds = perf_config.get("thresholds", {})
    flow_paths = ",".join(perf_config.get("flow_paths", ["/"]))
    command = [
        executable,
        "run",
        "--summary-export",
        str(RAW_EXPORT_PATH),
        "--env",
        f"TARGET_URL={config.target_url}",
        "--env",
        f"VUS={config.vus}",
        "--env",
        f"DURATION={config.duration_s}s",
        "--env",
        f"P95_MS={thresholds.get('p95_ms', 800)}",
        "--env",
        f"MAX_FAIL={thresholds.get('max_failure_rate', 0.01)}",
        "--env",
        f"FLOW_PATHS={flow_paths}",
        str(script_path),
    ]
    streamer = LogStreamer(command, cwd=PROJECT_ROOT)
    if on_start is not None:
        on_start(streamer)
    for line in streamer.stream():
        if on_line is not None:
            on_line(line)
    exit_code = streamer.returncode if streamer.returncode is not None else -1

    if not RAW_EXPORT_PATH.is_file():
        return None, exit_code, f"k6 exited with {exit_code} and produced no summary"
    try:
        raw = json.loads(RAW_EXPORT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, exit_code, f"k6 exited with {exit_code}; its summary is unreadable: {exc}"
    summary = _parse_summary(raw, config, passed=exit_code == 0)
    _persist(summary)
    message = (
        "Run completed, all thresholds passed"
        if exit_code == 0
        else f"Run completed with exit code {exit_code} (99 = thresholds crossed)"
    )
    return summary, exit_code, message


def _persist(summary: K6Summary) -> None:
    SUMMARY_PATH.write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    history: list[dict[str, Any]] = []
    if HISTORY_PATH.is_file():
        try:
            history = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    history.insert(0, asdict(summary))
    HISTORY_PATH.write_text(json.dumps(history[:100], indent=2), encoding="utf-8")


def latest_summary() -> dict[str, Any] | None:
    """The most recent parsed summary, if any."""
    if not SUMMARY_PATH.is_file():
        return None
    try:
        return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def history() -> list[dict[str, Any]]:
    """All recorded k6 runs, newest first."""
    if not HISTORY_PATH.is_file():
        return []
    try:
        entries = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return entries if isinstance(entries, list) else []


def comparable_runs(
    runs: list[dict[str, Any]], target_url: str, script: str
) -> list[dict[str, Any]]:
    """Runs against the same target with the same script (newest first).

    Trends and deltas only mean something between like-for-like runs; mixing
    targets or scripts in one line chart would be misleading.
    """
    return [
        run for run in runs if run.get("target_url") == target_url and run.get("script") == script
    ]
