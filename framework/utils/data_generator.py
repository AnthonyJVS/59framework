"""Faker-backed test data generation."""

from __future__ import annotations

from dataclasses import dataclass

from faker import Faker


@dataclass(frozen=True)
class CheckoutInfo:
    """Buyer details for the checkout information form."""

    first_name: str
    last_name: str
    postal_code: str


class DataGenerator:
    """Central factory for randomized-but-valid test data."""

    def __init__(self, seed: int | None = None) -> None:
        self.faker = Faker()
        if seed is not None:
            Faker.seed(seed)

    def checkout_info(self) -> CheckoutInfo:
        """A realistic buyer for the checkout form."""
        return CheckoutInfo(
            first_name=self.faker.first_name(),
            last_name=self.faker.last_name(),
            postal_code=self.faker.postcode(),
        )
