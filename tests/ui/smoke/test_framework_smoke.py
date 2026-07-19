"""Phase 1 sanity check: the fixture chain resolves a base URL and opens it.

Deliberately selector-free — it must pass against any configured target app.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.smoke, pytest.mark.ui]


def test_base_url_resolves_and_page_opens(page: Page, base_url: str) -> None:
    """The resolved base_url loads with a 2xx/3xx response and renders a title."""
    response = page.goto("/")
    assert response is not None, f"No response object returned for {base_url}"
    assert response.ok, f"{base_url} answered HTTP {response.status}"
    assert page.title().strip(), f"{base_url} rendered an empty <title>"


def test_api_base_url_is_resolved(api_base_url: str) -> None:
    """The API base URL resolves through the same hierarchy and looks like a URL."""
    assert api_base_url.startswith(("http://", "https://"))
