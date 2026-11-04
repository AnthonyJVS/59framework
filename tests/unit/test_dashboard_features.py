"""Unit tests for the dashboard's background jobs and the newer service features."""

from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from dashboard.services import (
    allure_service,
    gemini_service,
    job_manager,
    k6_service,
    run_history,
    test_executor,
)
from dashboard.services.job_manager import JobBusyError, JobManager
from dashboard.services.test_executor import RunConfig, RunCounters, build_pytest_command
from framework.scanner.console_error_capture import ConsoleIssue
from framework.scanner.link_crawler import check_links

pytestmark = [pytest.mark.unit]


# --- progress parsing ---------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "total"),
    [
        ("collected 44 items / 34 deselected / 10 selected", 10),
        ("collected 7 items", 7),
        ("4 workers [12 items]", 12),
    ],
)
def test_counters_pick_up_the_total(line: str, total: int) -> None:
    counters = RunCounters()
    counters.observe(line)
    assert counters.total == total
    assert counters.progress == 0.0


def test_progress_is_clamped() -> None:
    counters = RunCounters(passed=3, errors=1, total=3)
    assert counters.progress == 1.0


def test_last_failed_and_scanner_flags() -> None:
    command = build_pytest_command(
        RunConfig(
            markers=["scanner"],
            target_url="https://x.test",
            last_failed=True,
            scan_external=True,
            scan_ignore_console=["gtm", "ads .*"],
        )
    )
    assert {"--last-failed", "--last-failed-no-failures=none", "--scan-external"} <= set(command)
    assert "--scan-ignore-console=ads .*" in command


def test_display_command_hides_the_interpreter() -> None:
    shown = test_executor.display_command([sys.executable, "-m", "pytest", "-m", "smoke or api"])
    assert shown == 'pytest -m "smoke or api"'


# --- background jobs ------------------------------------------------------------

_FAKE_PYTEST = """
import sys, time
print("collected 3 items", flush=True)
print("tests/a.py::test_one PASSED", flush=True)
print("tests/a.py::test_two FAILED", flush=True)
if "--slow" in sys.argv:
    time.sleep(60)
print("tests/a.py::test_three PASSED", flush=True)
sys.exit(1)
"""


