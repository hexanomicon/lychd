"""Static Svelte shell routing and API/fallback separation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient


@pytest.mark.parametrize(
    "path",
    ["/bridge", "/nexus", "/loom", "/orb"],
)
def test_pages_return_compiled_svelte_shell(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    response = altar_client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/_app/immutable/" in response.text


def test_root_redirects_to_bridge(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/bridge"


def test_altar_status_publishes_the_vessel_csrf_names(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/altar/status")

    assert response.status_code == 200
    assert response.json()["csrf"] == {
        "cookie_name": "csrftoken",
        "header_name": "x-csrftoken",
    }


@pytest.mark.parametrize(
    "path",
    ["/bridge/session-x", "/loom/pattern-x/revision-1", "/orb/run-x"],
)
def test_deep_links_return_same_static_shell(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    shell = altar_client.get("/bridge")
    deep = altar_client.get(path)

    assert deep.status_code == 200
    assert deep.content == shell.content


def test_unknown_api_is_not_swallowed_by_spa_fallback(
    altar_client: TestClient[Litestar],
) -> None:
    assert altar_client.get("/api/v1/not-real").status_code == 404


@pytest.mark.parametrize(
    "path",
    ["/reliquary", "/bindings", "/scrying", "/scrying/run-x", "/loom/unversioned"],
)
def test_retired_or_ambiguous_pages_are_not_routes(
    altar_client: TestClient[Litestar],
    path: str,
) -> None:
    assert altar_client.get(path).status_code == 404
