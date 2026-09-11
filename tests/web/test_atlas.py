"""Atlas HTTP admission, owner boundaries, replay, and execution separation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State

from lychd.domain.codex import middleware as identity
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.codex.sigil import Sigil
from lychd.interface.web import AltarController, AtlasController
from lychd.interface.web.deps import web_dependencies
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION, AsgiClient

if TYPE_CHECKING:
    from types import SimpleNamespace

    import pytest


def _create(client: AsgiClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/atlas/projects",
        json={"id": str(uuid4()), "title": "The record", "brief": "Preserve the original sound."},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _change(project: dict[str, Any], **change: Any) -> dict[str, Any]:
    return {"request_id": str(uuid4()), "expected_version": project["version"], "change": change}


def test_project_is_useful_without_a_conversation_or_run(
    altar_client: AsgiClient, fake_services: SimpleNamespace
) -> None:
    project = _create(altar_client)
    assert project["concerns"] == project["references"] == project["assessments"] == []
    assert fake_services.run_engine.submitted == []
    assert altar_client.get("/api/v1/bridge").json()["sessions"] == []
    assert altar_client.get(f"/api/v1/atlas/projects/{project['id']}").json() == project
    catalogue = altar_client.get("/api/v1/atlas/projects?limit=1&offset=0").json()
    assert catalogue["total"] == 1
    assert catalogue["projects"][0]["id"] == project["id"]
    assert catalogue["projects"][0]["unassessed_count"] == 0


def test_http_conflicts_preserve_saved_work_and_retry_returns_latest(altar_client: AsgiClient) -> None:
    project = _create(altar_client)
    url = f"/api/v1/atlas/projects/{project['id']}/changes"
    first = _change(
        project, kind="concern.save", concern_id=None, statement="Keep dynamics", criteria="Compare the master"
    )
    saved = altar_client.post(url, json=first)
    assert saved.status_code == 200
    stale = altar_client.post(url, json={**first, "request_id": str(uuid4())})
    assert stale.status_code == 409
    assert stale.json()["extra"] == {"code": "atlas_write_rejected"}
    later = altar_client.post(
        url,
        json=_change(
            saved.json(),
            kind="project.update",
            title=project["title"],
            brief=project["brief"],
            next_action="Listen together",
            lifecycle="paused",
        ),
    )
    assert later.status_code == 200
    replay = altar_client.post(url, json=first)
    assert replay.json() == later.json()
    assert len(replay.json()["concerns"]) == 1
    assert replay.json()["assessments"] == []


def test_linked_activity_has_a_backlink_and_does_not_inject_context(
    altar_client: AsgiClient,
    fake_services: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _create(altar_client)
    session = altar_client.post("/api/v1/bridge/sessions").json()["session"]
    url = f"/api/v1/atlas/projects/{project['id']}/changes"
    body = _change(
        project,
        kind="reference.add",
        reference_kind="session",
        target_id=session["id"],
        concern_id=None,
        note="Mix review",
    )
    saved = altar_client.post(url, json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["assessments"] == []
    linked = altar_client.get(f"/api/v1/atlas/references?kind=session&target_id={session['id']}").json()
    assert [entry["id"] for entry in linked] == [project["id"]]
    assert altar_client.get(f"/api/v1/bridge/sessions/{session['id']}").json()["session"]["turns"] == []
    assert fake_services.run_engine.submitted == []

    async def unavailable(_session_id: str) -> None:
        return None

    monkeypatch.setattr(fake_services.bridge_sessions, "get_session", unavailable)
    replay = altar_client.post(url, json=body)
    assert replay.status_code == 200
    assert replay.json() == saved.json()
    assert altar_client.post(url, json={**body, "request_id": str(uuid4())}).status_code == 400


def test_reference_requires_an_existing_target_and_matching_owner(
    altar_client: AsgiClient,
    fake_services: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _create(altar_client)
    url = f"/api/v1/atlas/projects/{project['id']}/changes"
    body = _change(project, kind="reference.add", reference_kind="run", target_id="missing", concern_id=None, note="")
    assert altar_client.post(url, json=body).status_code == 400
    session = altar_client.post("/api/v1/bridge/sessions").json()["session"]
    original = fake_services.bridge_sessions.get_session

    async def foreign(session_id: str) -> Any:
        record = await original(session_id)
        record.sigil_name = "another-sigil"
        return record

    monkeypatch.setattr(fake_services.bridge_sessions, "get_session", foreign)
    body["change"].update(reference_kind="session", target_id=session["id"])
    assert altar_client.post(url, json=body).status_code == 400
    assert altar_client.get(f"/api/v1/atlas/projects/{project['id']}").json()["version"] == 1


def test_scoped_owner_cannot_read_change_or_reuse_foreign_project(
    altar_client: AsgiClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _create(altar_client)
    monkeypatch.setattr(identity, "default_local_sigil", lambda: Sigil(name="other", scopes=frozenset({"*"})))
    assert altar_client.get("/api/v1/atlas/projects").json()["total"] == 0
    assert altar_client.get(f"/api/v1/atlas/projects/{project['id']}").status_code == 404
    assert (
        altar_client.post("/api/v1/atlas/projects", json={"id": project["id"], "title": project["title"]}).status_code
        == 404
    )
    change = _change(project, kind="concern.save", concern_id=None, statement="Foreign", criteria="")
    assert altar_client.post(f"/api/v1/atlas/projects/{project['id']}/changes", json=change).status_code == 404


def test_read_scope_does_not_authorize_atlas_writes(altar_client: AsgiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(identity, "default_local_sigil", lambda: Sigil(name="magus", scopes=frozenset({"altar:read"})))
    assert altar_client.get("/api/v1/atlas/projects").status_code == 200
    assert altar_client.post("/api/v1/atlas/projects", json={"id": str(uuid4()), "title": "Denied"}).status_code == 403


def test_atlas_rejects_forged_attribution_and_invalid_pagination(altar_client: AsgiClient) -> None:
    response = altar_client.post(
        "/api/v1/atlas/projects", json={"id": str(uuid4()), "title": "Forged", "author": "admin"}
    )
    assert response.status_code == 400
    assert altar_client.get("/api/v1/atlas/projects?limit=101").status_code == 400
    assert altar_client.get("/api/v1/atlas/projects?offset=-1").status_code == 400
    assert altar_client.get("/api/v1/atlas/references?kind=arbitrary&target_id=x").status_code == 400


def test_atlas_mutations_use_the_vessel_csrf_boundary(fake_services: SimpleNamespace) -> None:
    client = AsgiClient(
        Litestar(
            route_handlers=[AltarController, AtlasController],
            dependencies=web_dependencies,
            middleware=[sigil_auth_middleware(access_password=TEST_ACCESS_PASSWORD)],
            csrf_config=CSRFConfig(secret=str(uuid4()), cookie_secure=False),
            state=State({"services": fake_services}),
        ),
        headers={"authorization": TEST_AUTHORIZATION},
    )
    body = {"id": str(uuid4()), "title": "Protected"}
    assert client.post("/api/v1/atlas/projects", json=body).status_code == 403
    initial = client.get("/atlas")
    token = initial.cookies["csrftoken"]
    response = client.post(
        "/api/v1/atlas/projects", json=body, headers={"cookie": f"csrftoken={token}", "x-csrftoken": token}
    )
    assert response.status_code == 201
