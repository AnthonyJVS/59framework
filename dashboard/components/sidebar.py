"""Sidebar: run setup (target, suites, browsers, execution) and launch buttons.

Launching starts a background job (see ``dashboard/services/job_manager.py``)
and jumps to the Live run page, so the sidebar itself never blocks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import streamlit as st

from config.config_loader import (
    available_environments,
    load_environment,
    match_environment_for_url,
)
from dashboard.services import k6_service
from dashboard.services.job_manager import JobBusyError, JobManager
from dashboard.services.k6_service import K6Config
from dashboard.services.test_executor import RunConfig
from framework.core.driver_factory import SUPPORTED_BROWSERS

_TYPE_TO_MARKER = {
    "Smoke": "smoke",
    "Regression": "regression",
    "API": "api",
}
_BROWSER_LABELS = {"chromium": "Chromium", "firefox": "Firefox", "webkit": "WebKit"}


@dataclass(frozen=True)
class Target:
    """What the run is aimed at, resolved from the URL box and environment picker."""

    url: str | None
    env_name: str | None  # None in Mode B
    mode: str  # "A" (fixed environment) or "B" (site scanner)

    @property
    def base_url(self) -> str:
        return self.url or load_environment(self.env_name or "dev").base_url

    @property
    def label(self) -> str:
        return self.url or (self.env_name or "dev")


def render(manager: JobManager, live_page: Any) -> None:
    """Draw the sidebar; start jobs and switch to ``live_page`` on demand."""
    with st.sidebar:
        st.markdown("### :material/science: 59framework")
        st.caption("Test automation control panel")

        target = _target_section()
        if target.mode == "B":
            config, meta = _scanner_section(target)
        else:
            config, meta = _suite_section(target)

        busy = manager.busy
        if st.button(
            "Run tests",
            type="primary",
            icon=":material/play_arrow:",
            width="stretch",
            disabled=busy or config is None,
            help="A run is already in progress" if busy else None,
        ):
            _start(lambda: manager.start_tests(config, meta), live_page)

        k6_config = _k6_section(target)
        if st.button(
            "Run load test",
            icon=":material/speed:",
            width="stretch",
            disabled=busy or not k6_service.k6_available(),
            help=None if k6_service.k6_available() else "k6 is not installed (https://k6.io)",
        ):
            _start(lambda: manager.start_k6(k6_config), live_page)


def _start(launch: Any, live_page: Any) -> None:
    try:
        launch()
    except JobBusyError:
        st.toast("Another run is still in progress", icon=":material/hourglass_top:")
        return
    st.switch_page(live_page)


# --- sections ---------------------------------------------------------------


def _target_section() -> Target:
    url = st.text_input(
        "Target URL",
        placeholder="https://… — empty uses the environment",
        help="A URL that matches a configured environment runs the fixed suites "
        "(Mode A). Any other URL runs the generic Site Scanner (Mode B).",
    ).strip()
    environments = list(available_environments())
    matched = match_environment_for_url(url) if url else None
    mode = "B" if url and not matched else "A"

    env_name = st.selectbox(
        "Environment",
        environments,
        index=environments.index(matched) if matched else 0,
        disabled=mode == "B" or bool(matched),
        help="Selects config/environments/<name>.yaml (URLs, credentials, timeouts).",
    )
    if mode == "B":
        st.badge("Site Scanner · Mode B", icon=":material/travel_explore:", color="orange")
    elif matched:
        st.badge(f"Matches {matched} · Mode A", icon=":material/link:", color="green")
    else:
        st.badge(f"Environment {env_name} · Mode A", icon=":material/dns:", color="blue")
    return Target(url=url or None, env_name=None if mode == "B" else env_name, mode=mode)


def _suite_section(target: Target) -> tuple[RunConfig | None, dict[str, Any]]:
    st.markdown("**Suites**")
    test_types = st.pills(
        "Test types",
        list(_TYPE_TO_MARKER),
        selection_mode="multi",
        default=["Smoke"],
        label_visibility="collapsed",
    )
    browsers = st.pills(
        "Browsers",
        list(SUPPORTED_BROWSERS),
        selection_mode="multi",
        default=["chromium"],
        format_func=_BROWSER_LABELS.get,
        help="Each selected browser runs the UI suites once.",
    )
    with st.container(horizontal=True, vertical_alignment="bottom"):
        execution = st.segmented_control(
            "Execution", ["Serial", "Parallel"], default="Serial", required=True
        )
        reruns = st.number_input(
            "Retries",
            min_value=0,
            max_value=3,
            value=0,
            help="Re-run a failing test up to N times before reporting it (flaky guard).",
        )
    if not test_types:
        st.caption(":material/info: Pick at least one test type.")
        return None, {}
    config = RunConfig(
        markers=[_TYPE_TO_MARKER[name] for name in test_types],
        env_name=target.env_name,
        target_url=target.url,
        browsers=browsers or ["chromium"],
        parallel=execution == "Parallel",
        reruns=int(reruns),
    )
    meta = {
        "title": f"{', '.join(test_types)} · {target.label}",
        "mode": "A",
        "target": target.label,
        "test_types": list(test_types),
        "browsers": config.browsers,
    }
    return config, meta


def _scanner_section(target: Target) -> tuple[RunConfig | None, dict[str, Any]]:
    st.markdown("**Site Scanner**")
    with st.container(horizontal=True):
        depth = st.number_input(
            "Crawl depth",
            min_value=0,
            max_value=5,
            value=1,
            help="Links followed from the start page. Pages are opened in the browser "
            "up to depth − 1; links at the last level are only status-checked.",
        )
        max_pages = st.number_input(
            "Max pages",
            min_value=1,
            max_value=100,
            value=15,
            help="Upper bound on pages opened in the browser (only matters at depth 2+).",
        )
    external = st.toggle("Check external links", help="Status-check links to other sites too.")
    record = st.toggle(
        "Record video", help="Save a recording of the crawl (adds overhead and disk usage)."
    )
    ignore_raw = st.text_area(
        "Ignore console errors matching",
        placeholder="One regular expression per line, e.g.\ngoogletagmanager|doubleclick",
        height=80,
    )
    patterns, invalid = _parse_patterns(ignore_raw)
    if invalid:
        st.error(f"Not a valid regular expression: `{invalid}`", icon=":material/error:")
        return None, {}
    config = RunConfig(
        markers=["scanner"],
        target_url=target.url,
        scan_depth=int(depth),
        scan_max_pages=int(max_pages),
        scan_record_video=record,
        scan_external=external,
        scan_ignore_console=patterns,
    )
    meta = {
        "title": f"Site scan · {target.url}",
        "mode": "B",
        "target": target.label,
        "test_types": ["Site Scanner"],
        "browsers": ["chromium"],
    }
    return config, meta


def _parse_patterns(raw: str) -> tuple[list[str], str | None]:
    patterns = [line.strip() for line in raw.splitlines() if line.strip()]
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error:
            return [], pattern
    return patterns, None


def _k6_section(target: Target) -> K6Config:
    defaults = k6_service.default_settings()
    scripts = k6_service.available_scripts()
    with st.expander("Load test (k6)", icon=":material/speed:"):
        labels = list(scripts)
        default_label = next(
            (label for label, file in scripts.items() if file == defaults.script),
            labels[0] if labels else None,
        )
        script_label = st.selectbox(
            "Script",
            labels,
            index=labels.index(default_label) if default_label in labels else 0,
        )
        with st.container(horizontal=True):
            vus = st.number_input("Virtual users", 1, 500, defaults.vus)
            duration = st.number_input("Duration, s", 5, 3600, defaults.duration_s)
        st.caption(f"Target: {target.base_url}")
    return K6Config(
        target_url=target.base_url,
        script=scripts.get(script_label, defaults.script) if script_label else defaults.script,
        vus=int(vus),
        duration_s=int(duration),
    )
