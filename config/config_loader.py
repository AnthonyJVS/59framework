"""Environment configuration loading with ``${ENV_VAR}`` interpolation.

Reads per-environment YAML files from ``config/environments/*.yaml``, expands
``${VAR}`` / ``${VAR:default}`` placeholders from the process environment
(``.env`` is loaded first via python-dotenv), and caches parsed results with
``lru_cache`` so every fixture/service sees the same immutable config object.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

CONFIG_DIR = Path(__file__).resolve().parent
ENVIRONMENTS_DIR = CONFIG_DIR / "environments"
PROJECT_ROOT = CONFIG_DIR.parent

DEFAULT_ENVIRONMENT = "dev"

_PLACEHOLDER_RE = re.compile(r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::(?P<default>[^}]*))?\}")

load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(RuntimeError):
    """Raised when an environment file is missing, malformed, or incomplete."""


@dataclass(frozen=True)
class EnvironmentConfig:
    """Immutable view of one ``config/environments/<name>.yaml`` file."""

    name: str
    base_url: str
    api_base_url: str
    default_timeout_ms: int
    credentials: Mapping[str, str]
    raw: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, name: str, data: Mapping[str, Any]) -> EnvironmentConfig:
        """Build a config object, failing loudly on missing required keys."""
        missing = [key for key in ("base_url", "api_base_url") if not data.get(key)]
        if missing:
            raise ConfigError(f"Environment '{name}' is missing required key(s): {missing}")
        return cls(
            name=name,
            base_url=str(data["base_url"]).rstrip("/"),
            api_base_url=str(data["api_base_url"]).rstrip("/"),
            default_timeout_ms=int(data.get("default_timeout_ms", 10_000)),
            credentials=dict(data.get("credentials") or {}),
            raw=dict(data),
        )


def _interpolate(value: Any) -> Any:
    """Recursively expand ``${VAR}`` / ``${VAR:default}`` in strings, dicts and lists."""
    if isinstance(value, str):

        def _replace(match: re.Match[str]) -> str:
            name = match.group("name")
            resolved = os.environ.get(name, match.group("default"))
            if resolved is None:
                raise ConfigError(
                    f"Environment variable '{name}' is not set and has no default "
                    f"(placeholder '{match.group(0)}')"
                )
            return resolved

        return _PLACEHOLDER_RE.sub(_replace, value)
    if isinstance(value, Mapping):
        return {key: _interpolate(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_interpolate(item) for item in value]
    return value


def available_environments() -> tuple[str, ...]:
    """Names of all configured environments (drives the Streamlit dropdown)."""
    return tuple(sorted(path.stem for path in ENVIRONMENTS_DIR.glob("*.yaml")))


@cache
def load_environment(name: str = DEFAULT_ENVIRONMENT) -> EnvironmentConfig:
    """Load, interpolate and cache the config for one environment."""
    path = ENVIRONMENTS_DIR / f"{name}.yaml"
    if not path.is_file():
        raise ConfigError(
            f"Unknown environment '{name}' — expected {path}. "
            f"Available: {', '.join(available_environments()) or '(none)'}"
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, Mapping):
        raise ConfigError(f"{path} must contain a YAML mapping, got {type(data).__name__}")
    return EnvironmentConfig.from_mapping(name, _interpolate(data))


def match_environment_for_url(url: str) -> str | None:
    """Return the environment whose ``base_url`` matches ``url``, else ``None``.

    Used by the dashboard to route a pasted URL: a match means Mode A
    (fixed-environment testing), no match means Mode B (Site Scanner).
    """
    normalized = url.strip().rstrip("/").lower()
    for env_name in available_environments():
        if load_environment(env_name).base_url.lower() == normalized:
            return env_name
    return None
