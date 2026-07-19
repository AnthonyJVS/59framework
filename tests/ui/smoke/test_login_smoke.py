"""Smoke: login page renders and the critical login flow works."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from playwright.sync_api import expect

from framework.pages.login_page import LoginPage

pytestmark = [pytest.mark.smoke, pytest.mark.ui]


def test_login_page_shows_critical_elements(login_page: LoginPage) -> None:
    """Username, password and submit controls are all present."""
    expect(login_page.username_input).to_be_visible()
    expect(login_page.password_input).to_be_visible()
    expect(login_page.login_button).to_be_enabled()


@pytest.mark.cross_browser
def test_standard_user_can_login(login_page: LoginPage, credentials: Mapping[str, str]) -> None:
    """Valid credentials land on the catalog with products rendered."""
    inventory = login_page.login(credentials["username"], credentials["password"])
    assert inventory.is_current(), "Login did not land on the inventory page"
    expect(inventory.items.first).to_be_visible()
