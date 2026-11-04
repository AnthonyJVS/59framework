"""Report: the latest Allure report, embedded, with headline numbers."""

import streamlit as st

from dashboard.components.ui import empty_state, fmt_duration
from dashboard.services import allure_service

if not allure_service.allure_available():
    st.error(
        "The Allure commandline is not installed. Install it with "
        "`npm install -g allure-commandline` (needs Java 8+), then reload this page.",
        icon=":material/error:",
    )
    st.stop()

with st.container(horizontal=True, vertical_alignment="center"):
    regenerate = st.button("Regenerate", icon=":material/refresh:")
    report_ready = (allure_service.REPORT_DIR / "index.html").is_file()
    if report_ready:
        url = allure_service.ensure_report_server()
        st.link_button("Open full screen", url, icon=":material/open_in_new:")

if regenerate:
    with st.spinner("Generating report…"):
        success, message = allure_service.generate_report()
    if success:
        st.toast("Report regenerated", icon=":material/check_circle:")
        st.rerun()
    st.warning(message, icon=":material/warning:")

if not report_ready:
    empty_state("No report yet — run some tests first.", icon=":material/assessment:")
    st.stop()

summary = allure_service.report_summary() or {}
stats = summary.get("statistic", {})
total = stats.get("total", 0)
passed = stats.get("passed", 0)
duration_ms = (summary.get("time") or {}).get("duration")
with st.container(horizontal=True):
    st.metric(
        "Pass rate",
        f"{passed / total:.0%}" if total else "—",
        border=True,
        help="Passed out of all tests in the latest report.",
    )
    st.metric("Passed", passed, border=True)
    st.metric("Failed", stats.get("failed", 0), border=True)
    st.metric("Broken", stats.get("broken", 0), border=True, help="Errors outside assertions.")
    st.metric("Skipped", stats.get("skipped", 0), border=True)
    st.metric(
        "Duration",
        fmt_duration(duration_ms / 1000) if duration_ms else "—",
        border=True,
    )

st.iframe(allure_service.ensure_report_server(), height=820)
