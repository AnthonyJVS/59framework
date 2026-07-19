"""SauceDemo checkout pages: information form, order overview, confirmation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from playwright.sync_api import Page

from framework.core.base_page import BasePage
from framework.utils.data_generator import CheckoutInfo

if TYPE_CHECKING:
    from framework.pages.cart_page import CartPage
    from framework.pages.inventory_page import InventoryPage


def _money(text: str) -> float:
    """Extract the dollar amount from labels like ``Item total: $39.98``."""
    match = re.search(r"\$([0-9.]+)", text)
    if match is None:
        raise ValueError(f"No dollar amount found in {text!r}")
    return float(match.group(1))


class CheckoutInfoPage(BasePage):
    """Step one (``/checkout-step-one.html``): buyer information form."""

    url_path = "/checkout-step-one.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.first_name_input = page.locator('[data-test="firstName"]')
        self.last_name_input = page.locator('[data-test="lastName"]')
        self.postal_code_input = page.locator('[data-test="postalCode"]')
        self.continue_button = page.locator('[data-test="continue"]')
        self.cancel_button = page.locator('[data-test="cancel"]')
        self.error_banner = page.locator('[data-test="error"]')

    def fill_info(self, info: CheckoutInfo) -> None:
        """Fill the buyer information form (empty strings are left blank)."""
        self.first_name_input.fill(info.first_name)
        self.last_name_input.fill(info.last_name)
        self.postal_code_input.fill(info.postal_code)

    def submit(self, info: CheckoutInfo) -> CheckoutOverviewPage:
        """Fill and submit expecting success; returns the overview page."""
        self.fill_info(info)
        self.continue_button.click()
        return CheckoutOverviewPage(self.page)

    def submit_expecting_error(self, info: CheckoutInfo) -> str:
        """Fill and submit expecting a validation error; returns its text."""
        self.fill_info(info)
        self.continue_button.click()
        return self.error_banner.inner_text()

    def cancel(self) -> CartPage:
        """Abort checkout; returns to the cart."""
        from framework.pages.cart_page import CartPage

        self.cancel_button.click()
        return CartPage(self.page)


class CheckoutOverviewPage(BasePage):
    """Step two (``/checkout-step-two.html``): order summary."""

    url_path = "/checkout-step-two.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.item_names = page.locator('[data-test="inventory-item-name"]')
        self.item_prices = page.locator('[data-test="inventory-item-price"]')
        self.subtotal_label = page.locator('[data-test="subtotal-label"]')
        self.tax_label = page.locator('[data-test="tax-label"]')
        self.total_label = page.locator('[data-test="total-label"]')
        self.finish_button = page.locator('[data-test="finish"]')
        self.cancel_button = page.locator('[data-test="cancel"]')

    def listed_names(self) -> list[str]:
        """Names of the items in the order summary."""
        return self.item_names.all_inner_texts()

    def listed_prices(self) -> list[float]:
        """Prices of the items in the order summary as floats."""
        return [float(text.lstrip("$")) for text in self.item_prices.all_inner_texts()]

    def subtotal(self) -> float:
        """Item total before tax."""
        return _money(self.subtotal_label.inner_text())

    def tax(self) -> float:
        """Tax amount."""
        return _money(self.tax_label.inner_text())

    def total(self) -> float:
        """Grand total."""
        return _money(self.total_label.inner_text())

    def finish(self) -> CheckoutCompletePage:
        """Place the order; returns the confirmation page."""
        self.finish_button.click()
        return CheckoutCompletePage(self.page)

    def cancel(self) -> None:
        """Abort checkout from the overview (returns to the catalog)."""
        self.cancel_button.click()


class CheckoutCompletePage(BasePage):
    """Confirmation (``/checkout-complete.html``)."""

    url_path = "/checkout-complete.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.header = page.locator('[data-test="complete-header"]')
        self.back_home_button = page.locator('[data-test="back-to-products"]')

    def confirmation_text(self) -> str:
        """The big thank-you headline."""
        return self.header.inner_text()

    def back_home(self) -> InventoryPage:
        """Return to the catalog."""
        from framework.pages.inventory_page import InventoryPage

        self.back_home_button.click()
        return InventoryPage(self.page)
