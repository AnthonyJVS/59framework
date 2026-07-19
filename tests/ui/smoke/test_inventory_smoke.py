"""Smoke: catalog renders products and the cart is reachable."""

from __future__ import annotations

import pytest

from framework.pages.inventory_page import InventoryPage

pytestmark = [pytest.mark.smoke, pytest.mark.ui]


def test_catalog_lists_products_with_names_and_prices(inventory_page: InventoryPage) -> None:
    """Every catalog card has a non-empty name and a positive price."""
    names = inventory_page.product_names()
    prices = inventory_page.product_prices()
    assert names, "Catalog rendered no products"
    assert len(names) == len(prices)
    assert all(name.strip() for name in names)
    assert all(price > 0 for price in prices)


def test_cart_is_reachable_from_catalog(inventory_page: InventoryPage) -> None:
    """The header cart icon navigates to the cart page."""
    cart = inventory_page.open_cart()
    assert cart.is_current(), "Cart icon did not navigate to /cart.html"
