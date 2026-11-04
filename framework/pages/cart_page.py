"""SauceDemo shopping cart page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import Locator, Page

from framework.core.base_page import BasePage
from framework.pages.inventory_page import product_slug

if TYPE_CHECKING:
    from framework.pages.checkout_page import CheckoutInfoPage
    from framework.pages.inventory_page import InventoryPage


class CartPage(BasePage):
    """The ``/cart.html`` shopping cart."""

    url_path = "/cart.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.items = page.locator('[data-test="inventory-item"]')
        self.item_names = page.locator('[data-test="inventory-item-name"]')
        self.item_prices = page.locator('[data-test="inventory-item-price"]')
        self.checkout_button = page.locator('[data-test="checkout"]')
        self.continue_shopping_button = page.locator('[data-test="continue-shopping"]')

    def ready_locator(self) -> Locator:
        """Rendered once ``checkout_button`` is visible."""
        return self.checkout_button

    def item_count(self) -> int:
        """Number of line items in the cart."""
        return self.items.count()

    def listed_names(self) -> list[str]:
        """Names of the items in the cart, in display order."""
        return self.item_names.all_inner_texts()

    def listed_prices(self) -> list[float]:
        """Prices of the items in the cart as floats, in display order."""
        return [float(text.lstrip("$")) for text in self.item_prices.all_inner_texts()]

    def remove(self, name: str) -> None:
        """Remove the named product from the cart."""
        self.locator(f'[data-test="remove-{product_slug(name)}"]').click()

    def start_checkout(self) -> CheckoutInfoPage:
        """Proceed to checkout step one."""
        from framework.pages.checkout_page import CheckoutInfoPage

        self.checkout_button.click()
        return CheckoutInfoPage(self.page).wait_until_current()

    def continue_shopping(self) -> InventoryPage:
        """Go back to the catalog."""
        from framework.pages.inventory_page import InventoryPage

        self.continue_shopping_button.click()
        return InventoryPage(self.page).wait_until_current()
