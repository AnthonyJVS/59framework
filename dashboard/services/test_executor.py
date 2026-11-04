"""Builds and runs pytest commands from dashboard selections.

Mode routing mirrors the fixture hierarchy in ``tests/conftest.py``:
an explicit target URL becomes ``--base-url`` and the chosen environment
becomes ``--env``. Mode B (Site Scanner) sends only the URL; Mode A sends the
environment, plus the URL when the user pasted one that matched it.
"""

from __future__ import annotations

import re
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from dashboard.utils.log_streamer import LogStreamer

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_STATUS_RE = re.compile(r"\b(PASSED|FAILED|ERROR|SKIPPED)\b")
# Every live per-test status line is emitted before any of pytest's end-of-run
# recap sections. Those recap sections restate the same statuses: "ERRORS" and
# "FAILURES" print an "ERROR at setup of <test>" / test-name subheader per
# item, and `-ra` (see pyproject.toml) reprints every non-passed test again
# under "short test summary info". Stop counting the moment any of these
# banners appears, or FAILED/ERROR/SKIPPED get counted 2-3x over.
_RECAP_HEADER_RE = re.compile(r"^=+\s+(FAILURES|ERRORS|short test summary info)\s+=+\s*$")


@dataclass(frozen=True)
class RunConfig:
    """Everything the dashboard chose for one test run."""

    markers: list[str]
    env_name: str | None = None  # Mode A
    target_url: str | None = None  # Mode B / explicit override
    browsers: list[str] = field(default_factory=lambda: ["chromium"])
    parallel: bool = False
    reruns: int = 0
    scan_depth: int | None = None  # scanner-only knobs
    scan_max_pages: int | None = None
    scan_record_video: bool = False


@dataclass
class RunCounters:
    """Live pass/fail counters parsed from verbose pytest output."""

    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    _in_recap: bool = field(default=False, repr=False, compare=False)

    def observe(self, line: str) -> None:
        """Update counters from one output line."""
        if self._in_recap:
            return
        if _RECAP_HEADER_RE.match(line.strip()):
            self._in_recap = True
            return
        match = _STATUS_RE.search(line)
        if match is None:
            return
        status = match.group(1)
        if status == "PASSED":
            self.passed += 1
        elif status == "FAILED":
            self.failed += 1
        elif status == "ERROR":
            self.errors += 1
        elif status == "SKIPPED":
            self.skipped += 1


@dataclass(frozen=True)
class RunResult:
    """Outcome of a completed run."""

    exit_code: int
    duration_s: float
    counters: RunCounters
    command: list[str]


def build_pytest_command(config: RunConfig) -> list[str]:
    """Translate dashboard selections into a pytest CLI invocation."""
    command = [sys.executable, "-m", "pytest", "-v", "--color=no"]
    if config.markers:
        command += ["-m", " or ".join(config.markers)]
    # Independent flags: a URL that matches a configured environment runs in
    # Mode A with *both*, so that environment's credentials and timeouts apply.
    if config.target_url:
        command.append(f"--base-url={config.target_url}")
    if config.env_name:
        command.append(f"--env={config.env_name}")
    is_scanner_only = config.markers == ["scanner"]
    if not is_scanner_only:  # the scanner drives its own chromium instance
        for browser in config.browsers:
            command += ["--browser", browser]
    if config.parallel:
        command += ["-n", "auto"]
    if config.reruns > 0:
        command.append(f"--reruns={config.reruns}")
    if config.scan_depth is not None:
        command.append(f"--scan-depth={config.scan_depth}")
    if config.scan_max_pages is not None:
        command.append(f"--scan-max-pages={config.scan_max_pages}")
    if config.scan_record_video:
        command.append("--scan-record-video")
    return command


class TestExecutor:
    """Runs pytest with live output streaming."""

    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self.project_root = project_root

    def run(
        self,
        config: RunConfig,
        on_line: Callable[[str, RunCounters], None] | None = None,
    ) -> RunResult:
        """Execute the run, invoking ``on_line`` for every output line."""
        command = build_pytest_command(config)
        counters = RunCounters()
        started = time.monotonic()
        streamer = LogStreamer(command, cwd=self.project_root)
        for line in streamer.stream():
            counters.observe(line)
            if on_line is not None:
                on_line(line, counters)
        return RunResult(
            exit_code=streamer.returncode if streamer.returncode is not None else -1,
            duration_s=time.monotonic() - started,
            counters=counters,
            command=command,
        )

    def stream(self, config: RunConfig) -> Iterator[str]:
        """Lower-level variant: yield raw lines (no counters)."""
        yield from LogStreamer(build_pytest_command(config), cwd=self.project_root).stream()
