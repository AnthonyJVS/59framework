"""SauceDemo inventory (home/catalog) page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from playwright.sync_api import Page

from framework.core.base_page import BasePage

if TYPE_CHECKING:
    from framework.pages.cart_page import CartPage
    from framework.pages.login_page import LoginPage
    from framework.pages.product_page import ProductPage

SORT_NAME_ASC = "az"
SORT_NAME_DESC = "za"
SORT_PRICE_ASC = "lohi"
SORT_PRICE_DESC = "hilo"


def product_slug(name: str) -> str:
    """SauceDemo derives button ids from the product name, lowercased/dashed."""
    return name.lower().replace(" ", "-")


class InventoryPage(BasePage):
    """The ``/inventory.html`` product catalog shown after login."""

    url_path = "/inventory.html"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.items = page.locator('[data-test="inventory-item"]')
        self.item_names = page.locator('[data-test="inventory-item-name"]')
        self.item_prices = page.locator('[data-test="inventory-item-price"]')
        self.sort_select = page.locator('[data-test="product-sort-container"]')
        self.cart_link = page.locator('[data-test="shopping-cart-link"]')
        self.cart_badge = page.locator('[data-test="shopping-cart-badge"]')
        self.menu_button = page.locator("#react-burger-menu-btn")
        self.logout_link = page.locator("#logout_sidebar_link")

    def product_names(self) -> list[str]:
        """Visible product names, in page order."""
        return self.item_names.all_inner_texts()

    def product_prices(self) -> list[float]:
        """Visible product prices as floats, in page order."""
        return [float(text.lstrip("$")) for text in self.item_prices.all_inner_texts()]

    def sort_by(self, option_value: str) -> None:
        """Apply a sort option (see the SORT_* constants in this module)."""
        self.sort_select.select_option(option_value)

    def add_to_cart(self, name: str) -> None:
        """Click the Add-to-cart button of the named product."""
        self.locator(f'[data-test="add-to-cart-{product_slug(name)}"]').click()

    def remove_from_cart(self, name: str) -> None:
        """Click the Remove button of the named product."""
        self.locator(f'[data-test="remove-{product_slug(name)}"]').click()

    def cart_count(self) -> int:
        """Number shown on the cart badge; 0 when the badge is absent."""
        if self.cart_badge.count() == 0:
            return 0
        return int(self.cart_badge.inner_text())

    def open_cart(self) -> CartPage:
        """Navigate to the cart via the header icon."""
        from framework.pages.cart_page import CartPage

        self.cart_link.click()
        return CartPage(self.page)

    def open_product(self, name: str) -> ProductPage:
        """Open a product's detail page by clicking its name."""
        from framework.pages.product_page import ProductPage

        self.item_names.filter(has_text=name).first.click()
        return ProductPage(self.page)

    def logout(self) -> LoginPage:
        """Log out through the burger menu; returns the login page."""
        from framework.pages.login_page import LoginPage

        self.menu_button.click()
        self.logout_link.click()
        return LoginPage(self.page)
