"""Regression: login validation, lockout and logout flows."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from playwright.sync_api import expect

from framework.pages.inventory_page import InventoryPage
from framework.pages.login_page import LoginPage

pytestmark = [pytest.mark.regression, pytest.mark.ui]


def test_wrong_password_shows_error(login_page: LoginPage, credentials: Mapping[str, str]) -> None:
    """A bad password is rejected with the do-not-match error."""
    error = login_page.login_expecting_error(credentials["username"], "definitely-wrong")
    assert "do not match" in error


def test_locked_out_user_is_blocked(login_page: LoginPage, credentials: Mapping[str, str]) -> None:
    """The locked account is refused with a lockout message."""
    error = login_page.login_expecting_error(
        credentials["locked_username"], credentials["password"]
    )
    assert "locked out" in error


def test_empty_username_shows_error(login_page: LoginPage, credentials: Mapping[str, str]) -> None:
    """Submitting without a username reports it as required."""
    error = login_page.login_expecting_error("", credentials["password"])
    assert "Username is required" in error


def test_empty_password_shows_error(login_page: LoginPage, credentials: Mapping[str, str]) -> None:
    """Submitting without a password reports it as required."""
    error = login_page.login_expecting_error(credentials["username"], "")
    assert "Password is required" in error


def test_logout_returns_to_login(inventory_page: InventoryPage) -> None:
    """Logging out through the burger menu lands back on the login form."""
    login = inventory_page.logout()
    expect(login.login_button).to_be_visible()
    assert login.is_current(), "Logout did not return to the login page"
