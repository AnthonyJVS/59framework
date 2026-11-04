"""Console / uncaught-exception capture for Site Scanner mode (Mode B).

Attaches to Playwright's ``console`` and ``pageerror`` events; completely
independent of Page Objects and app-specific selectors.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Self
from urllib.parse import urlparse

from playwright.sync_api import ConsoleMessage, Error, Page

IssueKind = Literal["console-error", "page-error"]


@dataclass(frozen=True)
class ConsoleIssue:
    """One captured browser-side error."""

    kind: IssueKind
    page_url: str
    text: str
    #: Script/resource that emitted the message, when the browser reports one.
    source_url: str = ""

    @property
    def third_party(self) -> bool:
        """Emitted by a script from another origin than the page (ads, widgets…)."""
        if not self.source_url:
            return False
        return urlparse(self.source_url).netloc != urlparse(self.page_url).netloc


class ConsoleErrorCapture:
    """Records error-severity console messages and uncaught JS exceptions.

    ``ignore`` takes regular expressions; a message matching any of them (for
    example known third-party noise) is not recorded.
    """

    def __init__(self, page: Page, ignore: Iterable[str] = ()) -> None:
        self._page = page
        self._ignore = [re.compile(pattern) for pattern in ignore]
        self.issues: list[ConsoleIssue] = []
        self.ignored_count = 0

    def attach(self) -> Self:
        """Start listening; safe to call once per page."""
        self._page.on("console", self._on_console)
        self._page.on("pageerror", self._on_page_error)
        return self

    def detach(self) -> None:
        """Stop listening (captured issues are kept)."""
        self._page.remove_listener("console", self._on_console)
        self._page.remove_listener("pageerror", self._on_page_error)

    def issues_for(self, page_url: str) -> list[ConsoleIssue]:
        """Issues captured while the given URL was open."""
        return [issue for issue in self.issues if issue.page_url == page_url]

    def _record(self, issue: ConsoleIssue) -> None:
        if any(pattern.search(issue.text) for pattern in self._ignore):
            self.ignored_count += 1
            return
        self.issues.append(issue)

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            location = message.location or {}
            self._record(
                ConsoleIssue("console-error", self._page.url, message.text, location.get("url", ""))
            )

    def _on_page_error(self, error: Error) -> None:
        self._record(ConsoleIssue("page-error", self._page.url, str(error)))
