"""Site Scanner (Mode B) fixtures — deliberately self-contained.

The scanner never reads environment YAMLs or Page Objects: its target comes
exclusively from the explicit override channel (``--base-url`` CLI flag or
``TARGET_URL`` env var). Without a target, scanner tests skip so they can
coexist with Mode A suites in one run. One crawl is shared per session.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from playwright.sync_api import Playwright

from framework.core.driver_factory import DriverFactory
from framework.scanner.console_error_capture import ConsoleErrorCapture, ConsoleIssue
from framework.scanner.link_crawler import CrawlReport, LinkCrawler
from framework.scanner.perf_probe import NavigationTiming, measure_page_load


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
    yield ScanArtifacts(report=report, console_issues=list(capture.issues), timing=timing)
    browser.close()
