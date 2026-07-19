"""Sidebar: target/environment selection, test types, browsers, run triggers."""

from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st

from config.config_loader import available_environments, match_environment_for_url
from framework.core.driver_factory import SUPPORTED_BROWSERS

_TYPE_TO_MARKER = {
    "Smoke": "smoke",
    "Regression": "regression",
    "API": "api",
    "Site Scanner": "scanner",
}


@dataclass(frozen=True)
class RunRequest:
    """What the user asked the Run Tests button to do."""

    mode: str  # "A" (fixed env) or "B" (site scanner)
    env_name: str | None
    target_url: str | None
    test_types: list[str]
    markers: list[str]
    browsers: list[str]
    parallel: bool
    submitted: bool


@dataclass(frozen=True)
class PerfRequest:
    """What the user asked the k6 button to do."""

    vus: int
    duration_s: int
    target_url: str
    submitted: bool


@dataclass(frozen=True)
class SidebarState:
    """Everything the sidebar produced this rerun."""

    run: RunRequest
    perf: PerfRequest
    scan_depth: int = 1
    scan_max_pages: int = field(default=15)


def render() -> SidebarState:
    """Draw the sidebar and return the collected selections."""
    st.sidebar.title("🧪 Control Panel")

    target_url = st.sidebar.text_input(
        "Target URL",
        placeholder="https://… (leave empty to use an environment)",
        help="A URL matching a configured environment runs Mode A; any other URL "
        "is offered as a Site Scanner run (Mode B).",
    ).strip()

    environments = list(available_environments())
    matched_env = match_environment_for_url(target_url) if target_url else None
    mode = "A"
    scanner_forced = False

    if target_url and matched_env:
        st.sidebar.success(f"URL matches environment **{matched_env}** → Mode A")
    elif target_url:
        mode = "B"
        scanner_forced = True
        st.sidebar.warning("Unknown URL → will run as **Site Scanner** (Mode B)")

    env_name = st.sidebar.selectbox(
        "Environment (Mode A)",
        environments,
        index=environments.index(matched_env) if matched_env else 0,
        disabled=mode == "B",
    )

    if scanner_forced:
        test_types = ["Site Scanner"]
        st.sidebar.multiselect(
            "Test types", list(_TYPE_TO_MARKER), default=["Site Scanner"], disabled=True
        )
    else:
        test_types = st.sidebar.multiselect(
            "Test types", [t for t in _TYPE_TO_MARKER if t != "Site Scanner"], default=["Smoke"]
        )

    browsers = st.sidebar.multiselect(
        "Browsers",
        list(SUPPORTED_BROWSERS),
        default=["chromium"],
        disabled=scanner_forced,
        help="The Site Scanner always uses Chromium.",
    )
    parallel = (
        st.sidebar.radio("Execution mode", ["Serial", "Parallel"], horizontal=True) == "Parallel"
    )

    scan_depth, scan_max_pages = 1, 15
    if scanner_forced:
        scan_depth = int(st.sidebar.number_input("Scan depth", 0, 5, 1))
        scan_max_pages = int(st.sidebar.number_input("Max pages to open", 1, 100, 15))

    run_clicked = st.sidebar.button(
        "▶ Run Tests",
        type="primary",
        use_container_width=True,
        disabled=not test_types,
    )

    st.sidebar.divider()
    st.sidebar.subheader("Performance test (k6)")
    vus = int(st.sidebar.number_input("Virtual users", 1, 200, 5))
    duration_s = int(st.sidebar.number_input("Duration (seconds)", 5, 600, 30))
    perf_target = target_url or ""
    perf_clicked = st.sidebar.button("⚡ Run k6 Load Test", use_container_width=True)

    markers = [_TYPE_TO_MARKER[test_type] for test_type in test_types]
    return SidebarState(
        run=RunRequest(
            mode=mode,
            env_name=None if mode == "B" else env_name,
            target_url=target_url or None,
            test_types=test_types,
            markers=markers,
            browsers=browsers or ["chromium"],
            parallel=parallel,
            submitted=run_clicked,
        ),
        perf=PerfRequest(
            vus=vus,
            duration_s=duration_s,
            target_url=perf_target,
            submitted=perf_clicked,
        ),
        scan_depth=scan_depth,
        scan_max_pages=scan_max_pages,
    )
