"""Scan Results tab (Mode B): broken links, console errors, perf summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCAN_RESULTS_PATH = PROJECT_ROOT / "reports" / "scan_results.json"


def _load() -> dict[str, Any] | None:
    if not SCAN_RESULTS_PATH.is_file():
        return None
    try:
        return json.loads(SCAN_RESULTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def render() -> None:
    """Show the latest Site Scanner results, if any."""
    scan = _load()
    if scan is None:
        st.info(
            "No scan results yet. Paste an unknown URL in the sidebar and run "
            "the Site Scanner (Mode B)."
        )
        return

    st.caption(
        f"Scanned **{scan['start_url']}** at depth {scan['max_depth']} " f"({scan['generated_at']})"
    )

    results = scan.get("results", [])
    broken = [result for result in results if not result.get("ok")]
    issues = scan.get("console_issues", [])
    timing = scan.get("timing", {})

    cols = st.columns(4)
    cols[0].metric("Links checked", len(results))
    cols[1].metric("Broken links", len(broken))
    cols[2].metric("Console errors", len(issues))
    cols[3].metric("Page load", f"{timing.get('load_ms', 0):.0f} ms")

    st.subheader("Broken links")
    if broken:
        st.dataframe(
            pd.DataFrame(broken)[["status", "url", "found_on", "error"]],
            use_container_width=True,
        )
    else:
        st.success("No broken links found.")

    st.subheader("Console / page errors")
    if issues:
        st.dataframe(
            pd.DataFrame(issues)[["kind", "page_url", "text"]],
            use_container_width=True,
        )
    else:
        st.success("No browser errors captured.")

    st.subheader("Performance signals (start page)")
    st.write(
        {
            "TTFB": f"{timing.get('ttfb_ms', 0):.0f} ms",
            "DOMContentLoaded": f"{timing.get('dom_content_loaded_ms', 0):.0f} ms",
            "Load": f"{timing.get('load_ms', 0):.0f} ms",
        }
    )
