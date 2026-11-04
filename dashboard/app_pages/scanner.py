"""Site scanner: results of the most recent Mode B scan."""

import pandas as pd
import streamlit as st

from dashboard.components.ui import empty_state, fmt_ms, fmt_timestamp
from dashboard.services import scan_results

scan = scan_results.load()
if scan is None:
    empty_state(
        "No scan yet. Paste any URL that is not a configured environment into "
        "**Target URL** in the sidebar and press **Run tests**.",
        icon=":material/travel_explore:",
    )
    st.stop()

results = scan.get("results", [])
broken = [result for result in results if not result.get("ok")]
issues = scan.get("console_issues", [])
first_party = [issue for issue in issues if not issue.get("third_party")]
timing = scan.get("timing", {})
budget = scan.get("load_budget_ms")
load_ms = timing.get("load_ms")

st.caption(
    f"Scanned [{scan['start_url']}]({scan['start_url']}) at depth {scan['max_depth']} · "
    f"{len(scan.get('visited_pages', []))} page(s) opened · {fmt_timestamp(scan['generated_at'])}"
)

with st.container(horizontal=True):
    st.metric("Links checked", len(results), border=True)
    st.metric(
        "Broken links",
        len(broken),
        border=True,
        help="Links whose final response was not 2xx/3xx, or that did not answer at all.",
    )
    st.metric(
        "Console errors",
        len(issues),
        border=True,
        help=f"{len(first_party)} from the site itself, {len(issues) - len(first_party)} "
        f"from third-party scripts. {scan.get('ignored_console_count', 0)} ignored by filter.",
    )
    st.metric(
        "Page load",
        fmt_ms(load_ms),
        delta=(
            f"{'over' if load_ms > budget else 'within'} {fmt_ms(budget)} budget"
            if budget and load_ms is not None
            else None
        ),
        delta_color="inverse" if budget and load_ms and load_ms > budget else "normal",
        delta_arrow="off",
        border=True,
        help=f"TTFB {fmt_ms(timing.get('ttfb_ms'))}, DOMContentLoaded "
        f"{fmt_ms(timing.get('dom_content_loaded_ms'))} — measured cold, before the crawl.",
    )

link_columns = {
    "status": st.column_config.NumberColumn("Status", format="%d", width="small"),
    "url": st.column_config.LinkColumn("URL", width="large"),
    "found_on": st.column_config.LinkColumn("Found on"),
    "error": "Error",
    "external": st.column_config.CheckboxColumn("External", width="small"),
}

broken_tab, console_tab, links_tab, video_tab = st.tabs(
    [
        f":material/link_off: Broken links ({len(broken)})",
        f":material/terminal: Console ({len(issues)})",
        f":material/link: All links ({len(results)})",
        ":material/videocam: Recording",
    ]
)

with broken_tab:
    if broken:
        st.dataframe(
            pd.DataFrame(broken),
            hide_index=True,
            column_order=["status", "url", "found_on", "error", "external"],
            column_config=link_columns,
        )
    else:
        st.success("Every checked link resolved.", icon=":material/check_circle:")

with console_tab:
    if issues:
        hide_third_party = st.toggle(
            "Hide third-party scripts",
            help="Errors emitted by scripts loaded from other origins (ads, analytics, widgets).",
        )
        shown = first_party if hide_third_party else issues
        st.dataframe(
            pd.DataFrame(shown) if shown else pd.DataFrame(columns=["kind", "page_url", "text"]),
            hide_index=True,
            column_order=["kind", "page_url", "text", "source_url", "third_party"],
            column_config={
                "kind": st.column_config.TextColumn("Kind", width="small"),
                "page_url": st.column_config.LinkColumn("Page"),
                "text": st.column_config.TextColumn("Message", width="large"),
                "source_url": st.column_config.LinkColumn("Source"),
                "third_party": st.column_config.CheckboxColumn("3rd party", width="small"),
            },
        )
    else:
        st.success("No browser errors captured.", icon=":material/check_circle:")

with links_tab:
    st.dataframe(
        pd.DataFrame(results),
        hide_index=True,
        column_order=["status", "url", "found_on", "external", "error"],
        column_config=link_columns,
    )

with video_tab:
    if scan_results.VIDEO_PATH.is_file():
        st.video(str(scan_results.VIDEO_PATH), format="video/webm")
    else:
        st.caption(
            "No recording for this scan. Turn on **Record video** in the sidebar before "
            "scanning to capture one."
        )
