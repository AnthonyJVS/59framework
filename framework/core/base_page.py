"""Base class for all Page Objects.

Playwright auto-waits on every action, so the helpers here stay deliberately
thin: navigation relative to the context ``base_url``, load-state waiting and
shared conveniences. App-specific selectors belong exclusively in subclasses —
never in test files (strict POM).
"""

from __future__ import annotations

from typing import Self
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page


class BasePage:
    """Common behaviour shared by every Page Object."""

    #: Path of the page relative to the context ``base_url``.
    url_path: str = "/"

    def __init__(self, page: Page) -> None:
        self.page = page

    def navigate(self) -> Self:
        """Open this page via its ``url_path`` (resolved against ``base_url``)."""
        self.page.goto(self.url_path)
        return self

    def wait_loaded(self) -> Self:
        """Wait for the default ``load`` state."""
        self.page.wait_for_load_state()
        return self

    @property
    def current_path(self) -> str:
        """Path component of the browser's current URL."""
        return urlparse(self.page.url).path

    def is_current(self) -> bool:
        """Whether the browser is currently on this page's ``url_path``."""
        return self.current_path == urlparse(self.url_path).path

    def locator(self, selector: str) -> Locator:
        """Shorthand for ``page.locator`` scoped helpers in subclasses."""
        return self.page.locator(selector)
