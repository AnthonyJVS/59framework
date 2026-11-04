"""Overview: the state of everything at a glance."""

import streamlit as st

from config.config_loader import available_environments
from dashboard.components import job_panel
from dashboard.components.ui import fmt_duration, fmt_ms, fmt_timestamp, status_badge
from dashboard.services import (
    allure_service,
    gemini_service,
    k6_service,
    run_history,
    scan_results,
)
from dashboard.state import job_manager

manager = job_manager()
if manager.busy:
    job_panel.render(manager, compact=True)

# --- latest test run ----------------------------------------------------------
history = run_history.load_history()
# Stopped runs are partial: they would distort pass rate, deltas and streaks.
suite_runs = [entry for entry in history if entry["mode"] == "A" and entry["status"] != "stopped"]

with st.container(border=True):
    st.subheader("Test runs", icon=":material/fact_check:")
    if not suite_runs:
        st.caption("No suite runs yet — pick suites in the sidebar and press **Run tests**.")
    else:
        latest = suite_runs[0]
        same_target = [entry for entry in suite_runs if entry["target"] == latest["target"]]
        previous = same_target[1] if len(same_target) > 1 else None
        with st.container(horizontal=True, vertical_alignment="center"):
            status_badge(latest["status"])
            st.markdown(
                f"**{', '.join(latest['test_types'])}** on {latest['target']}", width="content"
            )
            st.caption(fmt_timestamp(latest["timestamp"]), width="content")
        recent = list(reversed(same_target[:15]))
        sparkline = len(recent) > 1  # a single point draws a meaningless chart
        rate = latest["pass_rate"]
        prev_rate = previous["pass_rate"] if previous else None
        with st.container(horizontal=True):
            st.metric(
                "Pass rate",
                f"{rate:.0%}" if rate is not None else "—",
                delta=(
                    f"{(rate - prev_rate) * 100:+.0f} pp"
                    if rate is not None and prev_rate is not None
                    else None
                ),
                border=True,
                chart_data=(
                    [(entry["pass_rate"] or 0) * 100 for entry in recent] if sparkline else None
                ),
                chart_type="area",
            )
            st.metric(
                "Failed",
                latest["failed"],
                delta=latest["failed"] - previous["failed"] if previous else None,
                delta_color="inverse",
                border=True,
            )
            st.metric(
                "Duration",
                fmt_duration(latest["duration_s"]),
                border=True,
                chart_data=[entry["duration_s"] for entry in recent] if sparkline else None,
                chart_type="bar",
            )
            green_streak = 0
            for entry in same_target:
                if entry["status"] != "passed":
                    break
                green_streak += 1
            st.metric(
                "Green streak",
                green_streak,
                border=True,
                help="Consecutive passing runs against this target, newest first.",
            )

left, right = st.columns(2)

# --- performance ---------------------------------------------------------------
with left, st.container(border=True, height="stretch"):
    st.subheader("Performance", icon=":material/speed:")
    k6_runs = k6_service.history()
    if not k6_runs:
        st.caption("No load tests yet.")
    else:
        latest_k6 = k6_runs[0]
        series = k6_service.comparable_runs(
            k6_runs, latest_k6.get("target_url", ""), latest_k6.get("script", "")
        )[:15]
        st.caption(
            f"{latest_k6['script']} → {latest_k6['target_url']} · "
            f"{fmt_timestamp(latest_k6['started_at'])}"
        )
        with st.container(horizontal=True):
            st.metric(
                "p95 latency",
                fmt_ms(latest_k6["latency_p95_ms"]),
                border=True,
                chart_data=(
                    [run["latency_p95_ms"] for run in reversed(series)] if len(series) > 1 else None
                ),
            )
            st.metric("Error rate", f"{latest_k6['error_rate']:.2%}", border=True)
            st.metric(
                "Thresholds",
                "Passed" if latest_k6["thresholds_passed"] else "Crossed",
                border=True,
            )
    st.page_link("app_pages/performance.py", label="Details", icon=":material/arrow_forward:")

# --- site scanner ---------------------------------------------------------------
with right, st.container(border=True, height="stretch"):
    st.subheader("Site scanner", icon=":material/travel_explore:")
    scan = scan_results.load()
    if scan is None:
        st.caption("No scans yet.")
    else:
        broken = sum(1 for result in scan["results"] if not result.get("ok"))
        st.caption(f"{scan['start_url']} · {fmt_timestamp(scan['generated_at'])}")
        with st.container(horizontal=True):
            st.metric("Broken links", broken, border=True)
            st.metric("Console errors", len(scan["console_issues"]), border=True)
            st.metric("Page load", fmt_ms(scan["timing"].get("load_ms")), border=True)
    st.page_link("app_pages/scanner.py", label="Details", icon=":material/arrow_forward:")

# --- tooling --------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Tooling", icon=":material/build:")
    with st.container(horizontal=True):
        for name, ready, hint in (
            ("Allure", allure_service.allure_available(), "npm i -g allure-commandline"),
            ("k6", k6_service.k6_available(), "https://k6.io"),
            ("Gemini", gemini_service.gemini_available(), "set GEMINI_API_KEY in .env"),
        ):
            st.badge(
                f"{name} {'ready' if ready else 'not set up'}",
                icon=":material/check_circle:" if ready else ":material/radio_button_unchecked:",
                color="green" if ready else "gray",
                help=None if ready else hint,
            )
        environments = available_environments()
        st.badge(
            f"{len(environments)} environments: {', '.join(environments)}",
            icon=":material/dns:",
            color="blue",
        )
