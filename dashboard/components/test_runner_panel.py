"""Live Run tab: streamed pytest output, progress and pass/fail counters."""

from __future__ import annotations

import streamlit as st

from dashboard.components.sidebar import SidebarState
from dashboard.services import allure_service, run_history
from dashboard.services.test_executor import RunConfig, RunCounters, TestExecutor

_TAIL_LINES = 40


def _run_config_from(state: SidebarState) -> RunConfig:
    request = state.run
    return RunConfig(
        markers=request.markers,
        env_name=request.env_name,
        target_url=request.target_url,
        browsers=request.browsers,
        parallel=request.parallel,
        scan_depth=state.scan_depth if request.mode == "B" else None,
        scan_max_pages=state.scan_max_pages if request.mode == "B" else None,
    )


def render(state: SidebarState) -> None:
    """Draw the Live Run tab; executes a run when the button was pressed."""
    request = state.run
    if request.submitted:
        _execute(state)
    elif "last_run_log" in st.session_state:
        st.caption("Output of the most recent run:")
        st.code(st.session_state["last_run_log"][-8000:], language="text")
    else:
        st.info("Configure a run in the sidebar and press **Run Tests**.")


def _execute(state: SidebarState) -> None:
    request = state.run
    config = _run_config_from(state)
    executor = TestExecutor()

    status_line = st.empty()
    columns = st.columns(4)
    metric_slots = [column.empty() for column in columns]
    log_slot = st.empty()
    lines: list[str] = []

    def _update_metrics(counters: RunCounters) -> None:
        metric_slots[0].metric("Passed ✅", counters.passed)
        metric_slots[1].metric("Failed ❌", counters.failed)
        metric_slots[2].metric("Errors 💥", counters.errors)
        metric_slots[3].metric("Skipped ⏭", counters.skipped)

    def _on_line(line: str, counters: RunCounters) -> None:
        lines.append(line)
        _update_metrics(counters)
        log_slot.code("\n".join(lines[-_TAIL_LINES:]), language="text")

    status_line.info("Running…  `" + " ".join(config_display(config)) + "`")
    _update_metrics(RunCounters())
    with st.spinner("Test run in progress"):
        result = executor.run(config, on_line=_on_line)

    full_log = "\n".join(lines)
    st.session_state["last_run_log"] = full_log
    _update_metrics(result.counters)
    if result.exit_code == 0:
        status_line.success(f"Run finished green in {result.duration_s:.1f}s ✅")
    else:
        status_line.error(
            f"Run finished with exit code {result.exit_code} in {result.duration_s:.1f}s"
        )

    generated, message = allure_service.generate_report()
    if generated:
        st.caption("Allure report regenerated — see the **Allure Report** tab.")
    else:
        st.caption(f"Allure report not regenerated: {message}")

    run_history.append_entry(
        mode=request.mode,
        target=request.target_url or (request.env_name or "dev"),
        test_types=request.test_types,
        browsers=request.browsers if request.mode == "A" else ["chromium"],
        parallel=request.parallel,
        duration_s=result.duration_s,
        passed=result.counters.passed,
        failed=result.counters.failed + result.counters.errors,
        skipped=result.counters.skipped,
        exit_code=result.exit_code,
    )


def config_display(config: RunConfig) -> list[str]:
    """The pytest command as shown to the user (without the interpreter path)."""
    from dashboard.services.test_executor import build_pytest_command

    return ["pytest", *build_pytest_command(config)[3:]]
