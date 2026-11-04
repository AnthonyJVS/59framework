"""Streamlit control panel for the test automation framework.

Run with::

    streamlit run dashboard/app.py

Entry point: page config, the shared run-setup sidebar and top navigation.
Each page lives in ``dashboard/app_pages/`` as a plain script.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402 (path bootstrap must run first)

from dashboard.components import sidebar  # noqa: E402
from dashboard.state import job_manager  # noqa: E402

st.set_page_config(
    page_title="59framework",
    page_icon=":material/science:",
    layout="wide",
)

manager = job_manager()

live_page = st.Page(
    "app_pages/live_run.py",
    title="Live run",
    icon=":material/progress_activity:" if manager.busy else ":material/terminal:",
)
page = st.navigation(
    [
        st.Page("app_pages/overview.py", title="Overview", icon=":material/space_dashboard:"),
        live_page,
        st.Page("app_pages/allure_report.py", title="Report", icon=":material/assessment:"),
        st.Page("app_pages/performance.py", title="Performance", icon=":material/speed:"),
        st.Page("app_pages/scanner.py", title="Site scanner", icon=":material/travel_explore:"),
        st.Page("app_pages/history.py", title="History", icon=":material/history:"),
    ],
    position="top",
)

sidebar.render(manager, live_page)
st.title(page.title, icon=page.icon)
page.run()
