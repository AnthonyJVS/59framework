"""Process-wide dashboard state shared by every page and browser session."""

from __future__ import annotations

import streamlit as st

from dashboard.services.job_manager import JobManager


@st.cache_resource
def job_manager() -> JobManager:
    """The single job manager: one run at a time for the whole dashboard.

    Cached as a resource (not per session) on purpose — runs write to shared
    folders under ``reports/``, so two concurrent runs would corrupt each other.
    """
    return JobManager()
