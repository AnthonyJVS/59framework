"""Generic line-by-line subprocess streaming for the dashboard.

Used by the test executor (pytest) and the k6 service so both stream output
into the UI the same way.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator, Mapping
from pathlib import Path


class LogStreamer:
    """Runs a command and yields decoded output lines as they arrive."""

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
        try:
            yield from (line.rstrip("\r\n") for line in self._process.stdout)
        finally:
            self._process.stdout.close()
            self._process.wait()

    @property
    def returncode(self) -> int | None:
        """Exit code once the stream is exhausted; None while running."""
        return self._process.returncode if self._process else None

    def terminate(self) -> None:
        """Best-effort stop of a running process."""
        if self._process and self._process.poll() is None:
            self._process.terminate()
