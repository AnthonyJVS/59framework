"""Root fixtures: dual-mode ``base_url`` / ``api_base_url`` resolution.

Resolution hierarchy (Section 3 of the build spec), highest priority first:

1. **Explicit URL override** — ``--base-url`` CLI flag (pytest-base-url) or
   ``TARGET_URL`` env var; ``--api-base-url`` / ``API_TARGET_URL`` for the API.
   This is the channel the Streamlit dashboard's Site Scanner (Mode B) uses.
2. **Environment config** — ``--env`` CLI flag or ``ENV`` env var, resolved
   through ``config/environments/<env>.yaml`` (Mode A).
3. **Default** — the ``dev`` environment.

Both modes coexist in one run: scanner tests under ``tests/scanner/`` bring
their own fixtures and never touch Page Objects or environment YAMLs.
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import BrowserContext

from config.config_loader import (
    DEFAULT_ENVIRONMENT,
    EnvironmentConfig,
    available_environments,
    load_environment,
)
from framework.core.driver_factory import DriverFactory


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help=(
            "Environment name (see config/environments/). "
            f"Falls back to $ENV, then '{DEFAULT_ENVIRONMENT}'."
        ),
    )
    parser.addoption(
        "--api-base-url",
        action="store",
        default=None,
        help="Explicit API base URL override; bypasses environment config.",
    )


@pytest.fixture(scope="session")
def env_name(request: pytest.FixtureRequest) -> str:
    """Active environment name: --env flag > $ENV > default."""
    name = request.config.getoption("--env") or os.environ.get("ENV") or DEFAULT_ENVIRONMENT
    if name not in available_environments():
        raise pytest.UsageError(
            f"Unknown environment '{name}'. Available: {', '.join(available_environments())}"
        )
    return name


@pytest.fixture(scope="session")
def env_config(env_name: str) -> EnvironmentConfig:
    """Parsed, ${ENV_VAR}-interpolated config for the active environment."""
    return load_environment(env_name)


@pytest.fixture(scope="session")
def base_url(request: pytest.FixtureRequest, env_config: EnvironmentConfig) -> str:
    """UI base URL. Overrides pytest-base-url's fixture with the dual-mode hierarchy."""
    explicit = request.config.getoption("--base-url") or os.environ.get("TARGET_URL")
    return explicit.rstrip("/") if explicit else env_config.base_url


@pytest.fixture(scope="session")
def api_base_url(request: pytest.FixtureRequest, env_config: EnvironmentConfig) -> str:
    """API base URL, resolved with the same hierarchy as ``base_url``."""
    explicit = request.config.getoption("--api-base-url") or os.environ.get("API_TARGET_URL")
    return explicit.rstrip("/") if explicit else env_config.api_base_url


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict, base_url: str) -> dict:
    """Merge framework context defaults into pytest-playwright's context args."""
    return {**browser_context_args, **DriverFactory.context_args(base_url=base_url)}


@pytest.fixture
def context(context: BrowserContext, env_config: EnvironmentConfig) -> BrowserContext:
    """Apply the environment's default timeout to every test's browser context."""
    context.set_default_timeout(env_config.default_timeout_ms)
    return context