@pytest.fixture
def fake_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Replace pytest with a tiny script and keep side effects in tmp_path."""

    def fake_command(config: RunConfig) -> list[str]:
        extra = ["--slow"] if "slow" in config.markers else []
        return [sys.executable, "-c", _FAKE_PYTEST, *extra]

    monkeypatch.setattr(test_executor, "build_pytest_command", fake_command)
    monkeypatch.setattr(job_manager, "build_pytest_command", fake_command)
    monkeypatch.setattr(allure_service, "generate_report", lambda: (False, "skipped in tests"))
    monkeypatch.setattr(run_history, "HISTORY_PATH", tmp_path / "run_history.json")
    return tmp_path


def _wait_until_done(manager: JobManager, timeout_s: float = 30) -> None:
    deadline = time.monotonic() + timeout_s
    while manager.busy:
        assert time.monotonic() < deadline, "job did not finish in time"
        time.sleep(0.05)


def test_job_runs_in_background_and_records_history(fake_runs: Path) -> None:
    manager = JobManager()
    job = manager.start_tests(
        RunConfig(markers=["smoke"]), {"mode": "A", "target": "dev", "test_types": ["Smoke"]}
    )
    _wait_until_done(manager)
    assert job.status == "failed"
    assert (job.counters.passed, job.counters.failed, job.counters.total) == (2, 1, 3)
    assert job.exit_code == 1
    assert job.needs_attention
    entry = run_history.load_history()[0]
    assert (entry["status"], entry["passed"], entry["failed"]) == ("failed", 2, 1)


def test_only_one_job_at_a_time_and_stop_terminates_it(fake_runs: Path) -> None:
    manager = JobManager()
    job = manager.start_tests(RunConfig(markers=["slow"]), {"target": "dev"})
    deadline = time.monotonic() + 15
    while job.counters.failed == 0:  # wait until the fake run reaches its sleep
        assert time.monotonic() < deadline
        time.sleep(0.05)
    with pytest.raises(JobBusyError):
        manager.start_tests(RunConfig(markers=["smoke"]), {})
    started = time.monotonic()
    manager.stop()
    _wait_until_done(manager)
    assert time.monotonic() - started < 15
    assert job.status == "stopped"
    assert run_history.load_history()[0]["status"] == "stopped"
    assert manager.previous is None and manager.current is job


# --- run history ----------------------------------------------------------------


def test_history_normalizes_legacy_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "run_history.json"
    path.write_text(json.dumps([{"timestamp": "t", "exit_code": 0, "passed": 3, "failed": 1}]))
    monkeypatch.setattr(run_history, "HISTORY_PATH", path)
    entry = run_history.load_history()[0]
    assert entry["status"] == "passed"
    assert entry["pass_rate"] == 0.75
    assert entry["browsers"] == []


# --- k6 --------------------------------------------------------------------------


def test_comparable_runs_filter_by_target_and_script() -> None:
    runs = [
        {"target_url": "a", "script": "x.js", "n": 1},
        {"target_url": "b", "script": "x.js", "n": 2},
        {"target_url": "a", "script": "y.js", "n": 3},
        {"target_url": "a", "script": "x.js", "n": 4},
    ]
    assert [run["n"] for run in k6_service.comparable_runs(runs, "a", "x.js")] == [1, 4]


def test_available_scripts_use_config_labels_then_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("homepage_load.js", "checkout_flow.js", "extra.js"):
        (tmp_path / name).write_text("//", encoding="utf-8")
    config = tmp_path / "perf.yaml"
    config.write_text(
        "defaults: {script: checkout_flow.js, vus: 3, duration_s: 12}\n"
        "scripts: {homepage: homepage_load.js, missing: nope.js}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(k6_service, "SCRIPTS_DIR", tmp_path)
    monkeypatch.setattr(k6_service, "PERF_CONFIG_PATH", config)
    assert k6_service.available_scripts() == {
        "homepage": "homepage_load.js",
        "checkout_flow": "checkout_flow.js",
        "extra": "extra.js",
    }
    defaults = k6_service.default_settings()
    assert (defaults.script, defaults.vus, defaults.duration_s) == ("checkout_flow.js", 3, 12)


# --- Allure ----------------------------------------------------------------------


def test_allure_history_is_carried_into_the_next_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report, results = tmp_path / "report", tmp_path / "results"
    (report / "history").mkdir(parents=True)
    (report / "history" / "history-trend.json").write_text("[1]", encoding="utf-8")
    results.mkdir()
    monkeypatch.setattr(allure_service, "REPORT_DIR", report)
    monkeypatch.setattr(allure_service, "RESULTS_DIR", results)
    allure_service._carry_over_history()
    assert (results / "history" / "history-trend.json").read_text() == "[1]"


# --- Gemini excerpt ---------------------------------------------------------------


def test_failure_excerpt_keeps_failures_section_and_summary() -> None:
    log = (
        "\n".join(f"tests/t.py::test_{i} PASSED" for i in range(2000))
        + "\n=================== FAILURES ===================\n"
        + "E   AssertionError: the real cause\n"
        + "x" * 20_000
        + "\n=========== 1 failed, 2000 passed in 9.99s ==========="
    )
    excerpt = gemini_service.failure_excerpt(log, limit=4000)
    assert len(excerpt) <= 4000
    assert "the real cause" in excerpt
    assert "1 failed, 2000 passed" in excerpt
    assert "test_5 PASSED" not in excerpt


def test_failure_excerpt_short_log_is_unchanged() -> None:
    assert gemini_service.failure_excerpt("short log") == "short log"


def test_gemini_model_is_configurable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_service, "ENV_PATH", tmp_path / "none.env")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert gemini_service.model_name() == gemini_service.DEFAULT_MODEL
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom")
    assert gemini_service.model_name() == "gemini-custom"


# --- scanner: HTTP link checks ------------------------------------------------------


class _Handler(BaseHTTPRequestHandler):
    def _respond(self, with_body: bool) -> None:
        if self.path == "/no-head" and self.command == "HEAD":
            self.send_response(405)
        elif self.path in ("/ok", "/no-head"):
            self.send_response(200)
        elif self.path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/ok")
        else:
            self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        self._respond(with_body=False)

    def do_GET(self) -> None:  # noqa: N802
        self._respond(with_body=True)

    def log_message(self, *_: object) -> None:
        pass


@pytest.fixture
def local_site() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_check_links_statuses_redirects_and_head_fallback(local_site: str) -> None:
    links = [
        (f"{local_site}/ok", None, False),
        (f"{local_site}/missing", "page", False),
        (f"{local_site}/moved", "page", True),
        (f"{local_site}/no-head", "page", False),
        ("http://127.0.0.1:9/unreachable", "page", True),
    ]
    results = check_links(links, workers=4, timeout_s=5)
    assert [result.url for result in results] == [url for url, _, _ in links]
    assert [(result.status, result.ok) for result in results[:4]] == [
        (200, True),
        (404, False),
        (200, True),
        (200, True),
    ]
    assert results[2].external
    assert results[4].status == 0 and not results[4].ok and results[4].error


# --- scanner: console issue origin --------------------------------------------------


@pytest.mark.parametrize(
    ("source", "third_party"),
    [("", False), ("https://site.test/app.js", False), ("https://cdn.other/x.js", True)],
)
def test_console_issue_third_party(source: str, third_party: bool) -> None:
    issue = ConsoleIssue("console-error", "https://site.test/page", "boom", source)
    assert issue.third_party is third_party
