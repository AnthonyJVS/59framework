"""Small shared UI helpers: status badges, formatting, empty states."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

#: How each run status is shown everywhere in the dashboard.
STATUS_STYLE: dict[str, tuple[str, str, str]] = {
    # status: (label, badge color, material icon)
    "running": ("Running", "blue", ":material/progress_activity:"),
    "passed": ("Passed", "green", ":material/check_circle:"),
    "failed": ("Failed", "red", ":material/cancel:"),
    "stopped": ("Stopped", "gray", ":material/stop_circle:"),
    "error": ("Error", "orange", ":material/error:"),
}


def status_badge(status: str) -> None:
    """A colored badge for a run status."""
    label, color, icon = STATUS_STYLE.get(status, (status.title(), "gray", None))
    st.badge(label, icon=icon, color=color)  # type: ignore[arg-type]


def status_label(status: str) -> str:
    """Plain-text status with a symbol, for tables."""
    symbols = {"passed": "✓", "failed": "✕", "stopped": "■", "error": "!", "running": "…"}
    label = STATUS_STYLE.get(status, (status.title(), "", ""))[0]
    return f"{symbols.get(status, '·')} {label}"


def fmt_duration(seconds: float | None) -> str:
    """``42s``, ``3m 05s`` or ``1h 02m``."""
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m"


def fmt_timestamp(value: str | datetime | None) -> str:
    """ISO timestamp → ``4 Nov, 23:31`` (adds the year when it is not this year)."""
    if value is None:
        return "—"
    moment = value if isinstance(value, datetime) else _parse(value)
    if moment is None:
        return str(value)
    pattern = "%d %b, %H:%M" if moment.year == datetime.now().year else "%d %b %Y, %H:%M"
    return moment.strftime(pattern).lstrip("0")


def _parse(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def fmt_ms(value: float | None) -> str:
    """Milliseconds, switching to seconds above 10 s."""
    if value is None:
        return "—"
    return f"{value / 1000:.1f} s" if value >= 10_000 else f"{value:,.0f} ms"


def empty_state(message: str, icon: str = ":material/inbox:") -> None:
    """A quiet bordered placeholder for sections that have no data yet."""
    with st.container(border=True):
        st.markdown(f"{icon} &nbsp; {message}")
