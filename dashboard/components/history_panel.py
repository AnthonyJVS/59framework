"""History tab: table of past dashboard-triggered runs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.services import run_history


def render() -> None:
    """Show the recorded run history, newest first."""
    entries = run_history.load_history()
    if not entries:
        st.info("No runs recorded yet — trigger one from the sidebar.")
        return
    frame = pd.DataFrame(entries)
    frame["test_types"] = frame["test_types"].apply(", ".join)
    frame["browsers"] = frame["browsers"].apply(", ".join)
    frame["result"] = frame["exit_code"].apply(lambda code: "✅" if code == 0 else "❌")
    st.dataframe(
        frame[
            [
                "timestamp",
                "result",
                "mode",
                "target",
                "test_types",
                "browsers",
                "parallel",
                "duration_s",
                "passed",
                "failed",
                "skipped",
            ]
        ],
        width="stretch",
        hide_index=True,
    )
