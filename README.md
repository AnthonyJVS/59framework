# Test Automation Framework

Production-ready Python test automation framework: **Playwright + pytest** for
UI and API testing, a **Streamlit control-panel dashboard**, **Allure**
reporting with failure screenshots and traces, **k6** performance testing, a
generic **Site Scanner** for arbitrary URLs, and **GitHub Actions** CI/CD.

Demo targets: [SauceDemo](https://www.saucedemo.com) (UI) and
[JSONPlaceholder](https://jsonplaceholder.typicode.com) (API) — swappable for
a real application via config only.

## Setup

Prerequisites: Python 3.11+, Node.js (for the Allure CLI), Java 8+ (Allure),
and optionally [k6](https://k6.io) and Docker.

```bash
python -m venv .venv
.venv\Scripts\activate                # Windows (POSIX: source .venv/bin/activate)
pip install -r requirements.txt
playwright install chromium firefox webkit
npm install -g allure-commandline     # report rendering
winget install GrafanaLabs.k6         # performance tests (optional)
copy .env.example .env                # then adjust as needed
```

> On machines with an Application Control policy that blocks compiled wheels,
> install black as pure Python: `pip install --force-reinstall --no-binary black black`.

## Running tests

```bash
pytest -m smoke                        # fast critical-path suite
pytest -m "regression or api"          # full functional coverage
pytest -m smoke --browser=firefox      # one alternate engine
pytest --browser chromium --browser firefox --browser webkit   # 3-browser matrix
pytest -n auto                         # parallel (pytest-xdist)
pytest -m regression -n 4 --reruns 1   # parallel + flaky retry
pytest -m performance                  # k6 smoke (skips without k6)
```

Registered markers: `smoke`, `regression`, `api`, `ui`, `scanner`,
`cross_browser`, `performance`.

## URL resolution modes

The same fixture layer serves two modes (highest priority first):

1. **Explicit override (Mode B)** — `--base-url=…` / `TARGET_URL`
   (`--api-base-url` / `API_TARGET_URL` for the API). Used by the Site Scanner.
2. **Environment config (Mode A)** — `--env=dev|staging|prod` / `ENV`, resolved
   through `config/environments/<env>.yaml` with `${VAR:default}` interpolation
   from `.env`.
3. **Default** — `dev`.

## Site Scanner (Mode B)

```bash
pytest tests/scanner --base-url=https://any.site --scan-depth=1 --scan-max-pages=15
```

Breadth-first same-origin crawl that flags non-2xx/3xx links, captures
error-severity console output and uncaught JS exceptions, and checks the start
page's load time against `--scan-load-budget-ms` (default 10 s). Fully
selector-agnostic — no Page Objects. Without a target URL the scanner tests
skip, so Modes A and B coexist in one run. Results also land in
`reports/scan_results.json` for the dashboard.

## Streamlit dashboard

```bash
streamlit run dashboard/app.py
```

- **Sidebar** — target URL (auto-routes: known URL → Mode A, unknown → Site
  Scanner), environment, test types, browsers, serial/parallel, and a k6
  section (VUs / duration).
- **Live Run** — the exact pytest command, streamed output, live pass/fail
  counters.
- **Allure Report** — embedded latest report + full-screen link.
- **Performance Results** — k6 metrics, latency-distribution chart, trend
  across runs.
- **Scan Results** — broken links, console errors, load timing (Mode B).
- **History** — persisted table of past runs.

## Reporting (Allure)

Every pytest run writes `reports/allure-results` (latest-run semantics).
Failures attach a full-page screenshot and a Playwright trace zip
(`reports/traces/`, inspectable via `playwright show-trace`).

```bash
allure serve reports/allure-results    # one-shot local view
allure generate reports/allure-results -o reports/allure-report --clean
```

## Performance testing (k6)

Scripts in `performance/k6-scripts/` (`homepage_load.js`, `checkout_flow.js`)
are env-driven; defaults and thresholds live in `performance/perf_config.yaml`.
Triggered from the dashboard sidebar or `pytest -m performance` — both go
through `dashboard/services/k6_service.py`, which parses k6's JSON summary
into `reports/k6_summary.json` (+ bounded history for trend charts).
Note: SPA inner routes 404 over plain HTTP, so `flow_paths` must list real
server routes.

## Docker

```bash
docker compose -f docker/docker-compose.yml run --rm tests                  # smoke
docker compose -f docker/docker-compose.yml run --rm tests \
    python -m pytest -m regression -n auto
docker compose -f docker/docker-compose.yml up dashboard                    # :8501
```

`docker/Dockerfile.playwright` bundles Playwright browsers + k6 so local and
CI runs share one environment.

## CI/CD (GitHub Actions)

- **ci-tests.yml** — on push/PR to `main`/`develop`: smoke suite across a
  3-browser matrix with retries; per-browser Allure results uploaded and
  merged into one artifact. `workflow_dispatch` offers suite
  (smoke/regression/all), environment, and an optional k6 perf job. Optional
  GitHub Pages publishing of the Allure report (set repo variable
  `PUBLISH_ALLURE_PAGES=true`).
- **nightly-regression.yml** — full suite × 3 browsers + k6 smoke every night
  at 02:00 UTC.

## Project layout

```
config/            environment YAMLs + ${VAR} interpolating loader
framework/
  core/            BasePage, DriverFactory
  pages/           SauceDemo Page Objects (strict POM)
  api/             BaseApiClient, endpoint layer, JSON schemas
  scanner/         link crawler, console error capture, perf probe
  utils/           assertions (schema validation), Faker data, logger
tests/
  ui/  api/        smoke + regression suites (Mode A)
  scanner/         generic site scan (Mode B, self-contained fixtures)
  performance/     pytest-triggered k6 smoke
dashboard/         Streamlit app: components + services (executor, allure, k6)
performance/       k6 scripts + perf_config.yaml
docker/            Dockerfile.playwright + docker-compose.yml
.github/workflows/ ci-tests.yml, nightly-regression.yml
reports/           allure-results/report, traces, JSON artifacts (gitignored)
```

## Coding standards

Strict Page Object Model (no selectors in tests), config only via
`config_loader.py`/fixtures, type hints + docstrings throughout, `ruff` +
`black` (`ruff check . && black .`).
