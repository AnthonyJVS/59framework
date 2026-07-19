"""Streamlit control panel for the test automation framework.

Run with::

    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402 (path bootstrap must run first)

from dashboard.components import (  # noqa: E402
    history_panel,
    perf_trigger_panel,
    report_viewer,
    scanner_panel,
    sidebar,
    test_runner_panel,
)

st.set_page_config(
    page_title="Test Automation Control Panel",
    page_icon="🧪",
    layout="wide",
)

state = sidebar.render()

st.title("Test Automation Control Panel")

live_tab, report_tab, perf_tab, scan_tab, history_tab = st.tabs(
    ["🔴 Live Run", "📊 Allure Report", "⚡ Performance Results", "🔍 Scan Results", "🕘 History"]
)

with live_tab:
    perf_trigger_panel.handle_trigger(state.perf)
    test_runner_panel.render(state)

with report_tab:
    report_viewer.render()

with perf_tab:
    perf_trigger_panel.render_results()

with scan_tab:
    scanner_panel.render()

with history_tab:
    history_panel.render()
