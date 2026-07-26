"""Loom workflow catalogue, typed graph projection, and Mermaid source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.agents.workflows import WORKFLOW_REGISTRY

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient

_NAME = WORKFLOW_REGISTRY.default.name


def test_catalogue_lists_registered_workflow(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/loom")

    assert response.status_code == 200
    assert _NAME in {item["name"] for item in response.json()}


def test_view_returns_typed_graph(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/{_NAME}")

    assert response.status_code == 200
    assert response.json()["name"] == _NAME
    assert "stateDiagram-v2" in response.json()["mermaid_source"]


def test_source_is_plaintext_mermaid(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/{_NAME}/source")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "stateDiagram-v2" in response.text


def test_view_unknown_workflow_404(altar_client: TestClient[Litestar]) -> None:
    assert altar_client.get("/api/v1/loom/nope").status_code == 404
