"""Allure report generation and local serving for the dashboard.

The generated report is static HTML that cannot be iframed from disk, so a
tiny daemon-thread HTTP server serves ``reports/allure-report`` on
localhost; the Streamlit tab embeds that URL.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "reports" / "allure-results"
REPORT_DIR = PROJECT_ROOT / "reports" / "allure-report"
REPORT_PORT = 8899


def allure_available() -> bool:
    """Whether the Allure commandline is on PATH."""
    return shutil.which("allure") is not None


def has_results() -> bool:
    """Whether any test results exist to build a report from."""
    return RESULTS_DIR.is_dir() and any(RESULTS_DIR.glob("*.json"))


def generate_report() -> tuple[bool, str]:
    """Regenerate the HTML report from the latest results."""
    executable = shutil.which("allure")
    if executable is None:
        return False, "Allure commandline not found on PATH (npm i -g allure-commandline)"
    if not has_results():
        return False, f"No test results in {RESULTS_DIR} — run some tests first"
    completed = subprocess.run(
        [executable, "generate", str(RESULTS_DIR), "-o", str(REPORT_DIR), "--clean"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if completed.returncode != 0:
        return False, completed.stderr.strip() or completed.stdout.strip()
    return True, f"Report generated at {REPORT_DIR}"


def report_summary() -> dict[str, Any] | None:
    """Quick stats from the generated report's summary widget, if present."""
    summary_path = REPORT_DIR / "widgets" / "summary.json"
    if not summary_path.is_file():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


class _NoCacheHandler(SimpleHTTPRequestHandler):
    """Static file handler that forbids caching so regenerated reports show up."""

    def end_headers(self) -> None:  # noqa: N802 (http.server naming)
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # keep Streamlit's console quiet


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex(("127.0.0.1", port)) == 0


def ensure_report_server(port: int = REPORT_PORT) -> str:
    """Serve the report directory on localhost (idempotent); returns its URL.

    The URL carries the report's mtime as a cache-buster so an embedded
    iframe reloads after every regeneration.
    """
    if not _port_in_use(port):
        handler = partial(_NoCacheHandler, directory=str(REPORT_DIR))
        server = ThreadingHTTPServer(("127.0.0.1", port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    index = REPORT_DIR / "index.html"
    stamp = int(index.stat().st_mtime) if index.is_file() else 0
    return f"http://127.0.0.1:{port}/index.html?v={stamp}"
