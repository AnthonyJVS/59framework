"""Live run: the current (or most recent) test run / load test, streamed."""

from dashboard.components import job_panel
from dashboard.components.ui import empty_state
from dashboard.state import job_manager

manager = job_manager()

if manager.current is None:
    empty_state(
        "Nothing has run since the dashboard started. Set up a run in the sidebar "
        "and press **Run tests** or **Run load test**.",
        icon=":material/play_circle:",
    )
else:
    job_panel.render(manager)
