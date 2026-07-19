"""SauceDemo login page."""

from __future__ import annotations

from playwright.sync_api import Page

from framework.core.base_page import BasePage
from framework.pages.inventory_page import InventoryPage


class LoginPage(BasePage):
    """The ``/`` login form."""

    url_path = "/"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username_input = page.locator('[data-test="username"]')
        self.password_input = page.locator('[data-test="password"]')
        self.login_button = page.locator('[data-test="login-button"]')
        self.error_banner = page.locator('[data-test="error"]')

    def submit_credentials(self, username: str, password: str) -> None:
        """Fill and submit the form without asserting the outcome."""
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def login(self, username: str, password: str) -> InventoryPage:
        """Log in expecting success; returns the landing (inventory) page."""
        self.submit_credentials(username, password)
        return InventoryPage(self.page)

    def login_expecting_error(self, username: str, password: str) -> str:
        """Log in expecting failure; returns the displayed error text."""
        self.submit_credentials(username, password)
        return self.error_text()

    def error_text(self) -> str:
        """Text of the red error banner (waits for it to appear)."""
        return self.error_banner.inner_text()
