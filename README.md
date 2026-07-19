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
playwright install chromium
copy .env.example .env
pytest -m smoke
```

## URL resolution modes

- **Mode A (fixed environments):** `pytest --env=staging` → URLs come from
  `config/environments/staging.yaml`.
- **Mode B (site scanner / explicit override):** `pytest --base-url=https://any.site`
  or `TARGET_URL=https://any.site` → wins over environment config.
