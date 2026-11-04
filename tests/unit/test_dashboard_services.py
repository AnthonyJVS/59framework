"""Unit tests for the dashboard's pure logic: command building, output parsing,
subprocess streaming, k6 summary handling and Gemini key lookup."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from dashboard.services import gemini_service, k6_service
from dashboard.services.test_executor import RunConfig, RunCounters, build_pytest_command
from dashboard.utils.log_streamer import LogStreamer

pytestmark = [pytest.mark.unit]


# --- build_pytest_command ---------------------------------------------------


def test_mode_a_passes_env_only() -> None:
    command = build_pytest_command(RunConfig(markers=["smoke"], env_name="staging"))
    assert "--env=staging" in command
    assert not any(arg.startswith("--base-url") for arg in command)


def test_matched_url_keeps_its_environment() -> None:
    """A URL that matched an environment must still select that env's config."""
    command = build_pytest_command(
        RunConfig(markers=["smoke"], env_name="staging", target_url="https://staging.example")
    )
    assert "--base-url=https://staging.example" in command
    assert "--env=staging" in command


def test_scanner_only_run_has_no_browser_flags() -> None:
    command = build_pytest_command(
        RunConfig(
            markers=["scanner"],
            target_url="https://any.site",
            browsers=["firefox"],
            scan_depth=2,
            scan_max_pages=7,
            scan_record_video=True,
        )
    )
    assert "--browser" not in command
    assert "--env" not in " ".join(command)
    assert {"--scan-depth=2", "--scan-max-pages=7", "--scan-record-video"} <= set(command)


def test_markers_browsers_and_parallel() -> None:
    command = build_pytest_command(
        RunConfig(
            markers=["smoke", "api"],
            env_name="dev",
            browsers=["chromium", "webkit"],
            parallel=True,
            reruns=2,
        )
    )
    pytest_args = command[3:]  # drop "<python> -m pytest"
    assert pytest_args[pytest_args.index("-m") + 1] == "smoke or api"
    assert command.count("--browser") == 2
    assert command[command.index("-n") + 1] == "auto"
    assert "--reruns=2" in command


# --- RunCounters ------------------------------------------------------------


def test_counters_parse_serial_and_xdist_lines_and_ignore_recap() -> None:
    lines = [
        "tests/ui/test_a.py::test_one[chromium] PASSED                [ 25%]",
        "[gw0] [ 50%] PASSED tests/ui/test_a.py::test_two[chromium]",
        "[gw1] [ 75%] FAILED tests/ui/test_a.py::test_three[chromium]",
        "tests/api/test_b.py::test_four SKIPPED (no target)          [ 90%]",
        "tests/api/test_b.py::test_five ERROR                         [100%]",
        "==================================== FAILURES ====================================",
        "____________________________ test_three[chromium] ____________________________",
        "E   AssertionError: FAILED to find element",
        "=========================== short test summary info ============================",
        "FAILED tests/ui/test_a.py::test_three[chromium] - AssertionError",
        "ERROR tests/api/test_b.py::test_five",
    ]
    counters = RunCounters()
    for line in lines:
        counters.observe(line)
    assert (counters.passed, counters.failed, counters.skipped, counters.errors) == (2, 1, 1, 1)


# --- LogStreamer ------------------------------------------------------------


def test_streamer_yields_lines_and_exit_code(tmp_path: Path) -> None:
    streamer = LogStreamer(
        [sys.executable, "-c", "print('one'); print('two'); raise SystemExit(3)"], cwd=tmp_path
    )
    assert list(streamer.stream()) == ["one", "two"]
    assert streamer.returncode == 3


def test_abandoned_stream_stops_the_process(tmp_path: Path) -> None:
    """Closing the generator early (e.g. a Streamlit rerun) must not leave the
    process running, nor block until it finishes on its own."""
    script = "import time\nprint('started', flush=True)\ntime.sleep(60)\n"
    streamer = LogStreamer([sys.executable, "-c", script], cwd=tmp_path)
    lines = streamer.stream()
    assert next(lines) == "started"
    started = time.monotonic()
    lines.close()
    assert time.monotonic() - started < 15, "closing the stream waited for the process"
    assert streamer.returncode is not None, "process is still running"
    assert streamer.returncode != 0


# --- k6 service -------------------------------------------------------------


class _SilentFailingStreamer:
    """Stands in for a k6 process that dies without writing a summary."""

    def __init__(self, *_: object, **__: object) -> None:
        self.returncode: int | None = None

    def stream(self) -> Iterator[str]:
        self.returncode = 107
        yield "k6: fatal error"


def test_k6_ignores_a_stale_summary_from_a_previous_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = tmp_path / "k6_summary_raw.json"
    raw.write_text(json.dumps({"metrics": {"http_reqs": {"count": 999}}}), encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "homepage_load.js").write_text("// stub", encoding="utf-8")
    monkeypatch.setattr(k6_service, "RAW_EXPORT_PATH", raw)
    monkeypatch.setattr(k6_service, "SCRIPTS_DIR", scripts)
    monkeypatch.setattr(k6_service, "SUMMARY_PATH", tmp_path / "k6_summary.json")
    monkeypatch.setattr(k6_service, "HISTORY_PATH", tmp_path / "k6_history.json")
    monkeypatch.setattr(k6_service.shutil, "which", lambda _: "k6")
    monkeypatch.setattr(k6_service, "LogStreamer", _SilentFailingStreamer)

    summary, exit_code, message = k6_service.run_k6(k6_service.K6Config(target_url="https://x"))

    assert summary is None
    assert exit_code == 107
    assert "no summary" in message
    assert not (tmp_path / "k6_history.json").exists()


def test_k6_summary_parsing() -> None:
    raw = {
        "metrics": {
            "http_reqs": {"count": 40, "rate": 8.0},
            "http_req_failed": {"value": 0.025},
            "http_req_duration": {
                "avg": 120.5,
                "med": 100.0,
                "p(90)": 180.0,
                "p(95)": 210.0,
                "max": 400.0,
            },
        }
    }
    summary = k6_service._parse_summary(raw, k6_service.K6Config(target_url="https://x"), True)
    assert (summary.requests, summary.rps, summary.error_rate) == (40, 8.0, 0.025)
    assert (summary.latency_p95_ms, summary.latency_max_ms) == (210.0, 400.0)
    assert summary.thresholds_passed


# --- Gemini key lookup ------------------------------------------------------


def test_gemini_key_lookup_does_not_touch_process_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=from-file\nENV=prod\nTARGET_URL=https://x\n")
    monkeypatch.setattr(gemini_service, "ENV_PATH", env_file)
    monkeypatch.setenv("ENV", "staging")
    monkeypatch.delenv("TARGET_URL", raising=False)

    assert gemini_service._current_api_key() == "from-file"
    assert os.environ["ENV"] == "staging"
    assert "TARGET_URL" not in os.environ


def test_gemini_key_falls_back_to_process_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gemini_service, "ENV_PATH", tmp_path / "missing.env")
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert gemini_service._current_api_key() == "from-env"
    monkeypatch.delenv("GEMINI_API_KEY")
    assert not gemini_service.gemini_available()
