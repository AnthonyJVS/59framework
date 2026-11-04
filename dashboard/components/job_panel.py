"""Live view of the current background job (test run or k6 load test).

The panel is a fragment that re-renders itself every second while the job
runs, so the rest of the page (and the sidebar) stays interactive. When the
job finishes, one full app rerun refreshes everything that depends on it
(run buttons, history, reports).
"""

from __future__ import annotations

import dataclasses

import streamlit as st

from dashboard.components.ui import fmt_duration, fmt_ms, status_badge
from dashboard.services import gemini_service
from dashboard.services.job_manager import Job, JobBusyError, JobManager

_LOG_TAIL_LINES = 300
_POLL_SECONDS = 1.0


def render(manager: JobManager, *, compact: bool = False) -> None:
    """Draw the current job; polls while it is running."""
    job = manager.current
    if job is None:
        return
    seen_key = f"job_seen_running_{job.id}"

    @st.fragment(run_every=_POLL_SECONDS if job.running else None)
    def _panel() -> None:
        if job.running:
            st.session_state[seen_key] = True
        elif st.session_state.pop(seen_key, False):
            st.rerun(scope="app")  # finished while we watched: refresh the whole app
        if compact:
            _compact(job)
        else:
            _full(manager, job)

    _panel()


# --- layouts ----------------------------------------------------------------


def _header(job: Job) -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        status_badge(job.status)
        st.markdown(f"**{job.title}**", width="content")
        st.caption(
            f"started {job.started_at:%H:%M:%S} · {fmt_duration(job.elapsed_s)}", width="content"
        )


def _compact(job: Job) -> None:
    with st.container(border=True):
        _header(job)
        if job.kind == "tests":
            _progress(job)
        st.page_link(
            "app_pages/live_run.py", label="Open live run", icon=":material/arrow_forward:"
        )


def _full(manager: JobManager, job: Job) -> None:
    with st.container(horizontal=True, vertical_alignment="center"):
        _header(job)
        st.space("stretch")
        if job.running:
            st.button(
                "Stop run",
                icon=":material/stop:",
                key=f"stop_{job.id}",
                on_click=manager.stop,
                disabled=job.stop_requested,
            )
    st.code(job.command, language="bash", wrap_lines=True)

    if job.kind == "tests":
        _progress(job)
        _test_metrics(job)
    elif job.k6_summary is not None:
        _k6_metrics(job)

    with st.container(height=380, border=True, autoscroll=True):
        tail = job.lines[-_LOG_TAIL_LINES:]
        st.code("\n".join(tail) or "Waiting for output…", language="text")

    if job.running:
        if job.message:
            st.caption(job.message)
        return
    _finished_actions(manager, job)


def _progress(job: Job) -> None:
    counters = job.counters
    if counters.total:
        st.progress(counters.progress or 0.0, text=f"{counters.done} of {counters.total} tests")
    elif job.running:
        st.progress(0.0, text="Collecting tests…")


def _test_metrics(job: Job) -> None:
    counters = job.counters
    with st.container(horizontal=True):
        st.metric("Passed", counters.passed, border=True)
        st.metric("Failed", counters.failed, border=True)
        st.metric("Errors", counters.errors, border=True)
        st.metric("Skipped", counters.skipped, border=True)


def _k6_metrics(job: Job) -> None:
    summary = job.k6_summary
    assert summary is not None
    with st.container(horizontal=True):
        st.metric("Requests", f"{summary.requests:,}", border=True)
        st.metric("p95 latency", fmt_ms(summary.latency_p95_ms), border=True)
        st.metric("Error rate", f"{summary.error_rate:.2%}", border=True)
        st.metric("Thresholds", "Passed" if summary.thresholds_passed else "Crossed", border=True)


# --- after the run ----------------------------------------------------------


def _finished_actions(manager: JobManager, job: Job) -> None:
    if job.message:
        st.caption(job.message)
    with st.container(horizontal=True):
        st.download_button(
            "Download log",
            data=job.log_text(),
            file_name=f"{job.kind}-{job.started_at:%Y%m%d-%H%M%S}.log",
            mime="text/plain",
            icon=":material/download:",
            on_click="ignore",
        )
        if job.kind == "tests" and job.needs_attention and "config" in job.meta:
            st.button(
                "Re-run failed tests",
                icon=":material/replay:",
                key=f"rerun_{job.id}",
                on_click=_rerun_failed,
                args=(manager, job),
            )
        if job.kind == "tests":
            st.page_link(
                "app_pages/allure_report.py", label="Open report", icon=":material/assessment:"
            )
    if job.needs_attention:
        _gemini_section(job)


def _rerun_failed(manager: JobManager, job: Job) -> None:
    """Button callback: start a run of only the tests that failed in ``job``."""
    config = dataclasses.replace(job.meta["config"], last_failed=True)
    meta = {**job.meta, "title": "Re-run of failed tests"}
    meta.pop("config", None)
    try:
        manager.start_tests(config, meta)
    except JobBusyError:
        st.toast("Another run is still in progress", icon=":material/hourglass_top:")


def _gemini_section(job: Job) -> None:
    """On-demand AI explanation of the failures."""
    with st.container(border=True):
        st.markdown(":material/auto_awesome: **Explain the failures**")
        if not gemini_service.gemini_available():
            st.caption("Set `GEMINI_API_KEY` in `.env` to enable AI analysis (see `.env.example`).")
            return
        result_key, error_key = f"gemini_{job.id}", f"gemini_error_{job.id}"
        if st.button(
            "Analyze with Gemini",
            icon=":material/auto_awesome:",
            key=f"analyze_{job.id}",
            help=f"Sends the failure section of the log to {gemini_service.model_name()}.",
        ):
            st.session_state.pop(error_key, None)
            with st.spinner("Asking Gemini…"):
                try:
                    st.session_state[result_key] = gemini_service.analyze_log(job.log_text())
                except Exception as exc:  # SDK/network/quota errors: show, don't crash
                    st.session_state.pop(result_key, None)
                    st.session_state[error_key] = str(exc)
        if st.session_state.get(error_key):
            st.error(f"Gemini analysis failed: {st.session_state[error_key]}")
        elif st.session_state.get(result_key):
            st.markdown(st.session_state[result_key])
