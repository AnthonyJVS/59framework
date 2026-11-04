"""Faker-backed test data generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
            # Per-instance: Faker.seed() would reseed the shared class-level
            # generator and make every other DataGenerator deterministic too.
            self.faker.seed_instance(seed)

    def checkout_info(self) -> CheckoutInfo:
        """A realistic buyer for the checkout form."""
        return CheckoutInfo(
            first_name=self.faker.first_name(),
            last_name=self.faker.last_name(),
            postal_code=self.faker.postcode(),
        )

    def post_payload(self) -> dict[str, Any]:
        """A create/update payload for the /posts API."""
        return {
            "userId": self.faker.random_int(min=1, max=10),
            "title": self.faker.sentence(nb_words=6).rstrip("."),
            "body": self.faker.paragraph(nb_sentences=3),
        }
