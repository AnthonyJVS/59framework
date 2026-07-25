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
import re
from collections.abc import Generator
from pathlib import Path

import allure
import pytest
from playwright.sync_api import BrowserContext, Page

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
    # Site Scanner (Mode B) knobs. Defined here because pytest only honours
    # pytest_addoption in initial conftests; the fixtures using them live in
    # tests/scanner/conftest.py.
    parser.addoption(
        "--scan-depth",
        action="store",
        type=int,
        default=1,
        help="Site Scanner: crawl depth from the start page.",
    )
    parser.addoption(
        "--scan-max-pages",
        action="store",
        type=int,
        default=15,
        help="Site Scanner: maximum number of pages to open in the browser.",
    )
    parser.addoption(
        "--scan-load-budget-ms",
        action="store",
        type=int,
        default=10_000,
        help="Site Scanner: page-load budget for the start page, in ms.",
    )
    parser.addoption(
        "--scan-record-video",
        action="store_true",
        default=False,
        help="Site Scanner: record a video of the crawl to reports/scan_video.webm.",
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


TRACES_DIR = Path(__file__).resolve().parents[1] / "reports" / "traces"


def _safe_name(node_id: str) -> str:
    """Turn a pytest node id into a filesystem-safe file stem."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", node_id)[-120:]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo
) -> Generator[None, None, None]:
    """Stash the call report on the item and screenshot failures immediately.

    The screenshot happens here — before any fixture teardown — so the page
    is still open; the trace is saved later in the ``context`` teardown.
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)
    if report.when == "call" and report.failed:
        page = item.funcargs.get("page")
        if isinstance(page, Page) and not page.is_closed():
            allure.attach(
                page.screenshot(full_page=True),
                name="failure-screenshot",
                attachment_type=allure.attachment_type.PNG,
            )


@pytest.fixture
def context(
    context: BrowserContext,
    env_config: EnvironmentConfig,
    browser_name: str,
    request: pytest.FixtureRequest,
) -> Generator[BrowserContext, None, None]:
    """Apply the environment timeout and record a trace, kept only on failure.

    ``browser_name`` must stay in this signature even though it is unused:
    overriding ``context`` hides the plugin fixture chain from pytest's
    collection-time closure, and without ``browser_name`` present
    pytest-playwright cannot parametrize multi-``--browser`` matrix runs.
    """
    context.set_default_timeout(env_config.default_timeout_ms)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield context
    call_report = getattr(request.node, "rep_call", None)
    if call_report is not None and call_report.failed:
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        trace_path = TRACES_DIR / f"{_safe_name(request.node.nodeid)}.zip"
        context.tracing.stop(path=str(trace_path))
        allure.attach.file(
            str(trace_path),
            name="playwright-trace",
            extension="zip",
        )
    else:
        context.tracing.stop()
