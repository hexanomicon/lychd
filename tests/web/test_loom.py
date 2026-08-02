"""Loom workflow catalogue, typed graph projection, and Mermaid source."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any, cast

from lychd.agents.workflows import BRIDGE_CHAT, DELEGATED_RITE, WORKFLOW_REGISTRY, BuiltinWorkflowRegistry

if TYPE_CHECKING:
    from types import SimpleNamespace

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
    assert entry["implementation_revision"] == "py.1"
    assert entry["entry_node"] == "weave_context"
    assert len(entry["digest"]) == 64
    assert entry["detail_path"] == f"/loom/{_NAME}/{_REVISION}"
    assert entry["active"] is True
    assert entry["default"] is True
    assert entry["route_rank"] is None


def test_catalogue_reads_the_boot_composed_registry(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    fake_services.workflows = BuiltinWorkflowRegistry(workflows=(DELEGATED_RITE,))

    response = altar_client.get("/api/v1/loom")

    assert response.status_code == 200
    assert [entry["pattern_id"] for entry in response.json()] == [DELEGATED_RITE.manifest.key]


def test_catalogue_names_retained_non_routable_revision(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    fake_services.workflows = BuiltinWorkflowRegistry(
        workflows=(DELEGATED_RITE, BRIDGE_CHAT),
        active_revisions=((BRIDGE_CHAT.name, BRIDGE_CHAT.manifest.revision),),
        default_name=BRIDGE_CHAT.name,
    )

    response = altar_client.get("/api/v1/loom")

    assert response.status_code == 200
    retained, active = response.json()
    assert (retained["active"], retained["default"], retained["route_rank"]) == (False, False, None)
    assert (active["active"], active["default"], active["route_rank"]) == (True, True, None)


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
    assert body["implementation_revision"] == "py.1"
    assert body["entry_node"] == "weave_context"
    assert {node["key"] for node in body["nodes"]} >= {"weave_context", "converse", "end"}
    assert {edge["relation"] for edge in body["edges"]} == {"permits"}


def test_source_is_plaintext_mermaid(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(f"/api/v1/loom/source/patterns/{_NAME}/{_REVISION}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "stateDiagram-v2" in response.text


def test_source_openapi_contract_is_plaintext(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/schema/openapi.json")
    assert response.status_code == 200
    schema = cast("dict[str, Any]", response.json())

    for path in (
        "/api/v1/loom/source/workflows/{workflow}",
        "/api/v1/loom/source/patterns/{pattern_id}/{revision}",
    ):
        content = cast("dict[str, Any]", schema["paths"][path]["get"]["responses"]["200"]["content"])
        assert set(content) == {"text/plain"}


def test_source_namespace_preserves_a_revision_named_source(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    source_revision = replace(
        BRIDGE_CHAT,
        manifest=replace(BRIDGE_CHAT.manifest, revision="source"),
    )
    fake_services.workflows = BuiltinWorkflowRegistry(workflows=(source_revision,))

    exact = altar_client.get(f"/api/v1/loom/{_NAME}/source")
    source = altar_client.get(f"/api/v1/loom/source/patterns/{_NAME}/source")

    assert exact.status_code == 200
    assert exact.headers["content-type"].startswith("application/json")
    assert exact.json()["revision"] == "source"
    assert source.status_code == 200
    assert source.headers["content-type"].startswith("text/plain")


def test_view_unknown_workflow_404(altar_client: TestClient[Litestar]) -> None:
    assert altar_client.get("/api/v1/loom/nope").status_code == 404
    assert altar_client.get(f"/api/v1/loom/{_NAME}/nope").status_code == 404
