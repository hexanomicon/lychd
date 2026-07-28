"""Loom workflow catalogue, typed graph projection, and Mermaid source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lychd.agents.workflows import WORKFLOW_REGISTRY

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.testing import TestClient

_NAME = WORKFLOW_REGISTRY.default.name
_REVISION = WORKFLOW_REGISTRY.default.manifest.revision


def test_catalogue_lists_registered_workflow(
    altar_client: TestClient[Litestar],
) -> None:
    response = altar_client.get("/api/v1/loom")

    assert response.status_code == 200
    entry = response.json()[0]
    assert entry["pattern_id"] == _NAME
    assert entry["revision"] == _REVISION
    assert len(entry["digest"]) == 64
    assert entry["detail_path"] == f"/loom/{_NAME}/{_REVISION}"


def test_view_returns_typed_graph(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/{_NAME}")

    assert response.status_code == 200
    assert response.json()["pattern_id"] == _NAME
    assert response.json()["revision"] == _REVISION
    assert "stateDiagram-v2" in response.json()["mermaid_source"]


def test_exact_revision_returns_semantic_score(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/{_NAME}/{_REVISION}")

    assert response.status_code == 200
    body = response.json()
    assert body["publication"] == "published"
    assert {node["key"] for node in body["nodes"]} >= {"weave_context", "converse", "end"}
    assert {edge["relation"] for edge in body["edges"]} == {"permits"}


def test_source_is_plaintext_mermaid(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/{_NAME}/{_REVISION}/source")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "stateDiagram-v2" in response.text


def test_view_unknown_workflow_404(altar_client: TestClient[Litestar]) -> None:
    assert altar_client.get("/api/v1/loom/nope").status_code == 404
    assert altar_client.get(f"/api/v1/loom/{_NAME}/nope").status_code == 404
