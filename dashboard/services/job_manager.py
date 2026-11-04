"""Background execution of test runs and k6 load tests for the dashboard.

Runs used to execute inside the Streamlit script itself, so any interaction —
switching page, clicking a widget, refreshing the tab — interrupted (and with
it, killed) the run. Here each run lives on a worker thread owned by one
process-wide :class:`JobManager`; the UI only polls it. That gives:

* runs that survive navigation, reruns and browser refreshes;
* an explicit Stop that terminates the whole process tree;
* one run at a time, so two runs never clobber ``reports/allure-results``.

This module has no Streamlit dependency; ``dashboard/state.py`` caches the
singleton with ``st.cache_resource``.
"""

from __future__ import annotations

import atexit
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from dashboard.services import allure_service, k6_service, run_history
from dashboard.services.k6_service import K6Config, K6Summary
from dashboard.services.test_executor import (
    RunConfig,
    RunCounters,
    TestExecutor,
    build_pytest_command,
    display_command,
)
from dashboard.utils.log_streamer import LogStreamer

JobKind = Literal["tests", "k6"]
JobStatus = Literal["running", "passed", "failed", "stopped", "error"]

#: Lines kept in memory per job; older output is dropped (the counters are not).
MAX_LOG_LINES = 20_000


@dataclass
class Job:
    """One test run or load test, observed by the UI while it executes."""

    kind: JobKind
    title: str
    command: str
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    started_at: datetime = field(default_factory=datetime.now)
    status: JobStatus = "running"
    lines: list[str] = field(default_factory=list)
    counters: RunCounters = field(default_factory=RunCounters)
    exit_code: int | None = None
    duration_s: float = 0.0
    message: str = ""
    k6_summary: K6Summary | None = None
    stop_requested: bool = False
    _started_monotonic: float = field(default_factory=time.monotonic, repr=False)
    _streamer: LogStreamer | None = field(default=None, repr=False)

    @property
    def running(self) -> bool:
        return self.status == "running"

    @property
    def elapsed_s(self) -> float:
        """Seconds since start (frozen at the final duration once finished)."""
        return time.monotonic() - self._started_monotonic if self.running else self.duration_s

    @property
    def needs_attention(self) -> bool:
        """A finished test run with failures or errors (worth explaining)."""
        return self.kind == "tests" and self.counters.failed + self.counters.errors > 0

    def log_text(self) -> str:
        return "\n".join(self.lines)

    def _append(self, line: str) -> None:
        self.lines.append(line)
        if len(self.lines) > MAX_LOG_LINES:
            del self.lines[: len(self.lines) - MAX_LOG_LINES]

    def _attach(self, streamer: LogStreamer) -> None:
        self._streamer = streamer
        if self.stop_requested:
            streamer.terminate()


class JobBusyError(RuntimeError):
    """Raised when a job is started while another one is still running."""


class JobManager:
    """Owns the current job (at most one runs at a time) and its worker thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: Job | None = None
        self.previous: Job | None = None
        atexit.register(self.stop)

    # --- queries ----------------------------------------------------------

    @property
    def current(self) -> Job | None:
        """The running job, or the most recent finished one."""
        return self._current

    @property
    def busy(self) -> bool:
        job = self._current
        return job is not None and job.running

    # --- commands ---------------------------------------------------------

    def start_tests(self, config: RunConfig, meta: dict[str, Any]) -> Job:
        """Start a pytest run in the background; ``meta`` feeds the run history."""
        job = Job(
            kind="tests",
            title=meta.get("title", "Test run"),
            command=display_command(build_pytest_command(config)),
            meta={**meta, "config": config},
        )
        return self._launch(job, lambda: self._run_tests(job, config))

    def start_k6(self, config: K6Config) -> Job:
        """Start a k6 load test in the background."""
        job = Job(
            kind="k6",
            title=f"Load test · {config.script}",
            command=(
                f"k6 run {config.script}  "
                f"(TARGET_URL={config.target_url}, VUS={config.vus}, "
                f"DURATION={config.duration_s}s)"
            ),
            meta={"config": config},
        )
        return self._launch(job, lambda: self._run_k6(job, config))

    def stop(self) -> None:
        """Ask the running job to stop; its process tree is terminated."""
        job = self._current
        if job is None or not job.running:
            return
        job.stop_requested = True
        if job._streamer is not None:
            job._streamer.terminate()

    # --- internals --------------------------------------------------------

    def _launch(self, job: Job, target: Callable[[], None]) -> Job:
        with self._lock:
            if self.busy:
                raise JobBusyError("Another run is still in progress")
            self.previous, self._current = self._current, job
        threading.Thread(
            target=self._guarded, args=(job, target), name=f"job-{job.id}", daemon=True
        ).start()
        return job

    @staticmethod
    def _guarded(job: Job, target: Callable[[], None]) -> None:
        try:
            target()
        except Exception as exc:  # surface any failure in the UI, never kill the thread
            job.status = "error"
            job.message = f"{type(exc).__name__}: {exc}"
            job._append(f"[dashboard] {job.message}")
        finally:
            if not job.duration_s:
                job.duration_s = time.monotonic() - job._started_monotonic

    @staticmethod
    def _finish_status(job: Job, exit_code: int) -> JobStatus:
        if job.stop_requested:
            return "stopped"
        return "passed" if exit_code == 0 else "failed"

    def _run_tests(self, job: Job, config: RunConfig) -> None:
        def on_line(line: str, counters: RunCounters) -> None:
            job.counters = counters
            job._append(line)

        result = TestExecutor().run(config, on_line=on_line, on_start=job._attach)
        job.counters = result.counters
        job.exit_code = result.exit_code
        job.duration_s = result.duration_s

        job.message = "Generating the Allure report…"
        generated, report_message = allure_service.generate_report()
        job.message = (
            "Allure report regenerated" if generated else f"Allure report: {report_message}"
        )
        status = self._finish_status(job, result.exit_code)
        meta = job.meta
        run_history.append_entry(
            mode=meta.get("mode", "A"),
            target=meta.get("target", "dev"),
            test_types=meta.get("test_types", []),
            browsers=meta.get("browsers", ["chromium"]),
            parallel=config.parallel,
            duration_s=result.duration_s,
            passed=result.counters.passed,
            failed=result.counters.failed + result.counters.errors,
            skipped=result.counters.skipped,
            exit_code=result.exit_code,
            status=status,
        )
        job.status = status

    def _run_k6(self, job: Job, config: K6Config) -> None:
        summary, exit_code, message = k6_service.run_k6(
            config, on_line=job._append, on_start=job._attach
        )
        job.exit_code = exit_code
        job.k6_summary = summary
        job.message = message
        if summary is None and not job.stop_requested:
            job.status = "error"
        else:
            job.status = self._finish_status(job, exit_code)
