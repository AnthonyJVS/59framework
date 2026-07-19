"""Console / uncaught-exception capture for Site Scanner mode (Mode B).

Attaches to Playwright's ``console`` and ``pageerror`` events; completely
independent of Page Objects and app-specific selectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Self

from playwright.sync_api import ConsoleMessage, Error, Page

IssueKind = Literal["console-error", "page-error"]


@dataclass(frozen=True)
class ConsoleIssue:
    """One captured browser-side error."""

    kind: IssueKind
    page_url: str
    text: str


class ConsoleErrorCapture:
    """Records error-severity console messages and uncaught JS exceptions."""

    def __init__(self, page: Page) -> None:
        self._page = page
        self.issues: list[ConsoleIssue] = []

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

    def _on_console(self, message: ConsoleMessage) -> None:
        if message.type == "error":
            self.issues.append(ConsoleIssue("console-error", self._page.url, message.text))

    def _on_page_error(self, error: Error) -> None:
        self.issues.append(ConsoleIssue("page-error", self._page.url, str(error)))
