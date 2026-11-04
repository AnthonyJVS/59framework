<div align="center">

# 59framework

**Production-ready test automation framework** — Playwright + pytest for UI & API,
a Streamlit control panel, Allure reporting, k6 performance tests
and a generic Site Scanner that works against *any* URL.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)](https://pytest.org)
[![CI](https://img.shields.io/github/actions/workflow/status/AnthonyJVS/59framework/ci-tests.yml?branch=main&style=for-the-badge&label=CI&logo=githubactions&logoColor=white)](../../actions/workflows/ci-tests.yml)

</div>

---

## Tech stack

<table>
<tr>
  <td><b>Core</b></td>
  <td>
    <img src="https://img.shields.io/badge/Python_3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Playwright-2EAD33?style=flat-square&logo=playwright&logoColor=white" alt="Playwright">
    <img src="https://img.shields.io/badge/pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="pytest">
    <img src="https://img.shields.io/badge/xdist_·_rerunfailures-0A9EDC?style=flat-square" alt="pytest plugins">
  </td>
</tr>
<tr>
  <td><b>API&nbsp;&&nbsp;Data</b></td>
  <td>
    <img src="https://img.shields.io/badge/APIRequestContext-2EAD33?style=flat-square&logo=playwright&logoColor=white" alt="APIRequestContext">
    <img src="https://img.shields.io/badge/JSON_Schema-000000?style=flat-square&logo=json&logoColor=white" alt="JSON Schema">
    <img src="https://img.shields.io/badge/Faker-4B8BBE?style=flat-square" alt="Faker">
    <img src="https://img.shields.io/badge/YAML_+_dotenv-CB171E?style=flat-square&logo=yaml&logoColor=white" alt="YAML + dotenv">
  </td>
</tr>
<tr>
  <td><b>Reporting</b></td>
  <td>
    <img src="https://img.shields.io/badge/Allure-FF6C37?style=flat-square&logo=qameta&logoColor=white" alt="Allure">
    <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
    <img src="https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white" alt="pandas">
  </td>
</tr>
<tr>
  <td><b>Performance</b></td>
  <td>
    <img src="https://img.shields.io/badge/k6-7D64FF?style=flat-square&logo=k6&logoColor=white" alt="k6">
    <img src="https://img.shields.io/badge/Navigation_Timing_API-5A5A5A?style=flat-square" alt="Navigation Timing API">
  </td>
</tr>
<tr>
  <td><b>AI</b></td>
  <td>
    <img src="https://img.shields.io/badge/Google_Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white" alt="Google Gemini">
  </td>
</tr>
<tr>
  <td><b>CI&nbsp;&&nbsp;Infra</b></td>
  <td>
    <img src="https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions">
    <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
    <img src="https://img.shields.io/badge/Ruff_+_Black-000000?style=flat-square&logo=ruff&logoColor=white" alt="Ruff + Black">
  </td>
</tr>
</table>

## Features

| | |
|---|---|
| **Two testing modes** | Mode A — fixed suites against a configured environment. Mode B — Site Scanner against any arbitrary URL. Both coexist in one run. |
| **UI tests** | Strict Page Object Model, zero selectors in tests, cross-browser matrix (Chromium / Firefox / WebKit). |
| **API tests** | Playwright `APIRequestContext` + JSON Schema contract validation. |
| **Site Scanner** | Selector-agnostic crawl: broken links, JS console errors, page load budget — no Page Objects needed. |
| **Dashboard** | Streamlit control panel: background runs with live progress and stop, reports, trends, history. |
| **Reporting** | Allure with a screenshot + Playwright trace attached to every failure. |
| **Performance** | k6 load scripts with thresholds, trend charts across runs. |
| **AI analysis** | One-click Gemini explanation of a failed run's log. |
| **CI/CD** | GitHub Actions: per-push smoke matrix, nightly full regression, merged Allure artifact. |
| **Docker** | One image with browsers + k6, so local and CI runs are identical. |

Demo targets: [SauceDemo](https://www.saucedemo.com) (UI) and
[JSONPlaceholder](https://jsonplaceholder.typicode.com) (API) — swappable for a
real application via config only.

## Quick start

Prerequisites: Python 3.11+, Node.js (Allure CLI), Java 8+ (Allure), optionally
[k6](https://k6.io) and Docker.

```bash
python -m venv .venv
.venv\Scripts\activate                # Windows (POSIX: source .venv/bin/activate)
pip install -r requirements.txt
playwright install chromium firefox webkit
npm install -g allure-commandline     # report rendering
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
pytest -m unit                         # framework/dashboard logic, no browser or network
```

Markers: `smoke`, `regression`, `api`, `ui`, `scanner`, `cross_browser`, `performance`, `unit`.

## URL resolution

One fixture layer, three priorities:

1. **Explicit override (Mode B)** — `--base-url=…` / `TARGET_URL`
   (`--api-base-url` / `API_TARGET_URL` for the API).
2. **Environment config (Mode A)** — `--env=dev|staging|prod` / `ENV`, resolved via
   `config/environments/<env>.yaml` with `${VAR:default}` interpolation from `.env`.
3. **Default** — `dev`.

## Site Scanner (Mode B)

```bash
pytest tests/scanner --base-url=https://any.site --scan-depth=2 --scan-max-pages=15
```

Measures the start page's load time first, in a fresh browser context (cold
cache), against `--scan-load-budget-ms` (default 10 s). Then crawls the site
breadth-first: same-origin pages up to depth − 1 are opened in the browser
(capturing error-level console output and uncaught JS exceptions), and every
link at the last level is status-checked concurrently over HTTP. Non-2xx/3xx
links are reported as broken.

| Option | Effect |
|---|---|
| `--scan-depth=N` | Link levels followed from the start page (default 1). |
| `--scan-max-pages=N` | Cap on pages opened in the browser (default 15). |
| `--scan-external` | Also status-check links to other sites (never crawled). |
| `--scan-ignore-console=REGEX` | Ignore console errors matching REGEX; repeatable. |
| `--scan-record-video` | Save a `.webm` of the crawl for the dashboard. |

Without a target URL the scanner tests simply skip. Results land in
`reports/scan_results.json`.

## Dashboard

```bash
streamlit run dashboard/app.py
```

Runs and load tests execute **in the background**: you can switch pages,
refresh the browser or keep configuring while one runs, and stop it at any time.
One run at a time, so concurrent runs never overwrite each other's reports.

- **Sidebar** — run setup: target URL (a known URL → Mode A, any other → Site
  Scanner), environment, suites, browsers, serial/parallel, retries, scanner
  options, and the k6 script/VUs/duration (defaults from `perf_config.yaml`).
- **Overview** — latest run with pass-rate and duration trends, green streak,
  latest load test and scan, and which tools (Allure, k6, Gemini) are set up.
- **Live run** — the exact command, a progress bar, live counters and log,
  **Stop**, **Download log**, **Re-run failed tests**, and **Analyze with Gemini**.
- **Report** — the embedded Allure report (with trend history across runs).
- **Performance** — k6 latency/throughput/error rate with deltas to the previous
  comparable run (same target and script) and a trend chart.
- **Site scanner** — broken links, console errors (third-party ones can be
  hidden), all checked links, load time against budget, and the crawl recording.
- **History** — every run with filters, pass-rate and duration charts.

The theme (light and dark) lives in `.streamlit/config.toml`; the dashboard
listens on `localhost` only unless started with `--server.address`.

> **Analyze with Gemini** needs `GEMINI_API_KEY` in `.env`
> ([free key](https://aistudio.google.com/apikey)); `GEMINI_MODEL` overrides the model.

## Reporting

Every run writes `reports/allure-results` (latest-run semantics). Failures attach a
full-page screenshot and a Playwright trace zip (`reports/traces/`, inspectable via
`playwright show-trace`).

```bash
allure serve reports/allure-results    # one-shot local view
allure generate reports/allure-results -o reports/allure-report --clean
```

## Performance (k6)

Env-driven scripts in `performance/k6-scripts/` (`homepage_load.js`,
`checkout_flow.js`); defaults and thresholds in `performance/perf_config.yaml`.
Triggered from the dashboard or `pytest -m performance` — both go through
`dashboard/services/k6_service.py`, which parses k6's JSON summary into
`reports/k6_summary.json` plus a bounded history for trend charts.

## Docker

```bash
docker compose -f docker/docker-compose.yml run --rm tests                  # smoke
docker compose -f docker/docker-compose.yml run --rm tests \
    python -m pytest -m regression -n auto
docker compose -f docker/docker-compose.yml up dashboard                    # :8501
```

`docker/Dockerfile.playwright` bundles Playwright browsers + k6, so local and CI
runs share one environment.

## CI/CD

- **`ci-tests.yml`** — on push/PR to `main`/`develop`: smoke suite across a 3-browser
  matrix with retries; per-browser Allure results uploaded and merged into one
  artifact. `workflow_dispatch` offers suite (smoke/regression/all), environment and
  an optional k6 job. Optional GitHub Pages publishing (repo variable
  `PUBLISH_ALLURE_PAGES=true`).
- **`nightly-regression.yml`** — full suite × 3 browsers + k6 smoke, nightly at 02:00 UTC;
  merged results and an HTML Allure report are uploaded as artifacts.

Every job writes a pass/fail table (with failing tests and messages) to its GitHub
job summary via `.github/scripts/allure_summary.py`; a `lint-unit` job runs ruff,
black and the unit tests. Published Pages reports keep Allure trend history.

## Layout

```
config/            environment YAMLs + ${VAR} interpolating loader
framework/
  core/            BasePage, DriverFactory
  pages/           Page Objects (strict POM)
  api/             BaseApiClient, endpoint layer, JSON schemas
  scanner/         link crawler, console error capture, perf probe
  utils/           assertions (schema validation), Faker data, logger
tests/
  ui/  api/        smoke + regression suites (Mode A)
  scanner/         generic site scan (Mode B, self-contained fixtures)
  performance/     pytest-triggered k6 smoke
dashboard/         Streamlit app: app.py (entry), app_pages/, components/,
                   services/ (job manager, executor, allure, k6, gemini, history)
performance/       k6 scripts + perf_config.yaml
docker/            Dockerfile.playwright + docker-compose.yml
.github/workflows/ ci-tests.yml, nightly-regression.yml
reports/           allure-results/report, traces, JSON artifacts (gitignored)
```

## Coding standards

Strict Page Object Model (no selectors in tests), config only via
`config_loader.py` / fixtures, type hints and docstrings throughout, `ruff` + `black`:

```bash
ruff check . && black .
```
