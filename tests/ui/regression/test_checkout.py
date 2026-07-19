"""Regression: end-to-end checkout, validation and order-total math."""

from __future__ import annotations

from dataclasses import replace

import pytest

from framework.pages.inventory_page import InventoryPage
from framework.utils.data_generator import CheckoutInfo

pytestmark = [pytest.mark.regression, pytest.mark.ui]


@pytest.mark.cross_browser
def test_full_checkout_happy_path(
    inventory_page: InventoryPage, checkout_data: CheckoutInfo
) -> None:
    """Add a product, check out with valid details, land on the thank-you page."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    overview = inventory_page.open_cart().start_checkout().submit(checkout_data)
    assert overview.listed_names() == [name]
    complete = overview.finish()
    assert "Thank you for your order" in complete.confirmation_text()


@pytest.mark.parametrize(
    ("blank_field", "expected_error"),
    [
        ("first_name", "First Name is required"),
        ("last_name", "Last Name is required"),
        ("postal_code", "Postal Code is required"),
    ],
)
def test_missing_checkout_field_shows_error(
    inventory_page: InventoryPage,
    checkout_data: CheckoutInfo,
    blank_field: str,
    expected_error: str,
) -> None:
    """Each required buyer field is validated independently."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    info_page = inventory_page.open_cart().start_checkout()
    error = info_page.submit_expecting_error(replace(checkout_data, **{blank_field: ""}))
    assert expected_error in error


def test_overview_totals_match_item_prices(
    inventory_page: InventoryPage, checkout_data: CheckoutInfo
) -> None:
    """Subtotal equals the sum of item prices and total equals subtotal + tax."""
    names = inventory_page.product_names()[:3]
    for name in names:
        inventory_page.add_to_cart(name)
    overview = inventory_page.open_cart().start_checkout().submit(checkout_data)
    assert sorted(overview.listed_names()) == sorted(names)
    assert overview.subtotal() == pytest.approx(sum(overview.listed_prices()), abs=0.01)
    assert overview.total() == pytest.approx(overview.subtotal() + overview.tax(), abs=0.01)


def test_cancel_from_info_returns_to_cart(
    inventory_page: InventoryPage,
) -> None:
    """Cancelling on the information step goes back to the cart."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    cart = inventory_page.open_cart().start_checkout().cancel()
    assert cart.is_current(), "Cancel did not return to the cart"
    assert cart.listed_names() == [name]


def test_finished_order_resets_cart(
    inventory_page: InventoryPage, checkout_data: CheckoutInfo
) -> None:
    """After finishing an order, returning home shows an empty cart badge."""
    name = inventory_page.product_names()[0]
    inventory_page.add_to_cart(name)
    complete = inventory_page.open_cart().start_checkout().submit(checkout_data).finish()
    catalog = complete.back_home()
    assert catalog.cart_count() == 0
