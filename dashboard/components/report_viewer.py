"""Allure Report tab: embedded latest report + full-screen link."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from dashboard.services import allure_service


def render() -> None:
    """Embed the latest Allure report; offer regenerate and full-screen."""
    if not allure_service.allure_available():
        st.error(
            "Allure commandline is not installed. "
            "Install with `npm install -g allure-commandline` (requires Java)."
        )
        return

    left, right = st.columns([1, 3])
    with left:
        if st.button("🔄 Regenerate report"):
            success, message = allure_service.generate_report()
            (st.success if success else st.warning)(message)

    if not (allure_service.REPORT_DIR / "index.html").is_file():
        st.info("No report generated yet — run some tests first.")
        return

    url = allure_service.ensure_report_server()
    with right:
        st.markdown(f"[Open report full-screen]({url})")

    summary = allure_service.report_summary()
    if summary:
        stats = summary.get("statistic", {})
        cols = st.columns(5)
        keys = ("total", "passed", "failed", "broken", "skipped")
        for column, key in zip(cols, keys, strict=True):
            column.metric(key.title(), stats.get(key, 0))

    components.iframe(url, height=800, scrolling=True)
