"""Site Scanner (Mode B) fixtures — deliberately self-contained.

The scanner never reads environment YAMLs or Page Objects: its target comes
exclusively from the explicit override channel (``--base-url`` CLI flag or
``TARGET_URL`` env var). Without a target, scanner tests skip so they can
coexist with Mode A suites in one run. One crawl is shared per session.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Generator
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Playwright, Video

from framework.core.driver_factory import DriverFactory
from framework.scanner.console_error_capture import ConsoleErrorCapture, ConsoleIssue
from framework.scanner.link_crawler import CrawlReport, LinkCrawler
from framework.scanner.perf_probe import NavigationTiming, measure_page_load

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
SCAN_RESULTS_PATH = REPORTS_DIR / "scan_results.json"
SCAN_VIDEO_PATH = REPORTS_DIR / "scan_video.webm"
SCAN_VIDEO_TMP_DIR = REPORTS_DIR / "_scan_video_tmp"


@dataclass(frozen=True)
class ScanArtifacts:
    """Everything one scan produced, shared by all scanner tests."""

    report: CrawlReport
    console_issues: list[ConsoleIssue]
    timing: NavigationTiming


@pytest.fixture(scope="session")
def scan_target_url(request: pytest.FixtureRequest) -> str:
    """The arbitrary URL to scan; skips the suite when none was supplied."""
    explicit = request.config.getoption("--base-url") or os.environ.get("TARGET_URL")
    if not explicit:
        pytest.skip("Site Scanner needs an explicit target URL (--base-url or TARGET_URL)")
    return explicit.rstrip("/")


@pytest.fixture(scope="session")
def scan_artifacts(
    playwright: Playwright, scan_target_url: str, request: pytest.FixtureRequest
) -> Generator[ScanArtifacts, None, None]:
    """Run one crawl (with console capture) and measure the start page once."""
    record_video = request.config.getoption("--scan-record-video")
    browser = DriverFactory.launch_browser(playwright, "chromium", headless=True)
    context = DriverFactory.new_context(
        browser,
        record_video_dir=str(SCAN_VIDEO_TMP_DIR) if record_video else None,
    )
    page = context.new_page()
    capture = ConsoleErrorCapture(page).attach()
    crawler = LinkCrawler(
        page,
        max_depth=request.config.getoption("--scan-depth"),
        max_pages=request.config.getoption("--scan-max-pages"),
    )
    report = crawler.crawl(scan_target_url)
    timing = measure_page_load(page, scan_target_url)
    artifacts = ScanArtifacts(report=report, console_issues=list(capture.issues), timing=timing)
    _export_scan_results(artifacts)
    video = page.video if record_video else None
    yield artifacts
    browser.close()
    if video is not None:
        _save_scan_video(video)


def _save_scan_video(video: Video) -> None:
    """Move the crawl's recording to the fixed "latest" path, replacing any prior one.

    ``Video.path()`` blocks until Playwright has finished writing the file,
    which only happens once the owning browser/context has closed. On
    Windows, the browser process can hold the file handle for a brief moment
    even after ``close()`` returns, so the rename is retried.
    """
    recorded_path = Path(video.path())
    SCAN_VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
    last_error: OSError | None = None
    for _ in range(10):
        try:
            recorded_path.replace(SCAN_VIDEO_PATH)
            break
        except OSError as exc:
            last_error = exc
            time.sleep(0.3)
    else:
        raise RuntimeError(f"Could not save scan video: {last_error}") from last_error
    shutil.rmtree(SCAN_VIDEO_TMP_DIR, ignore_errors=True)


def _export_scan_results(artifacts: ScanArtifacts) -> None:
    """Persist the scan as JSON for the dashboard's Scan Results tab."""
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "start_url": artifacts.report.start_url,
        "max_depth": artifacts.report.max_depth,
        "visited_pages": artifacts.report.visited_pages,
        "results": [asdict(result) for result in artifacts.report.results],
        "console_issues": [asdict(issue) for issue in artifacts.console_issues],
        "timing": asdict(artifacts.timing),
    }
    SCAN_RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
