"""Full-page surface tests: 200s, shell markers, dual-render, redirects."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient

_HX = {"HX-Request": "true"}


@pytest.mark.parametrize("path", ["/bridge", "/nexus", "/loom", "/scrying", "/reliquary", "/bindings"])
def test_pages_render(altar_client: TestClient[Litestar], path: str) -> None:
    """Every full page renders 200 within the shell (#altar-main present)."""
    response = altar_client.get(path)
    assert response.status_code == 200
    assert 'id="altar-main"' in response.text
    assert "<html" in response.text


def test_root_redirects_to_bridge(altar_client: TestClient[Litestar]) -> None:
    """The bare root 302-redirects to the Bridge."""
    response = altar_client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/bridge"


@pytest.mark.parametrize("slug", ["scrying", "reliquary", "bindings"])
def test_skeletons_are_unbuilt(altar_client: TestClient[Litestar], slug: str) -> None:
    """Unbuilt instruments carry the honest data-state=\"unbuilt\" placeholder."""
    response = altar_client.get(f"/{slug}")
    assert response.status_code == 200
    assert 'data-state="unbuilt"' in response.text


def test_board_dual_render(altar_client: TestClient[Litestar]) -> None:
    """GET /nexus/board returns the full page on direct nav, a fragment under HTMX."""
    full = altar_client.get("/nexus/board")
    assert full.status_code == 200
    assert "<html" in full.text

    fragment = altar_client.get("/nexus/board", headers=_HX)
    assert fragment.status_code == 200
    assert "<html" not in fragment.text
    assert 'data-fragment="nexus.board"' in fragment.text


def test_nav_uses_reversed_paths(altar_client: TestClient[Litestar]) -> None:
    """The instrument nav renders reversed routes (no hardcoded literals lost)."""
    response = altar_client.get("/bridge")
    assert 'href="/nexus"' in response.text
    assert 'href="/loom"' in response.text
