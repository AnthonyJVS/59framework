"""Generic line-by-line subprocess streaming for the dashboard.

Used by the test executor (pytest) and the k6 service so both stream output
into the UI the same way.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator, Mapping
from pathlib import Path

#: How long a stopped process gets to exit on its own before it is killed.
_TERMINATE_GRACE_S = 5.0


class LogStreamer:
    """Runs a command and yields decoded output lines as they arrive.

    If the consumer stops iterating early — e.g. Streamlit interrupts the
    script because the user clicked something mid-run — the process tree is
    stopped instead of being left running (or waited on) in the background.
    """

    def __init__(
        self,
        command: list[str],
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.env = dict(env) if env is not None else None
        self._process: subprocess.Popen[str] | None = None

    def stream(self) -> Iterator[str]:
        """Start the process and yield stdout+stderr lines until it exits."""
        self._process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert self._process.stdout is not None
        finished = False
        try:
            yield from (line.rstrip("\r\n") for line in self._process.stdout)
            finished = True
        finally:
            # Only an abandoned stream is stopped: after EOF the process may
            # still be flushing, and killing it would clobber its exit code.
            if not finished:
                self.terminate()
            self._process.stdout.close()
            self._process.wait()

    @property
    def returncode(self) -> int | None:
        """Exit code once the stream is exhausted; None while running."""
        return self._process.returncode if self._process else None

    def terminate(self) -> None:
        """Stop a still-running process and its children (no-op once it exited).

        pytest-xdist workers and Playwright browsers are child processes, so on
        Windows the whole tree is taken down with ``taskkill /T``; elsewhere the
        parent gets SIGTERM, then SIGKILL after a grace period.
        """
        process = self._process
        if process is None or process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                capture_output=True,
                check=False,
            )
            return
        process.terminate()
        try:
            process.wait(timeout=_TERMINATE_GRACE_S)
        except subprocess.TimeoutExpired:
            process.kill()
