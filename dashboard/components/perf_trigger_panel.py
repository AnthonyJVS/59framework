"""Performance Results tab and k6 trigger handling.

The k6 service itself lands in Phase 8; this panel already renders any
summary it finds and explains what is missing otherwise.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import streamlit as st

from dashboard.components.sidebar import PerfRequest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
K6_SUMMARY_PATH = PROJECT_ROOT / "reports" / "k6_summary.json"


def k6_available() -> bool:
    """Whether the k6 binary is on PATH."""
    return shutil.which("k6") is not None


def _load_summary() -> dict[str, Any] | None:
    if not K6_SUMMARY_PATH.is_file():
        return None
    try:
        return json.loads(K6_SUMMARY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def handle_trigger(request: PerfRequest) -> None:
    """React to the sidebar's k6 button (full wiring arrives in Phase 8)."""
    if not request.submitted:
        return
    if not k6_available():
        st.warning(
            "k6 is not installed — install it from https://k6.io/docs/get-started/. "
            "The k6 runner service is wired up in Phase 8."
        )
        return
    st.info("k6 execution service arrives in Phase 8 — the trigger UI is ready.")


def render_results() -> None:
    """Show the latest k6 summary, when one exists."""
    summary = _load_summary()
    if summary is None:
        st.info("No k6 results yet. Configure VUs/duration in the sidebar and run a load test.")
        return
    st.json(summary)
