"""k6 trigger handling and the Performance Results tab (plotly charts)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.sidebar import PerfRequest
from dashboard.services import k6_service
from dashboard.services.k6_service import K6Config

_TAIL_LINES = 25


def handle_trigger(request: PerfRequest) -> None:
    """React to the sidebar's k6 button: run the load test with live output."""
    if not request.submitted:
        return
    if not k6_service.k6_available():
        st.warning(
            "k6 is not installed — install it from https://k6.io/docs/get-started/ "
            "and restart the dashboard."
        )
        return

    defaults = k6_service.load_perf_config().get("defaults", {})
    config = K6Config(
        target_url=request.target_url,
        script=defaults.get("script", "homepage_load.js"),
        vus=request.vus,
        duration_s=request.duration_s,
    )
    st.info(
        f"k6: {config.script} against **{config.target_url}** "
        f"({config.vus} VUs, {config.duration_s}s)"
    )
    log_slot = st.empty()
    lines: list[str] = []

    def _on_line(line: str) -> None:
        lines.append(line)
        log_slot.code("\n".join(lines[-_TAIL_LINES:]), language="text")

    with st.spinner("Load test in progress"):
        summary, exit_code, message = k6_service.run_k6(config, on_line=_on_line)

    if summary is None:
        st.error(message)
    elif exit_code == 0:
        st.success(f"{message} — see the **Performance Results** tab.")
    else:
        st.warning(f"{message} — see the **Performance Results** tab.")


def render_results() -> None:
    """Latest k6 summary as metrics + charts, plus a trend over past runs."""
    summary = k6_service.latest_summary()
    if summary is None:
        st.info("No k6 results yet. Configure VUs/duration in the sidebar and run a load test.")
        return

    st.caption(
        f"{summary['script']} against **{summary['target_url']}** — "
        f"{summary['vus']} VUs for {summary['duration_s']}s at {summary['started_at']}"
    )
    cols = st.columns(4)
    cols[0].metric("Requests", summary["requests"])
    cols[1].metric("Throughput", f"{summary['rps']:.1f} req/s")
    cols[2].metric("Error rate", f"{summary['error_rate'] * 100:.2f} %")
    cols[3].metric(
        "Thresholds",
        "passed ✅" if summary["thresholds_passed"] else "crossed ❌",
    )

    latency_labels = ["avg", "median", "p90", "p95", "max"]
    latency_values = [
        summary["latency_avg_ms"],
        summary["latency_med_ms"],
        summary["latency_p90_ms"],
        summary["latency_p95_ms"],
        summary["latency_max_ms"],
    ]
    figure = go.Figure(go.Bar(x=latency_labels, y=latency_values))
    figure.update_layout(
        title="Response-time distribution (ms)",
        yaxis_title="ms",
        height=350,
        margin=dict(t=50, b=30),
    )
    st.plotly_chart(figure, width="stretch")

    runs = k6_service.history()
    if len(runs) > 1:
        frame = pd.DataFrame(reversed(runs))
        trend = go.Figure()
        trend.add_trace(
            go.Scatter(x=frame["started_at"], y=frame["latency_p95_ms"], name="p95 latency (ms)")
        )
        trend.add_trace(go.Scatter(x=frame["started_at"], y=frame["rps"], name="req/s", yaxis="y2"))
        trend.update_layout(
            title="Trend over runs",
            yaxis=dict(title="p95 (ms)"),
            yaxis2=dict(title="req/s", overlaying="y", side="right"),
            height=350,
            margin=dict(t=50, b=30),
        )
        st.plotly_chart(trend, width="stretch")
