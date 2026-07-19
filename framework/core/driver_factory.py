"""Centralised browser launch / context option factory.

pytest-playwright owns the browser lifecycle for test runs; this factory is
the single place where launch and context options are decided, so the pytest
fixtures, the Site Scanner and the Streamlit dashboard all create identical
browsers. Standalone helpers (:meth:`DriverFactory.launch_browser` /
:meth:`DriverFactory.new_context`) exist for code paths that run outside
pytest, e.g. dashboard-triggered scans.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Browser, BrowserContext, Playwright

SUPPORTED_BROWSERS: tuple[str, ...] = ("chromium", "firefox", "webkit")
DEFAULT_VIEWPORT: dict[str, int] = {"width": 1440, "height": 900}


class DriverFactory:
    """Builds Playwright launch/context arguments from framework config."""

    @staticmethod
    def launch_args(headless: bool = True, slow_mo_ms: int = 0) -> dict[str, Any]:
        """Arguments for ``browser_type.launch()``."""
        return {"headless": headless, "slow_mo": slow_mo_ms}

    @staticmethod
    def context_args(
        base_url: str | None = None,
        viewport: dict[str, int] | None = None,
        ignore_https_errors: bool = False,
        **extra: Any,
    ) -> dict[str, Any]:
        """Arguments for ``browser.new_context()`` / pytest-playwright's
        ``browser_context_args`` fixture."""
        args: dict[str, Any] = {
            "viewport": viewport or dict(DEFAULT_VIEWPORT),
            "ignore_https_errors": ignore_https_errors,
            **extra,
        }
        if base_url:
            args["base_url"] = base_url
        return args

    @staticmethod
    def launch_browser(
        playwright: Playwright,
        browser_name: str = "chromium",
        headless: bool = True,
        slow_mo_ms: int = 0,
    ) -> Browser:
        """Launch a browser by name — for use outside the pytest fixture chain."""
        if browser_name not in SUPPORTED_BROWSERS:
            raise ValueError(
                f"Unsupported browser '{browser_name}'. Supported: {SUPPORTED_BROWSERS}"
            )
        browser_type = getattr(playwright, browser_name)
        return browser_type.launch(**DriverFactory.launch_args(headless, slow_mo_ms))

    @staticmethod
    def new_context(
        browser: Browser,
        base_url: str | None = None,
        default_timeout_ms: int | None = None,
        **overrides: Any,
    ) -> BrowserContext:
        """Create a context with framework defaults — for use outside pytest."""
        context = browser.new_context(**DriverFactory.context_args(base_url, **overrides))
        if default_timeout_ms is not None:
            context.set_default_timeout(default_timeout_ms)
        return context
