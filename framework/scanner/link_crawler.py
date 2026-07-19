"""Generic same-origin link crawler for Site Scanner mode (Mode B).

Selector-agnostic by design: it never imports Page Objects and works against
any URL. Pages within the depth limit are visited in the browser (so console
listeners fire and deeper links are discovered); frontier links at the depth
limit are status-checked over the context's ``APIRequestContext`` without a
full navigation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlparse

from playwright.sync_api import Error, Page

from framework.utils.logger import get_logger

log = get_logger("scanner")

#: goto() failures that mean "not a navigable page", not "broken link" —
#: fall back to a plain HTTP check instead of flagging.
_NON_PAGE_NAVIGATION_ERRORS = ("Download is starting", "ERR_ABORTED")


@dataclass(frozen=True)
class LinkResult:
    """Outcome of checking one URL."""

    url: str
    status: int  # 0 when the request itself failed
    ok: bool  # final response was 2xx/3xx
    found_on: str | None  # page on which the link was discovered
    error: str | None = None


@dataclass
class CrawlReport:
    """Aggregated result of one crawl."""

    start_url: str
    max_depth: int
    visited_pages: list[str] = field(default_factory=list)
    results: list[LinkResult] = field(default_factory=list)

    @property
    def broken(self) -> list[LinkResult]:
        """Every checked link whose final response was not 2xx/3xx."""
        return [result for result in self.results if not result.ok]


def _normalize(url: str) -> str:
    """Drop fragments so ``/page#a`` and ``/page#b`` count as one URL."""
    return urldefrag(url)[0]


def _same_origin(url: str, origin_url: str) -> bool:
    """True when scheme and host match the crawl origin."""
    candidate, origin = urlparse(url), urlparse(origin_url)
    return candidate.scheme in ("http", "https") and candidate.netloc == origin.netloc


class LinkCrawler:
    """Breadth-first, depth-limited crawler over one origin."""

    def __init__(
        self,
        page: Page,
        max_depth: int = 1,
        max_pages: int = 15,
        request_timeout_ms: int = 15_000,
    ) -> None:
        self.page = page
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.request_timeout_ms = request_timeout_ms

    def crawl(self, start_url: str) -> CrawlReport:
        """Crawl from ``start_url``, returning statuses for every link seen."""
        start = _normalize(start_url)
        report = CrawlReport(start_url=start, max_depth=self.max_depth)
        queue: deque[tuple[str, int, str | None]] = deque([(start, 0, None)])
        seen: set[str] = {start}

        while queue:
            url, depth, found_on = queue.popleft()
            expandable = depth < self.max_depth and len(report.visited_pages) < self.max_pages
            if expandable or depth == 0:
                result, links = self._visit(url, found_on)
                if result.ok:
                    report.visited_pages.append(url)
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        queue.append((link, depth + 1, url))
            else:
                result = self._check(url, found_on)
            report.results.append(result)

        log.info(
            "Crawl of %s: %d pages visited, %d links checked, %d broken",
            start,
            len(report.visited_pages),
            len(report.results),
            len(report.broken),
        )
        return report

    def _visit(self, url: str, found_on: str | None) -> tuple[LinkResult, list[str]]:
        """Open a page in the browser; return its status and same-origin links."""
        try:
            response = self.page.goto(url, wait_until="load")
        except Error as exc:
            message = str(exc).splitlines()[0]
            if any(marker in message for marker in _NON_PAGE_NAVIGATION_ERRORS):
                return self._check(url, found_on), []
            return LinkResult(url, 0, False, found_on, error=message), []
        if response is None:  # e.g. about:blank or same-page anchor
            return LinkResult(url, 0, True, found_on), []
        if not response.ok:
            return LinkResult(url, response.status, False, found_on), []
        return LinkResult(url, response.status, True, found_on), self._extract_links(url)

    def _check(self, url: str, found_on: str | None) -> LinkResult:
        """HTTP-check a link without navigating (redirects followed)."""
        try:
            response = self.page.context.request.get(url, timeout=self.request_timeout_ms)
        except Error as exc:
            return LinkResult(url, 0, False, found_on, error=str(exc).splitlines()[0])
        return LinkResult(url, response.status, response.ok, found_on)

    def _extract_links(self, page_url: str) -> list[str]:
        """Absolute, fragment-free, same-origin links on the current page."""
        hrefs: list[str] = self.page.eval_on_selector_all(
            "a[href]", "elements => elements.map(e => e.href)"
        )
        unique: dict[str, None] = {}
        for href in hrefs:
            normalized = _normalize(href)
            if normalized and _same_origin(normalized, page_url):
                unique.setdefault(normalized, None)
        return list(unique)
