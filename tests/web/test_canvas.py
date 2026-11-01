"""Canvas admission, memory workspace custody and real OpenAPI schema exposure."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State

from lychd.compositions.canvas.workspace import lychd_project_id
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil
from lychd.interface.web.atlas import AtlasController
from lychd.interface.web.canvas import CanvasController
from lychd.interface.web.deps import web_dependencies
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.web.conftest import AsgiClient

if TYPE_CHECKING:
    from types import SimpleNamespace

_PASSWORD = "canvas-synthetic-test-password-0123456789"  # noqa: S105
_AUTHORIZATION = "Basic " + base64.b64encode(f"magus:{_PASSWORD}".encode()).decode("ascii")


@pytest.fixture
def canvas_client(fake_services: SimpleNamespace) -> AsgiClient:
    app = Litestar(
        route_handlers=[CanvasController, AtlasController],
        dependencies=web_dependencies,
        state=State({"services": fake_services}),
        middleware=[sigil_auth_middleware(access_password=_PASSWORD)],
        csrf_config=CSRFConfig(secret=str(uuid4()), cookie_secure=False),
        plugins=[StrictPydanticSchemaPlugin()],
        openapi_config=build_openapi_config(
            title="Canvas isolated contract", version="test", use_handler_docstrings=True
        ),
    )
    client = AsgiClient(app, headers={"authorization": _AUTHORIZATION})
    token = client.get("/api/v1/canvas/contracts").cookies["csrftoken"]
    client.headers.update({"cookie": f"csrftoken={token}", "x-csrftoken": token})
    return client


def _request() -> dict[str, Any]:
    scene_id, node_id = str(uuid4()), str(uuid4())
    node: dict[str, Any] = {
        "id": node_id,
        "x": 0,
        "y": 0,
        "width": 120,
        "height": 60,
        "label": "Original",
        "kind": "box",
        "pinned": False,
        "source_stroke_ids": [],
        "artwork": None,
    }
    return {
        "packet": {
            "format": "lychd.canvas.selection/1",
            "scene": {
                "format": "lychd.canvas/1",
                "id": scene_id,
                "revision": 1,
                "title": "Example",
                "strokes": [],
                "nodes": [node],
                "edges": [],
            },
            "selection": {
                "scene_id": scene_id,
                "revision": 1,
                "object_ids": [node_id],
                "bounds": {"x": 0, "y": 0, "width": 120, "height": 60},
            },
            "instruction": "Rename this node.",
            "crop": None,
        },
        "proposal": {
            "format": "lychd.canvas.proposal/1",
            "id": str(uuid4()),
            "scene_id": scene_id,
            "base_revision": 1,
            "selection_ids": [node_id],
            "author": "Explicit test fixture",
            "summary": "Rename the selected node.",
            "nodes": [{**node, "label": "Reviewed"}],
            "edges": [],
            "archive_stroke_ids": [],
        },
    }


def test_canvas_requires_authentication(canvas_client: AsgiClient) -> None:
    response = canvas_client.get("/api/v1/canvas/contracts", headers={"authorization": ""})
    assert response.status_code == 401


def test_canvas_descriptor_admits_retention_and_disclaims_provider_execution(canvas_client: AsgiClient) -> None:
    response = canvas_client.get("/api/v1/canvas/contracts")
    assert response.status_code == 200
    body = response.json()
    assert body["composition"] == "canvas.board"
    assert body["server_retention"] is True
    assert body["revision"] == 2
    assert body["model_transmission"] is False
    assert body["image_generation"] is False


def test_review_returns_one_successor_and_retains_no_state(canvas_client: AsgiClient) -> None:
    request = _request()
    first = canvas_client.post("/api/v1/canvas/review", json=request)
    second = canvas_client.post("/api/v1/canvas/review", json=request)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["scene"]["revision"] == 2
    assert first.json()["scene"]["nodes"][0]["label"] == "Reviewed"
    assert request["packet"]["scene"]["nodes"][0]["label"] == "Original"


def test_review_refuses_stale_and_outside_selection_updates(canvas_client: AsgiClient) -> None:
    request = _request()
    request["proposal"]["base_revision"] = 2
    assert canvas_client.post("/api/v1/canvas/review", json=request).status_code == 400
    request = _request()
    existing = {**request["packet"]["scene"]["nodes"][0], "id": str(uuid4()), "label": "Context"}
    request["packet"]["scene"]["nodes"].append(existing)
    request["proposal"]["nodes"] = [{**existing, "label": "Unauthorized"}]
    assert canvas_client.post("/api/v1/canvas/review", json=request).status_code == 400


def test_document_identity_validation_and_malformed_import(canvas_client: AsgiClient) -> None:
    document: dict[str, Any] = {
        "format": "lychd.canvas.document/1",
        "scene": _request()["packet"]["scene"],
        "past": [],
        "future": [],
    }
    response = canvas_client.post("/api/v1/canvas/documents/validate", json=document)
    assert response.status_code == 200
    assert response.json() == document
    document["unexpected"] = True
    assert canvas_client.post("/api/v1/canvas/documents/validate", json=document).status_code == 400


def test_canvas_write_scope_is_required(canvas_client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil",
        lambda: Sigil(name="synthetic-reader", scopes=frozenset({"altar:read"})),
    )
    assert canvas_client.get("/api/v1/canvas/contracts").status_code == 200
    assert canvas_client.post("/api/v1/canvas/review", json=_request()).status_code == 403


def test_canvas_mutation_requires_csrf_in_addition_to_authenticated_scope(canvas_client: AsgiClient) -> None:
    unprotected = AsgiClient(canvas_client.app, headers={"authorization": _AUTHORIZATION})
    assert unprotected.post("/api/v1/canvas/review", json=_request()).status_code == 403
    assert canvas_client.post("/api/v1/canvas/review", json=_request()).status_code == 200
    assert (
        canvas_client.post(
            "/api/v1/canvas/review", json=_request(), headers={"origin": "https://example.invalid"}
        ).status_code
        == 403
    )


def test_canvas_schemas_are_exposed_by_real_controller_signatures(canvas_client: AsgiClient) -> None:
    response = canvas_client.get("/schema/openapi.json")
    assert response.status_code == 200
    schema = cast("dict[str, Any]", response.json())
    models = schema["components"]["schemas"]
    expected = {
        "CanvasPoint",
        "CanvasBounds",
        "CanvasStroke",
        "CanvasArtwork",
        "CanvasNode",
        "CanvasEdge",
        "CanvasScene",
        "CanvasDocument",
        "CanvasSelection",
        "CanvasCrop",
        "CanvasPacket",
        "CanvasProposal",
        "CanvasReviewRequest",
        "CanvasReviewResult",
    }
    assert expected <= models.keys()
    assert all(models[name]["additionalProperties"] is False for name in expected)
    assert "/api/v1/canvas/review" in schema["paths"]
    assert "/api/v1/canvas/documents/validate" in schema["paths"]


def _document() -> dict[str, Any]:
    return {"format": "lychd.canvas.document/1", "scene": _request()["packet"]["scene"], "past": [], "future": []}


def _mutation(project: dict[str, Any], **change: Any) -> dict[str, Any]:
    return {"request_id": str(uuid4()), "expected_version": project["version"], "change": change}


def test_workspace_bootstrap_is_explicit_owner_scoped_and_pinned_outside_pagination(
    canvas_client: AsgiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = canvas_client.get("/api/v1/atlas/projects").json()
    assert empty["total"] == 0
    assert empty["pinned"] is None
    first = canvas_client.post("/api/v1/canvas/workspace/bootstrap")
    assert first.status_code == 200, first.text
    project = first.json()
    assert project["builtin"] is True
    assert project["workspace_state"] == "kept"
    assert "static" in project["canvas_document"]["scene"]["title"]
    assert canvas_client.post("/api/v1/canvas/workspace/bootstrap").json() == project
    catalogue = canvas_client.get("/api/v1/atlas/projects?limit=1&offset=100").json()
    assert catalogue["projects"] == []
    assert catalogue["total"] == 0
    assert catalogue["pinned"]["id"] == project["id"]
    assert canvas_client.post("/api/v1/atlas/projects", json={"id": project["id"], "title": "Squat"}).status_code == 409
    assert (
        canvas_client.post(
            "/api/v1/canvas/projects", json={"id": project["id"], "canvas_document": _document()}
        ).status_code
        == 409
    )
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil", lambda: Sigil(name="other", scopes=frozenset({"*"}))
    )
    assert canvas_client.get(f"/api/v1/atlas/projects/{project['id']}").status_code == 404
    assert canvas_client.get("/api/v1/atlas/projects").json()["pinned"] is None
    other = canvas_client.post("/api/v1/canvas/workspace/bootstrap").json()
    assert other["id"] != project["id"]


def test_workspace_create_save_discard_and_retries_return_retained_tombstone(canvas_client: AsgiClient) -> None:
    creation: dict[str, Any] = {"id": str(uuid4()), "canvas_document": _document()}
    created = canvas_client.post("/api/v1/canvas/projects", json=creation)
    assert created.status_code == 201, created.text
    project = created.json()
    assert project["workspace_state"] == "draft"
    assert project["builtin"] is False
    assert canvas_client.post("/api/v1/canvas/projects", json=creation).json() == project
    url = f"/api/v1/atlas/projects/{project['id']}/changes"
    revised = _document()
    revised["scene"]["id"] = creation["canvas_document"]["scene"]["id"]
    revised["scene"]["revision"] = 2
    save = _mutation(project, kind="canvas.save", canvas_document=revised)
    saved = canvas_client.post(url, json=save)
    assert saved.status_code == 200, saved.text
    stale = canvas_client.post(url, json={**save, "request_id": str(uuid4())})
    assert stale.status_code == 409
    assert stale.json()["extra"] == {"code": "atlas_write_rejected"}
    discard = _mutation(saved.json(), kind="project.discard")
    tombstone = canvas_client.post(url, json=discard)
    assert tombstone.status_code == 200
    assert tombstone.json()["workspace_state"] == "discarded"
    assert canvas_client.get("/api/v1/atlas/projects").json()["total"] == 0
    assert canvas_client.post(url, json=save).json() == tombstone.json()
    assert canvas_client.post(url, json=discard).json() == tombstone.json()
    assert canvas_client.post("/api/v1/canvas/projects", json=creation).json() == tombstone.json()
    rejected = canvas_client.post(url, json=_mutation(tombstone.json(), kind="project.keep"))
    assert rejected.status_code == 409
    assert rejected.json()["extra"] == {"code": "atlas_write_rejected"}


def test_foreign_sigil_cannot_squat_a_reserved_builtin_identity_before_bootstrap(
    canvas_client: AsgiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    victim_id = str(lychd_project_id("magus"))
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil", lambda: Sigil(name="other", scopes=frozenset({"*"}))
    )
    assert (
        canvas_client.post(
            "/api/v1/atlas/projects", json={"id": victim_id, "title": "Squat a foreign bootstrap"}
        ).status_code
        == 409
    )
    assert (
        canvas_client.post(
            "/api/v1/canvas/projects", json={"id": victim_id, "canvas_document": _document()}
        ).status_code
        == 409
    )
    assert canvas_client.get("/api/v1/atlas/projects").json()["total"] == 0
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil", lambda: Sigil(name="magus", scopes=frozenset({"*"}))
    )
    response = canvas_client.post("/api/v1/canvas/workspace/bootstrap")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == victim_id
    assert response.json()["builtin"] is True


@pytest.mark.parametrize("scopes", [{"altar:read", "canvas:write"}, {"altar:read", "atlas:write"}])
def test_workspace_writes_require_both_scopes_even_on_atlas_endpoint(
    canvas_client: AsgiClient, monkeypatch: pytest.MonkeyPatch, scopes: set[str]
) -> None:
    creation = {"id": str(uuid4()), "canvas_document": _document()}
    project = canvas_client.post("/api/v1/canvas/projects", json=creation).json()
    monkeypatch.setattr(
        "lychd.domain.codex.middleware.default_local_sigil", lambda: Sigil(name="magus", scopes=frozenset(scopes))
    )
    assert canvas_client.post("/api/v1/canvas/projects", json=creation).status_code == 403
    assert canvas_client.post("/api/v1/canvas/workspace/bootstrap").status_code == 403
    url = f"/api/v1/atlas/projects/{project['id']}/changes"
    for change in (
        {"kind": "canvas.save", "canvas_document": creation["canvas_document"]},
        {"kind": "project.keep"},
        {"kind": "project.discard"},
    ):
        assert canvas_client.post(url, json=_mutation(project, **change)).status_code == 403
    assert canvas_client.get(f"/api/v1/atlas/projects/{project['id']}").json()["version"] == 1


def test_workspace_creation_refuses_client_privilege_injection_and_uses_csrf(canvas_client: AsgiClient) -> None:
    body = {"id": str(uuid4()), "canvas_document": _document()}
    for extra in ({"builtin": True}, {"workspace_state": "kept"}):
        assert canvas_client.post("/api/v1/canvas/projects", json={**body, **extra}).status_code == 400
    unprotected = AsgiClient(canvas_client.app, headers={"authorization": _AUTHORIZATION})
    assert unprotected.post("/api/v1/canvas/projects", json=body).status_code == 403
    assert unprotected.post("/api/v1/canvas/workspace/bootstrap").status_code == 403


def test_bootstrap_preserves_user_edits_without_rebuilding_a_later_seed(
    canvas_client: AsgiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = canvas_client.post("/api/v1/canvas/workspace/bootstrap").json()
    board = project["canvas_document"]
    board["scene"]["revision"] += 1
    board["scene"]["nodes"][0]["label"] = "Authored by the operator"
    saved = canvas_client.post(
        f"/api/v1/atlas/projects/{project['id']}/changes",
        json=_mutation(project, kind="canvas.save", canvas_document=board),
    )
    assert saved.status_code == 200, saved.text

    def unavailable_seed(_owner: str) -> None:
        pytest.fail("An existing workspace must not rebuild a newer curated seed.")

    monkeypatch.setattr("lychd.interface.web.canvas.lychd_workspace_document", unavailable_seed)
    assert canvas_client.post("/api/v1/canvas/workspace/bootstrap").json() == saved.json()
