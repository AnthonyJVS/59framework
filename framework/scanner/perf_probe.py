"""Lightweight page-load performance signals via the Navigation Timing API.

This is the Site Scanner's built-in perf check; heavier on-demand load tests
run through k6 (see ``dashboard/services/k6_service.py``, Phase 8), which can
reuse the same target URL.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from playwright.sync_api import Error, Page


@dataclass(frozen=True)
class NavigationTiming:
    """Key millisecond marks of one navigation."""

    url: str
    ttfb_ms: float
    dom_content_loaded_ms: float
    load_ms: float


def measure_page_load(page: Page, url: str) -> NavigationTiming:
    """Navigate to ``url`` and read the browser's navigation-timing entry."""
    page.goto(url, wait_until="load")
    # loadEventEnd is 0 until the load handler finishes; give it a moment
    with contextlib.suppress(Error):
        page.wait_for_function(
            "() => performance.getEntriesByType('navigation')[0]?.loadEventEnd > 0",
            timeout=5_000,
        )
    timing = page.evaluate(
        """() => {
            const [nav] = performance.getEntriesByType('navigation');
            if (!nav) return null;
            return {
                ttfb: nav.responseStart,
                domContentLoaded: nav.domContentLoadedEventEnd,
                load: nav.loadEventEnd,
            };
        }"""
    )
    if timing is None:
        raise RuntimeError(f"No navigation-timing entry available for {url}")
    load_ms = timing["load"] or timing["domContentLoaded"]
    return NavigationTiming(
        url=url,
        ttfb_ms=float(timing["ttfb"]),
        dom_content_loaded_ms=float(timing["domContentLoaded"]),
        load_ms=float(load_ms),
    )
