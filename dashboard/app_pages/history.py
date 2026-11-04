"""History: every dashboard-triggered test run, with trends."""

import pandas as pd
import streamlit as st

from dashboard.components.ui import empty_state, status_label
from dashboard.services import run_history

entries = run_history.load_history()
if not entries:
    empty_state("No runs recorded yet — start one from the sidebar.", icon=":material/history:")
    st.stop()

frame = pd.DataFrame(entries)
frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")

with st.container(horizontal=True, vertical_alignment="bottom"):
    mode = st.segmented_control(
        "Mode",
        ["All", "Suites (A)", "Scanner (B)"],
        default="All",
        required=True,
    )
    targets = sorted(frame["target"].dropna().unique())
    chosen_targets = st.multiselect("Target", targets, placeholder="All targets", width=360)

if mode == "Suites (A)":
    frame = frame[frame["mode"] == "A"]
elif mode == "Scanner (B)":
    frame = frame[frame["mode"] == "B"]
if chosen_targets:
    frame = frame[frame["target"].isin(chosen_targets)]
if frame.empty:
    empty_state("No runs match these filters.", icon=":material/filter_alt_off:")
    st.stop()

finished = frame[frame["status"] != "stopped"]
green = (finished["status"] == "passed").sum()
with st.container(horizontal=True):
    st.metric("Runs", len(frame), border=True)
    st.metric(
        "Green runs",
        f"{green / len(finished):.0%}" if len(finished) else "—",
        border=True,
        help="Share of finished runs (stopped ones excluded) with no failures.",
    )
    st.metric(
        "Median duration",
        f"{finished['duration_s'].median():.0f}s" if len(finished) else "—",
        border=True,
    )
    st.metric(
        "Tests failed",
        int(frame["failed"].sum()),
        border=True,
        help="Failures and errors across the shown runs.",
    )

# Runs are irregular in time, so the charts use the run number (oldest = 1)
# as an evenly spaced axis instead of wall-clock time.
chronological = frame.sort_values("timestamp").reset_index(drop=True)
chronological["run"] = chronological.index + 1
left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown("**Pass rate per run**")
    rates = chronological.dropna(subset=["pass_rate"])
    if len(rates) > 1:
        st.line_chart(
            rates.assign(pass_rate=rates["pass_rate"] * 100),
            x="run",
            y="pass_rate",
            x_label="run #",
            y_label="% passed",
            height=240,
        )
    else:
        st.caption("Needs at least two runs with executed tests.")
with right, st.container(border=True):
    st.markdown("**Duration per run**")
    if len(chronological) > 1:
        st.bar_chart(
            chronological,
            x="run",
            y="duration_s",
            x_label="run #",
            y_label="seconds",
            height=240,
        )
    else:
        st.caption("Needs at least two runs.")

table = frame.assign(
    result=frame["status"].map(status_label),
    test_types=frame["test_types"].apply(lambda value: ", ".join(value)),
    browsers=frame["browsers"].apply(lambda value: ", ".join(value)),
)
st.dataframe(
    table,
    hide_index=True,
    column_order=[
        "timestamp",
        "result",
        "target",
        "test_types",
        "browsers",
        "pass_rate",
        "passed",
        "failed",
        "skipped",
        "duration_s",
        "parallel",
    ],
    column_config={
        "timestamp": st.column_config.DatetimeColumn("When", format="D MMM, HH:mm"),
        "result": st.column_config.TextColumn("Result", width="small"),
        "target": "Target",
        "test_types": "Suites",
        "browsers": "Browsers",
        "pass_rate": st.column_config.ProgressColumn(
            "Pass rate", min_value=0.0, max_value=1.0, format="percent"
        ),
        "passed": st.column_config.NumberColumn("Passed", width="small"),
        "failed": st.column_config.NumberColumn("Failed", width="small"),
        "skipped": st.column_config.NumberColumn("Skipped", width="small"),
        "duration_s": st.column_config.NumberColumn("Duration", format="%.0f s"),
        "parallel": st.column_config.CheckboxColumn("Parallel", width="small"),
    },
)
