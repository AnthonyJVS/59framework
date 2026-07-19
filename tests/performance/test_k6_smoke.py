"""Lightweight k6 smoke check triggered from pytest (``performance`` marker).

Reuses the same k6 service as the Streamlit dashboard so both entry points
share one execution path and one summary format. Skips when k6 is absent
(e.g. contributors without the binary) rather than failing.
"""

from __future__ import annotations

import pytest

from dashboard.services.k6_service import K6Config, k6_available, run_k6

pytestmark = [
    pytest.mark.performance,
    pytest.mark.skipif(not k6_available(), reason="k6 binary not installed"),
]


def test_homepage_handles_light_load(base_url: str) -> None:
    """A short 2-VU burst against the homepage stays inside the thresholds."""
    summary, exit_code, message = run_k6(K6Config(target_url=base_url, vus=2, duration_s=5))
    assert summary is not None, message
    assert summary.requests > 0, "k6 sent no requests"
    assert summary.error_rate == 0, f"{summary.error_rate:.2%} of requests failed"
    assert exit_code == 0, message
