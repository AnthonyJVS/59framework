"""UI-suite fixtures: page objects pre-wired with environment credentials."""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from playwright.sync_api import Page

from config.config_loader import EnvironmentConfig
from framework.pages.inventory_page import InventoryPage
from framework.pages.login_page import LoginPage
from framework.utils.data_generator import CheckoutInfo, DataGenerator


@pytest.fixture
def credentials(env_config: EnvironmentConfig) -> Mapping[str, str]:
    """Credentials block of the active environment."""
    return env_config.credentials


@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """The login page, already opened."""
    return LoginPage(page).navigate()


@pytest.fixture
def inventory_page(login_page: LoginPage, credentials: Mapping[str, str]) -> InventoryPage:
    """The catalog page, reached by logging in as the standard user."""
    return login_page.login(credentials["username"], credentials["password"])


@pytest.fixture
def checkout_data() -> CheckoutInfo:
    """Random-but-valid buyer details for checkout forms."""
    return DataGenerator().checkout_info()
