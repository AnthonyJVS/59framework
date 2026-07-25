"""Gemini-backed explanation of a Live Run's console output.

Triggered on demand from the Live Run tab ("Analyze with Gemini") once a run
has failures/errors — never called automatically. See
``dashboard/components/test_runner_panel.py``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

MODEL = "gemini-3.5-flash"
LOG_TAIL_CHARS = 8000  # matches the tail already shown in the Live Run log view

# Transient server-side codes worth a short retry (rate limit / momentary
# overload) — not auth/bad-request codes, which will just fail again.
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_RETRY_DELAY_S = 2.0

_SYSTEM_INSTRUCTION = (
    "You are looking at the tail of a pytest run's console output from a "
    "test-automation dashboard. It may contain Playwright UI/API test failures "
    "or Site Scanner results (broken links, browser console errors). Explain "
    "concisely what went wrong, point at the specific failing test or issue, "
    "and suggest a concrete next step. Keep it short: a few sentences or a "
    "short bullet list, not an essay."
)


def _current_api_key() -> str | None:
    """Re-read .env on every call.

    Unlike the pytest/k6 runs (which spawn a fresh subprocess and pick up
    .env naturally), this service is called in-process inside the
    long-running Streamlit server — without ``override=True`` here, editing
    .env after the dashboard has started would never be picked up.
    """
    load_dotenv(ENV_PATH, override=True)
    return os.environ.get("GEMINI_API_KEY") or None


def gemini_available() -> bool:
    """Whether GEMINI_API_KEY is configured — gates the Analyze button on/off."""
    return _current_api_key() is not None


def analyze_log(log_text: str) -> str:
    """Ask Gemini to explain the tail of a run's console output.

    Retries a couple of times on transient server errors (e.g. 503
    "model overloaded", common on the free tier) before giving up. Any other
    error (bad key, invalid request, exhausted retries) is raised as-is — the
    caller is responsible for turning that into a UI-facing message.
    """
    api_key = _current_api_key()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    client = genai.Client(api_key=api_key)
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=log_text[-LOG_TAIL_CHARS:],
                config=types.GenerateContentConfig(system_instruction=_SYSTEM_INSTRUCTION),
            )
            return response.text
        except errors.APIError as exc:
            if exc.code not in _RETRYABLE_CODES or attempt == _MAX_ATTEMPTS:
                raise
            time.sleep(_RETRY_DELAY_S)
    raise AssertionError("unreachable")  # loop always returns or raises
