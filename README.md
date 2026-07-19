# Test Automation Framework

Playwright + pytest test automation framework with a Streamlit control-panel
dashboard, Allure reporting, k6 performance testing, and a generic Site
Scanner mode for arbitrary URLs.

> **Status:** Phase 1 (framework skeleton) — full setup/usage documentation
> lands in Phase 9.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium firefox webkit
copy .env.example .env
pytest -m smoke
```

## Cross-browser & parallel execution

```bash
pytest -m smoke --browser=firefox            # one alternate browser
pytest --browser chromium --browser firefox --browser webkit   # full matrix
pytest -m cross_browser --browser chromium --browser firefox --browser webkit
pytest -n auto                               # parallel via pytest-xdist
pytest -m regression -n 4 --reruns 1         # parallel + flaky retry
```

Repeating `--browser` parametrizes every browser-backed test per engine
(test ids get `[chromium]`/`[firefox]`/`[webkit]` suffixes); API tests run
once regardless. Markers compose freely with browser and xdist flags.

## URL resolution modes

- **Mode A (fixed environments):** `pytest --env=staging` → URLs come from
  `config/environments/staging.yaml`.
- **Mode B (site scanner / explicit override):** `pytest --base-url=https://any.site`
  or `TARGET_URL=https://any.site` → wins over environment config.

## Streamlit dashboard

```bash
streamlit run dashboard/app.py
```

Sidebar: target URL (auto-routes Mode A/B), environment, test types, browsers,
serial/parallel, plus a k6 section. Tabs: Live Run (streamed output +
pass/fail counters), Allure Report (embedded latest report), Performance
Results, Scan Results (Mode B), History (persisted across restarts).

## Performance testing (k6)

Requires the [k6](https://k6.io) binary (`winget install GrafanaLabs.k6`).

- **Dashboard:** set VUs/duration in the sidebar and press *Run k6 Load Test*;
  results render in the Performance Results tab (latency distribution + trend).
- **pytest:** `pytest -m performance` runs a lightweight homepage smoke through
  the same service (skips when k6 is absent).
- Scripts live in `performance/k6-scripts/`; defaults and thresholds in
  `performance/perf_config.yaml`. Note: SPA inner routes 404 over plain HTTP,
  so `flow_paths` lists only real server routes.

## Site Scanner (Mode B)

```bash
pytest tests/scanner --base-url=https://any.site --scan-depth=1 --scan-max-pages=15
```

Crawls same-origin links breadth-first up to `--scan-depth`, flags any link
whose final response is not 2xx/3xx, captures error-severity console output
and uncaught JS exceptions, and checks the start page's load time against
`--scan-load-budget-ms` (default 10s). Fully selector-agnostic — no Page
Objects involved. Without an explicit target URL the scanner tests skip, so
they can sit in the same run as the fixed-environment suites.
