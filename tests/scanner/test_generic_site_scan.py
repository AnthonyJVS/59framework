"""Generic site scan (Mode B): works against any URL, no Page Objects.

Run with e.g.::

    pytest tests/scanner --base-url=https://any.site --scan-depth=1
"""

from __future__ import annotations

import pytest

from tests.scanner.conftest import ScanArtifacts

pytestmark = [pytest.mark.scanner]


def test_no_broken_links(scan_artifacts: ScanArtifacts) -> None:
    """Every same-origin link discovered within the depth limit resolves 2xx/3xx."""
    report = scan_artifacts.report
    assert report.visited_pages, f"Could not open the start page {report.start_url}"
    details = "\n".join(
        f"  {result.status or 'ERR'}  {result.url}"
        f"  (found on {result.found_on or 'start'})"
        + (f"  [{result.error}]" if result.error else "")
        for result in report.broken
    )
    assert not report.broken, (
        f"{len(report.broken)} broken link(s) of {len(report.results)} checked "
        f"on {report.start_url}:\n{details}"
    )


def test_no_console_or_page_errors(scan_artifacts: ScanArtifacts) -> None:
    """No error-severity console output or uncaught JS exceptions while crawling."""
    details = "\n".join(
        f"  [{issue.kind}] on {issue.page_url}: {issue.text[:200]}"
        for issue in scan_artifacts.console_issues
    )
    assert (
        not scan_artifacts.console_issues
    ), f"{len(scan_artifacts.console_issues)} browser error(s) captured:\n{details}"


def test_start_page_loads_within_budget(
    scan_artifacts: ScanArtifacts, request: pytest.FixtureRequest
) -> None:
    """The start page's load event completes inside the configured budget."""
    budget_ms = request.config.getoption("--scan-load-budget-ms")
    timing = scan_artifacts.timing
    assert timing.load_ms <= budget_ms, (
        f"{timing.url} loaded in {timing.load_ms:.0f} ms "
        f"(TTFB {timing.ttfb_ms:.0f} ms, DCL {timing.dom_content_loaded_ms:.0f} ms), "
        f"budget is {budget_ms} ms"
    )
