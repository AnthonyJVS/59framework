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
