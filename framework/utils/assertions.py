"""Reusable assertion helpers, most importantly JSON-schema validation."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import jsonschema
from playwright.sync_api import APIResponse

SCHEMAS_DIR = Path(__file__).resolve().parents[1] / "api" / "schemas"


@cache
def _load_schema(name: str) -> dict[str, Any]:
    """Load ``framework/api/schemas/<name>.schema.json`` (cached)."""
    path = SCHEMAS_DIR / f"{name}.schema.json"
    if not path.is_file():
        raise FileNotFoundError(f"Schema '{name}' not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_matches_schema(payload: Any, schema_name: str) -> None:
    """Validate ``payload`` against a named schema, failing with a readable path."""
    schema = _load_schema(schema_name)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema, format_checker=validator_cls.FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if errors:
        details = "; ".join(
            f"at $.{'.'.join(str(p) for p in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors[:5]
        )
        raise AssertionError(f"Response violates schema '{schema_name}': {details}")


def assert_status(response: APIResponse, expected: int) -> None:
    """Assert an exact HTTP status, including the body in the failure message."""
    assert response.status == expected, (
        f"{response.url} returned {response.status} {response.status_text}, "
        f"expected {expected}. Body: {response.text()[:500]}"
    )
