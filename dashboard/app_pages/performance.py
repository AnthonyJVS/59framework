"""Performance: k6 results — latest run vs the previous comparable one, and trends."""

import pandas as pd
import streamlit as st

from dashboard.components.ui import empty_state, fmt_ms, fmt_timestamp
from dashboard.services import k6_service

runs = k6_service.history()
if not runs:
    empty_state(
        "No load tests yet. Open **Load test (k6)** in the sidebar and press "
        "**Run load test**."
        + ("" if k6_service.k6_available() else " k6 is not installed — see https://k6.io."),
        icon=":material/speed:",
    )
    st.stop()

# --- pick which series to look at -------------------------------------------
series = sorted({(run.get("target_url", ""), run.get("script", "")) for run in runs})
latest_series = (runs[0].get("target_url", ""), runs[0].get("script", ""))
if len(series) > 1:
    chosen = st.selectbox(
        "Series",
        series,
        index=series.index(latest_series),
        format_func=lambda item: f"{item[1]} → {item[0]}",
        help="Only runs with the same target and script are compared.",
    )
else:
    chosen = latest_series
comparable = k6_service.comparable_runs(runs, *chosen)
latest = comparable[0]
previous = comparable[1] if len(comparable) > 1 else None

st.caption(
    f"**{latest['script']}** against {latest['target_url']} · "
    f"{latest['vus']} VUs for {latest['duration_s']}s · {fmt_timestamp(latest['started_at'])}"
)


def _delta(key: str, scale: float = 1.0) -> float | None:
    if previous is None:
        return None
    return round((latest[key] - previous[key]) * scale, 2)


p95_threshold = (k6_service.load_perf_config().get("thresholds") or {}).get("p95_ms")
with st.container(horizontal=True):
    st.metric(
        "p95 latency",
        fmt_ms(latest["latency_p95_ms"]),
        delta=_delta("latency_p95_ms"),
        delta_color="inverse",
        delta_description="ms vs previous run" if previous else None,
        help=f"Threshold: {p95_threshold} ms" if p95_threshold else None,
        border=True,
        chart_data=[run["latency_p95_ms"] for run in reversed(comparable[:20])],
    )
    st.metric(
        "Throughput",
        f"{latest['rps']:.1f} req/s",
        delta=_delta("rps"),
        border=True,
        chart_data=[run["rps"] for run in reversed(comparable[:20])],
    )
    st.metric(
        "Error rate",
        f"{latest['error_rate']:.2%}",
        delta=_delta("error_rate", 100),
        delta_color="inverse",
        delta_description="pp vs previous run" if previous else None,
        border=True,
    )
    st.metric("Requests", f"{latest['requests']:,}", border=True)
    st.metric(
        "Thresholds",
        "Passed" if latest["thresholds_passed"] else "Crossed",
        border=True,
    )

left, right = st.columns(2)
with left, st.container(border=True):
    st.markdown("**Response time distribution**")
    distribution = pd.DataFrame(
        {
            "statistic": ["avg", "median", "p90", "p95", "max"],
            "ms": [
                latest["latency_avg_ms"],
                latest["latency_med_ms"],
                latest["latency_p90_ms"],
                latest["latency_p95_ms"],
                latest["latency_max_ms"],
            ],
        }
    )
    st.bar_chart(distribution, x="statistic", y="ms", sort=False, height=280)

with right, st.container(border=True):
    st.markdown("**p95 latency across runs**")
    if len(comparable) > 1:
        # Evenly spaced run numbers (oldest = 1): runs are irregular in time.
        oldest_first = list(reversed(comparable))
        trend = pd.DataFrame(
            {
                "run": range(1, len(oldest_first) + 1),
                "p95 (ms)": [run["latency_p95_ms"] for run in oldest_first],
            }
        )
        st.line_chart(trend, x="run", y="p95 (ms)", x_label="run #", height=280)
    else:
        st.caption("Run the same script against the same target again to see a trend.")

with st.expander("All runs in this series", icon=":material/table_rows:"):
    table = pd.DataFrame(comparable)
    table["started_at"] = pd.to_datetime(table["started_at"])
    st.dataframe(
        table,
        hide_index=True,
        column_order=[
            "started_at",
            "vus",
            "duration_s",
            "requests",
            "rps",
            "error_rate",
            "latency_p95_ms",
            "thresholds_passed",
        ],
        column_config={
            "started_at": st.column_config.DatetimeColumn("Started", format="D MMM, HH:mm"),
            "vus": "VUs",
            "duration_s": st.column_config.NumberColumn("Duration", format="%d s"),
            "requests": "Requests",
            "rps": st.column_config.NumberColumn("req/s", format="%.1f"),
            "error_rate": st.column_config.NumberColumn("Errors", format="percent"),
            "latency_p95_ms": st.column_config.NumberColumn("p95", format="%.0f ms"),
            "thresholds_passed": st.column_config.CheckboxColumn("Thresholds ok"),
        },
    )
