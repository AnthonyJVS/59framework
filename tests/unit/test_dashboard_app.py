"""Headless render tests for every dashboard page (streamlit.testing AppTest).

Each page is rendered twice: against empty report folders (fresh checkout) and
against a populated set of artifacts, and must not raise in either case.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.services import allure_service, k6_service, run_history, scan_results

pytestmark = [pytest.mark.unit]

ENTRYPOINT = str(Path(__file__).resolve().parents[2] / "dashboard" / "app.py")
PAGES = [
    "app_pages/overview.py",
    "app_pages/live_run.py",
    "app_pages/allure_report.py",
    "app_pages/performance.py",
    "app_pages/scanner.py",
    "app_pages/history.py",
]


@pytest.fixture
def reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every artifact path the dashboard reads at an empty temp folder."""
    monkeypatch.setattr(run_history, "HISTORY_PATH", tmp_path / "run_history.json")
    monkeypatch.setattr(k6_service, "HISTORY_PATH", tmp_path / "k6_history.json")
    monkeypatch.setattr(k6_service, "SUMMARY_PATH", tmp_path / "k6_summary.json")
    monkeypatch.setattr(scan_results, "RESULTS_PATH", tmp_path / "scan_results.json")
    monkeypatch.setattr(scan_results, "VIDEO_PATH", tmp_path / "scan_video.webm")
    monkeypatch.setattr(allure_service, "REPORT_DIR", tmp_path / "allure-report")
    monkeypatch.setattr(allure_service, "allure_available", lambda: False)
    return tmp_path


def _populate(folder: Path) -> None:
    runs = [
        {
            "timestamp": f"2026-11-0{day}T10:00:00",
            "status": status,
            "mode": "A",
            "target": "dev",
            "test_types": ["Smoke"],
            "browsers": ["chromium"],
            "parallel": False,
            "duration_s": 30.0 + day,
            "passed": 10 - failed,
            "failed": failed,
            "skipped": 0,
            "exit_code": 0 if status == "passed" else 1,
        }
        for day, status, failed in ((3, "passed", 0), (2, "failed", 2), (1, "passed", 0))
    ]
    # an entry written by an older version (no status field) must still load
    legacy = {k: v for k, v in runs[-1].items() if k != "status"}
    (folder / "run_history.json").write_text(json.dumps([*runs, legacy]), encoding="utf-8")

    k6_runs = [
        {
            "target_url": "https://www.saucedemo.com",
            "script": "homepage_load.js",
            "vus": 5,
            "duration_s": 30,
            "started_at": f"2026-11-0{day}T09:00:00",
            "requests": 300,
            "rps": 10.0,
            "error_rate": 0.0,
            "latency_avg_ms": 120.0,
            "latency_med_ms": 100.0,
            "latency_p90_ms": 200.0,
            "latency_p95_ms": 250.0 + day,
            "latency_max_ms": 900.0,
            "thresholds_passed": True,
        }
        for day in (2, 1)
    ]
    (folder / "k6_history.json").write_text(json.dumps(k6_runs), encoding="utf-8")

    scan = {
        "generated_at": "2026-11-03T11:00:00",
        "start_url": "https://site.test",
        "max_depth": 1,
        "visited_pages": ["https://site.test"],
        "results": [
            {"url": "https://site.test", "status": 200, "ok": True, "found_on": None},
            {"url": "https://site.test/gone", "status": 404, "ok": False, "found_on": "x"},
        ],
        "console_issues": [
            {"kind": "console-error", "page_url": "https://site.test", "text": "boom"}
        ],
        "timing": {"url": "https://site.test", "ttfb_ms": 80, "load_ms": 1200},
        "load_budget_ms": 10000,
    }
    (folder / "scan_results.json").write_text(json.dumps(scan), encoding="utf-8")


def _render(page: str) -> AppTest:
    app = AppTest.from_file(ENTRYPOINT, default_timeout=30)
    app.run()
    if page != PAGES[0]:
        app.switch_page(page)
        app.run()
    return app


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_data(reports: Path, page: str) -> None:
    app = _render(page)
    assert not app.exception, app.exception


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_data(reports: Path, page: str) -> None:
    _populate(reports)
    app = _render(page)
    assert not app.exception, app.exception


def test_sidebar_switches_to_scanner_mode_for_unknown_url(reports: Path) -> None:
    app = _render(PAGES[0])
    app.sidebar.text_input[0].set_value("https://unknown.example").run()
    assert not app.exception, app.exception
    # st.badge renders as an ":orange-badge[…]" markdown element
    assert any("badge[" in md.value and "Mode B" in md.value for md in app.sidebar.markdown)
    assert [field.label for field in app.sidebar.number_input][:2] == ["Crawl depth", "Max pages"]
