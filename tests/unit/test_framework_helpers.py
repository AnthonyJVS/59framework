"""Unit tests for framework helpers that need no browser or network."""

from __future__ import annotations

import pytest

from config import config_loader
from framework.scanner.link_crawler import _normalize, _same_origin
from framework.utils.data_generator import DataGenerator

pytestmark = [pytest.mark.unit]


def test_seeded_generators_are_reproducible() -> None:
    assert DataGenerator(seed=42).checkout_info() == DataGenerator(seed=42).checkout_info()


def test_seeding_one_generator_does_not_seed_the_others() -> None:
    """Seeding must be per instance, not Faker's shared class-level seed."""
    DataGenerator(seed=1)
    first = [DataGenerator().post_payload()["title"] for _ in range(3)]
    DataGenerator(seed=1)
    second = [DataGenerator().post_payload()["title"] for _ in range(3)]
    assert first != second


def test_interpolation_uses_env_then_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNIT_USER", "alice")
    monkeypatch.delenv("UNIT_MISSING", raising=False)
    data = {"user": "${UNIT_USER:bob}", "items": ["${UNIT_MISSING:fallback}", 3]}
    assert config_loader._interpolate(data) == {"user": "alice", "items": ["fallback", 3]}


def test_interpolation_without_default_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UNIT_MISSING", raising=False)
    with pytest.raises(config_loader.ConfigError, match="UNIT_MISSING"):
        config_loader._interpolate("${UNIT_MISSING}")


def test_url_matching_ignores_case_and_trailing_slash() -> None:
    base_url = config_loader.load_environment("dev").base_url
    assert config_loader.match_environment_for_url(base_url.upper() + "/") is not None
    assert config_loader.match_environment_for_url("https://unknown.example") is None


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://site.test/page#section", "https://site.test/page"),
        ("https://site.test/?q=1#x", "https://site.test/?q=1"),
    ],
)
def test_normalize_drops_fragments(url: str, expected: str) -> None:
    assert _normalize(url) == expected


@pytest.mark.parametrize(
    ("url", "same"),
    [
        ("https://site.test/a", True),
        ("https://other.test/a", False),
        ("mailto:me@site.test", False),
        ("javascript:void(0)", False),
    ],
)
def test_same_origin(url: str, same: bool) -> None:
    assert _same_origin(url, "https://site.test/") is same
