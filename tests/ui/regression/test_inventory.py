"""Regression: catalog sorting, product detail consistency and cart badge."""

from __future__ import annotations

import pytest

from framework.pages.inventory_page import (
    SORT_NAME_ASC,
    SORT_NAME_DESC,
    SORT_PRICE_ASC,
    SORT_PRICE_DESC,
    InventoryPage,
)

pytestmark = [pytest.mark.regression, pytest.mark.ui]


def test_default_sort_is_name_ascending(inventory_page: InventoryPage) -> None:
    """The catalog opens sorted A→Z."""
    names = inventory_page.product_names()
    assert names == sorted(names)


def test_sort_name_descending(inventory_page: InventoryPage) -> None:
    """Z→A sorting reverses the name order."""
    inventory_page.sort_by(SORT_NAME_DESC)
    names = inventory_page.product_names()
    assert names == sorted(names, reverse=True)


def test_sort_price_low_to_high(inventory_page: InventoryPage) -> None:
    """Price ascending sorts cheapest first."""
    inventory_page.sort_by(SORT_PRICE_ASC)
    prices = inventory_page.product_prices()
    assert prices == sorted(prices)


def test_sort_price_high_to_low(inventory_page: InventoryPage) -> None:
    """Price descending sorts most expensive first."""
    inventory_page.sort_by(SORT_PRICE_DESC)
    prices = inventory_page.product_prices()
    assert prices == sorted(prices, reverse=True)


def test_sort_back_to_name_ascending(inventory_page: InventoryPage) -> None:
    """Re-selecting A→Z restores the default order after another sort."""
    inventory_page.sort_by(SORT_PRICE_DESC)
    inventory_page.sort_by(SORT_NAME_ASC)
    names = inventory_page.product_names()
    assert names == sorted(names)


def test_product_detail_matches_catalog(inventory_page: InventoryPage) -> None:
    """The detail page shows the same name and price as the catalog card."""
    catalog_name = inventory_page.product_names()[0]
    catalog_price = inventory_page.product_prices()[0]
    detail = inventory_page.open_product(catalog_name)
    assert detail.product_name() == catalog_name
    assert detail.product_price() == catalog_price


def test_add_to_cart_increments_badge(inventory_page: InventoryPage) -> None:
    """Adding products raises the cart badge count accordingly."""
    names = inventory_page.product_names()
    assert inventory_page.cart_count() == 0
    inventory_page.add_to_cart(names[0])
    assert inventory_page.cart_count() == 1
    inventory_page.add_to_cart(names[1])
    assert inventory_page.cart_count() == 2


def test_remove_from_catalog_clears_badge(inventory_page: InventoryPage) -> None:
    """Removing a product from the catalog card updates the badge."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    assert inventory_page.cart_count() == 1
    inventory_page.remove_from_cart(name)
    assert inventory_page.cart_count() == 0
