"""SauceDemo product detail page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page

from framework.core.base_page import BasePage

if TYPE_CHECKING:
    from framework.pages.inventory_page import InventoryPage


class ProductPage(BasePage):
    """The ``/inventory-item.html`` single-product view."""

    url_path = "/inventory-item.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.name_label = page.locator('[data-test="inventory-item-name"]')
        self.price_label = page.locator('[data-test="inventory-item-price"]')
        self.back_button = page.locator('[data-test="back-to-products"]')

    def ready_locator(self) -> Locator:
        """Rendered once ``back_button`` is visible."""
        return self.back_button

    def product_name(self) -> str:
        """Displayed product name."""
        return self.name_label.inner_text()

    def product_price(self) -> float:
        """Displayed price as a float."""
        return float(self.price_label.inner_text().lstrip("$"))

    def back_to_catalog(self) -> InventoryPage:
        """Return to the inventory page."""
        from framework.pages.inventory_page import InventoryPage

        self.back_button.click()
        return InventoryPage(self.page).wait_until_current()
