"""Regression: cart contents, removal and navigation."""

from __future__ import annotations

import pytest

from framework.pages.inventory_page import InventoryPage

pytestmark = [pytest.mark.regression, pytest.mark.ui]


def test_added_item_listed_with_correct_details(inventory_page: InventoryPage) -> None:
    """An added product appears in the cart with its catalog name and price."""
    name = inventory_page.product_names()[0]
    price = inventory_page.product_prices()[0]
    inventory_page.add_to_cart(name)
    cart = inventory_page.open_cart()
    assert cart.listed_names() == [name]
    assert cart.listed_prices() == [price]


def test_remove_item_empties_cart(inventory_page: InventoryPage) -> None:
    """Removing the only line item leaves an empty cart and no badge."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    cart = inventory_page.open_cart()
    cart.remove(name)
    assert cart.item_count() == 0
    assert inventory_page.cart_count() == 0


def test_continue_shopping_returns_to_catalog(inventory_page: InventoryPage) -> None:
    """Continue-shopping navigates back to the inventory."""
    catalog = inventory_page.open_cart().continue_shopping()
    assert catalog.is_current(), "Continue shopping did not return to the catalog"


def test_cart_badge_persists_across_navigation(inventory_page: InventoryPage) -> None:
    """The badge survives a detour through a product detail page."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    detail = inventory_page.open_product(name)
    catalog = detail.back_to_catalog()
    assert catalog.cart_count() == 1
