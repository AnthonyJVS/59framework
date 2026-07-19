"""Transport layer for API tests, wrapping Playwright's ``APIRequestContext``.

One HTTP client is shared across UI and API tests (no ``requests``/``httpx``)
so cookies and auth state can be reused between the two layers.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import APIRequestContext, APIResponse

from framework.utils.logger import get_logger

log = get_logger("api")


class BaseApiClient:
    """Thin verb-level wrapper adding logging around ``APIRequestContext``.

    Endpoint classes (``framework/api/endpoints/``) compose this client and
    expose domain methods; they never talk to Playwright directly, so the
    transport can evolve without touching endpoint or test code.
    """

    def __init__(self, context: APIRequestContext) -> None:
        self._context = context

    def _log(self, method: str, path: str, response: APIResponse) -> None:
        log.info("%s %s -> %s", method, path, response.status)

    def get(self, path: str, params: dict[str, Any] | None = None) -> APIResponse:
        """GET ``path`` (relative to the context base URL)."""
        response = self._context.get(path, params=params)
        self._log("GET", path, response)
        return response

    def post(self, path: str, payload: Any = None) -> APIResponse:
        """POST ``payload`` as JSON."""
        response = self._context.post(path, data=payload)
        self._log("POST", path, response)
        return response

    def put(self, path: str, payload: Any = None) -> APIResponse:
        """PUT ``payload`` as JSON."""
        response = self._context.put(path, data=payload)
        self._log("PUT", path, response)
        return response

    def patch(self, path: str, payload: Any = None) -> APIResponse:
        """PATCH ``payload`` as JSON."""
        response = self._context.patch(path, data=payload)
        self._log("PATCH", path, response)
        return response

    def delete(self, path: str) -> APIResponse:
        """DELETE ``path``."""
        response = self._context.delete(path)
        self._log("DELETE", path, response)
        return response
