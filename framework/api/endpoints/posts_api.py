"""Endpoint layer for JSONPlaceholder's ``/posts`` resource.

EXTENSION POINT — OpenAPI-driven schemas: each method advertises the name of
the hand-authored JSON schema (``framework/api/schemas/<name>.schema.json``)
that validates its response. To switch to schemas generated from an OpenAPI
spec, regenerate those files at build time and keep the names stable — the
endpoint classes and every test stay untouched.
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import APIResponse

from framework.api.clients.base_api_client import BaseApiClient


class PostsApi:
    """Typed access to the ``/posts`` resource and its nested comments."""

    LIST_SCHEMA = "post_list"
    ITEM_SCHEMA = "post"
    CREATED_SCHEMA = "post_created"
    COMMENTS_SCHEMA = "comment_list"

    def __init__(self, client: BaseApiClient) -> None:
        self._client = client

    def list_all(self) -> APIResponse:
        """GET /posts — the full post collection."""
        return self._client.get("/posts")

    def list_by_user(self, user_id: int) -> APIResponse:
        """GET /posts?userId=n — posts authored by one user."""
        return self._client.get("/posts", params={"userId": user_id})

    def get(self, post_id: int) -> APIResponse:
        """GET /posts/{id} — a single post."""
        return self._client.get(f"/posts/{post_id}")

    def comments_for(self, post_id: int) -> APIResponse:
        """GET /posts/{id}/comments — nested comment collection."""
        return self._client.get(f"/posts/{post_id}/comments")

    def create(self, payload: dict[str, Any]) -> APIResponse:
        """POST /posts — create a post."""
        return self._client.post("/posts", payload)

    def update(self, post_id: int, payload: dict[str, Any]) -> APIResponse:
        """PUT /posts/{id} — full replacement."""
        return self._client.put(f"/posts/{post_id}", payload)

    def partial_update(self, post_id: int, payload: dict[str, Any]) -> APIResponse:
        """PATCH /posts/{id} — update only the provided fields."""
        return self._client.patch(f"/posts/{post_id}", payload)

    def delete(self, post_id: int) -> APIResponse:
        """DELETE /posts/{id}."""
        return self._client.delete(f"/posts/{post_id}")
