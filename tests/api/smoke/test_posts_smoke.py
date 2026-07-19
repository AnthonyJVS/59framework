"""API smoke: the /posts resource is alive and contractually sound."""

from __future__ import annotations

from typing import Any

import pytest

from framework.api.endpoints.posts_api import PostsApi
from framework.utils.assertions import assert_matches_schema, assert_status

pytestmark = [pytest.mark.api, pytest.mark.smoke]


def test_posts_list_is_alive_and_matches_schema(posts_api: PostsApi) -> None:
    """GET /posts answers 200 with a non-empty, schema-valid collection."""
    response = posts_api.list_all()
    assert_status(response, 200)
    body = response.json()
    assert_matches_schema(body, PostsApi.LIST_SCHEMA)
    assert body, "Expected the post collection to be non-empty"


def test_single_post_matches_schema(posts_api: PostsApi) -> None:
    """GET /posts/1 answers 200 and validates against the item schema."""
    response = posts_api.get(1)
    assert_status(response, 200)
    body = response.json()
    assert_matches_schema(body, PostsApi.ITEM_SCHEMA)
    assert body["id"] == 1


def test_post_can_be_created(posts_api: PostsApi, post_payload: dict[str, Any]) -> None:
    """POST /posts answers 201, assigns an id and echoes the payload."""
    response = posts_api.create(post_payload)
    assert_status(response, 201)
    body = response.json()
    assert_matches_schema(body, PostsApi.CREATED_SCHEMA)
    assert body["title"] == post_payload["title"]
    assert body["body"] == post_payload["body"]
