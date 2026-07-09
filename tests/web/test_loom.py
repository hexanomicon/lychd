"""Loom: dual-render graph view, mermaid source surface, unknown workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.agents.workflows import WORKFLOW_REGISTRY

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient

_HX = {"HX-Request": "true"}
_NAME = WORKFLOW_REGISTRY.default.name


def test_view_htmx_returns_fragment_with_push_url(altar_client: TestClient[Litestar]) -> None:
    """The HTMX graph view returns a fragment and pushes the honest URL."""
    response = altar_client.get(f"/loom/{_NAME}", headers=_HX)
    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'data-fragment="loom.graph"' in response.text
    assert response.headers["hx-push-url"] == f"/loom/{_NAME}"


def test_view_direct_nav_returns_full_page(altar_client: TestClient[Litestar]) -> None:
    """Direct navigation to a workflow renders the full Loom page."""
    response = altar_client.get(f"/loom/{_NAME}")
    assert response.status_code == 200
    assert "<html" in response.text


def test_source_is_plaintext_mermaid(altar_client: TestClient[Litestar]) -> None:
    """The source surface returns text/plain mermaid stateDiagram-v2."""
    response = altar_client.get(f"/loom/{_NAME}/source")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "stateDiagram-v2" in response.text


def test_view_unknown_workflow_404(altar_client: TestClient[Litestar]) -> None:
    """An unknown pattern is 404."""
    assert altar_client.get("/loom/nope", headers=_HX).status_code == 404
