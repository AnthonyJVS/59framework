"""API regression: CRUD verbs, filtering and nested resources on /posts."""

from __future__ import annotations

from typing import Any

import pytest

from framework.api.endpoints.posts_api import PostsApi
from framework.utils.assertions import assert_matches_schema, assert_status

pytestmark = [pytest.mark.api, pytest.mark.regression]


def test_filter_by_user_returns_only_that_users_posts(posts_api: PostsApi) -> None:
    """GET /posts?userId=1 returns a non-empty list all authored by user 1."""
    response = posts_api.list_by_user(1)
    assert_status(response, 200)
    body = response.json()
    assert_matches_schema(body, PostsApi.LIST_SCHEMA)
    assert body, "Expected user 1 to have posts"
    assert all(post["userId"] == 1 for post in body)


def test_nested_comments_belong_to_post(posts_api: PostsApi) -> None:
    """GET /posts/1/comments validates (incl. email format) and references post 1."""
    response = posts_api.comments_for(1)
    assert_status(response, 200)
    body = response.json()
    assert_matches_schema(body, PostsApi.COMMENTS_SCHEMA)
    assert all(comment["postId"] == 1 for comment in body)


def test_created_post_gets_new_collection_id(
    posts_api: PostsApi, post_payload: dict[str, Any]
) -> None:
    """POST assigns an id beyond the seeded collection (write is simulated)."""
    response = posts_api.create(post_payload)
    assert_status(response, 201)
    assert response.json()["id"] > 100


def test_full_update_echoes_replacement(posts_api: PostsApi, post_payload: dict[str, Any]) -> None:
    """PUT /posts/1 answers 200 and echoes the replacement fields."""
    response = posts_api.update(1, post_payload)
    assert_status(response, 200)
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == post_payload["title"]
    assert body["body"] == post_payload["body"]


def test_partial_update_merges_fields(posts_api: PostsApi) -> None:
    """PATCH /posts/1 with only a title keeps the original body."""
    original = posts_api.get(1).json()
    response = posts_api.partial_update(1, {"title": "Patched Title"})
    assert_status(response, 200)
    body = response.json()
    assert_matches_schema(body, PostsApi.ITEM_SCHEMA)
    assert body["title"] == "Patched Title"
    assert body["body"] == original["body"]


def test_delete_post_is_accepted(posts_api: PostsApi) -> None:
    """DELETE /posts/1 answers 200 (simulated deletion)."""
    assert_status(posts_api.delete(1), 200)


def test_get_unknown_post_returns_404(posts_api: PostsApi) -> None:
    """A non-existent id is a clean 404, not a 200 with an empty body."""
    assert_status(posts_api.get(9999), 404)
