"""Site Scanner (Mode B) fixtures — deliberately self-contained.

The scanner never reads environment YAMLs or Page Objects: its target comes
exclusively from the explicit override channel (``--base-url`` CLI flag or
``TARGET_URL`` env var). Without a target, scanner tests skip so they can
coexist with Mode A suites in one run. One crawl is shared per session.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import Playwright

from framework.core.driver_factory import DriverFactory
from framework.scanner.console_error_capture import ConsoleErrorCapture, ConsoleIssue
from framework.scanner.link_crawler import CrawlReport, LinkCrawler
from framework.scanner.perf_probe import NavigationTiming, measure_page_load

SCAN_RESULTS_PATH = Path(__file__).resolve().parents[2] / "reports" / "scan_results.json"


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
    browser = DriverFactory.launch_browser(playwright, "chromium", headless=True)
    context = DriverFactory.new_context(browser)
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
    yield artifacts
    browser.close()


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
