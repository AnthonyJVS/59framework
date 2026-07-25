"""Scan Video tab (Mode B): recording of the most recent Site Scanner crawl."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCAN_VIDEO_PATH = PROJECT_ROOT / "reports" / "scan_video.webm"


def render() -> None:
    """Show the latest Site Scanner recording, if one was made."""
    if not SCAN_VIDEO_PATH.is_file():
        st.info(
            "No scan recording yet. Enable **🎥 Record browser session** in the "
            "sidebar before running the Site Scanner (Mode B) to capture one."
        )
        return
    st.caption("Recording of the most recent Site Scanner crawl:")
    st.video(str(SCAN_VIDEO_PATH))
