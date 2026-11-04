"""Generic link crawler for Site Scanner mode (Mode B).

Selector-agnostic by design: it never imports Page Objects and works against
any URL. Same-origin pages within the depth limit are visited in the browser
(so console listeners fire and deeper links are discovered). Every other link
— the same-origin frontier at the depth limit and, optionally, external links
— is only status-checked over plain HTTP, concurrently, without a navigation.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from collections import deque
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urlparse

from playwright.sync_api import Error, Page

from framework.utils.logger import get_logger

log = get_logger("scanner")

#: goto() failures that mean "not a navigable page", not "broken link" —
#: fall back to a plain HTTP check instead of flagging.
_NON_PAGE_NAVIGATION_ERRORS = ("Download is starting", "ERR_ABORTED")

#: Statuses with which some servers refuse HEAD but serve GET fine.
_RETRY_WITH_GET = {403, 405, 501}

USER_AGENT = "Mozilla/5.0 (compatible; 59framework-site-scanner/1.0; +link status check)"


@dataclass(frozen=True)
class LinkResult:
    """Outcome of checking one URL."""

    url: str
    status: int  # 0 when the request itself failed
    ok: bool  # final response was 2xx/3xx
    found_on: str | None  # page on which the link was discovered
    error: str | None = None
    external: bool = False  # different origin than the start page


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


def _is_http(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def _same_origin(url: str, origin_url: str) -> bool:
    """True when scheme and host match the crawl origin."""
    candidate, origin = urlparse(url), urlparse(origin_url)
    return candidate.scheme in ("http", "https") and candidate.netloc == origin.netloc


def http_status(url: str, timeout_s: float = 15.0) -> tuple[int, str | None]:
    """Status of ``url`` after redirects: ``(status, error)``; status 0 = no response.

    Tries HEAD first (cheap) and falls back to GET for servers that reject it.
    """
    status, error = 0, None
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                return response.status, None
        except urllib.error.HTTPError as exc:
            status, error = exc.code, None
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            status, error = 0, str(reason).splitlines()[0] if str(reason) else type(exc).__name__
        if method == "HEAD" and (status in _RETRY_WITH_GET or status == 0):
            continue
        break
    return status, error


def check_links(
    links: Iterable[tuple[str, str | None, bool]],
    workers: int = 8,
    timeout_s: float = 15.0,
) -> list[LinkResult]:
    """HTTP-check ``(url, found_on, external)`` triples concurrently, in input order."""
    items = list(links)
    if not items:
        return []

    def _one(item: tuple[str, str | None, bool]) -> LinkResult:
        url, found_on, external = item
        status, error = http_status(url, timeout_s)
        ok = 200 <= status < 400
        return LinkResult(url, status, ok, found_on, error=error, external=external)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        return list(pool.map(_one, items))


class LinkCrawler:
    """Breadth-first, depth-limited crawler over one origin."""

    def __init__(
        self,
        page: Page,
        max_depth: int = 1,
        max_pages: int = 15,
        request_timeout_ms: int = 15_000,
        check_external: bool = False,
        workers: int = 8,
    ) -> None:
        self.page = page
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.request_timeout_ms = request_timeout_ms
        self.check_external = check_external
        self.workers = workers

    def crawl(self, start_url: str) -> CrawlReport:
        """Crawl from ``start_url``, returning statuses for every link seen."""
        start = _normalize(start_url)
        report = CrawlReport(start_url=start, max_depth=self.max_depth)
        queue: deque[tuple[str, int, str | None]] = deque([(start, 0, None)])
        seen: set[str] = {start}
        to_check: list[tuple[str, str | None, bool]] = []

        while queue:
            url, depth, found_on = queue.popleft()
            expandable = depth < self.max_depth and len(report.visited_pages) < self.max_pages
            if not (expandable or depth == 0):
                to_check.append((url, found_on, False))
                continue
            result, links = self._visit(url, found_on)
            report.results.append(result)
            if result.ok:
                report.visited_pages.append(url)
            for link in links:
                if link in seen:
                    continue
                seen.add(link)
                if _same_origin(link, start):
                    queue.append((link, depth + 1, url))
                elif self.check_external:
                    to_check.append((link, url, True))

        report.results.extend(
            check_links(to_check, workers=self.workers, timeout_s=self.request_timeout_ms / 1000)
        )
        log.info(
            "Crawl of %s: %d pages visited, %d links checked, %d broken",
            start,
            len(report.visited_pages),
            len(report.results),
            len(report.broken),
        )
        return report

    def _visit(self, url: str, found_on: str | None) -> tuple[LinkResult, list[str]]:
        """Open a page in the browser; return its status and the links on it."""
        try:
            response = self.page.goto(url, wait_until="load")
        except Error as exc:
            message = str(exc).splitlines()[0]
            if any(marker in message for marker in _NON_PAGE_NAVIGATION_ERRORS):
                return check_links([(url, found_on, False)], workers=1)[0], []
            return LinkResult(url, 0, False, found_on, error=message), []
        if response is None:  # e.g. about:blank or same-page anchor
            return LinkResult(url, 0, True, found_on), []
        if not response.ok:
            return LinkResult(url, response.status, False, found_on), []
        return LinkResult(url, response.status, True, found_on), self._extract_links()

    def _extract_links(self) -> list[str]:
        """Absolute, fragment-free http(s) links on the current page (any origin)."""
        hrefs: list[str] = self.page.eval_on_selector_all(
            "a[href]", "elements => elements.map(e => e.href)"
        )
        unique: dict[str, None] = {}
        for href in hrefs:
            normalized = _normalize(href)
            if normalized and _is_http(normalized):
                unique.setdefault(normalized, None)
        return list(unique)
