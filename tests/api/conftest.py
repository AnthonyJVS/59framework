"""API-suite fixtures: a shared APIRequestContext and endpoint objects.

The request context resolves its base URL through the same dual-mode
hierarchy as the UI suite (see the root conftest's ``api_base_url``).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from playwright.sync_api import APIRequestContext, Playwright

from framework.api.clients.base_api_client import BaseApiClient
from framework.api.endpoints.posts_api import PostsApi
from framework.utils.data_generator import DataGenerator


@pytest.fixture(scope="session")
def api_request_context(
    playwright: Playwright, api_base_url: str
) -> Generator[APIRequestContext, None, None]:
    """One APIRequestContext for the whole session, targeting ``api_base_url``."""
    context = playwright.request.new_context(
        base_url=api_base_url,
        extra_http_headers={"Accept": "application/json"},
    )
    yield context
    context.dispose()


@pytest.fixture(scope="session")
def posts_api(api_request_context: APIRequestContext) -> PostsApi:
    """Endpoint object for /posts, composed over the shared client."""
    return PostsApi(BaseApiClient(api_request_context))


@pytest.fixture
def post_payload() -> dict[str, Any]:
    """Random-but-valid create payload for /posts."""
    return DataGenerator().post_payload()
