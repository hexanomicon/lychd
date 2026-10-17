"""Actual local authentication, Origin/CSRF and raw-body refusal at the API."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State

from lychd.compositions.creation.schemas import CaseView, ContinueRequest, CreationRefused, canonical, decode, digest
from lychd.compositions.creation.services import LocalCreationPolicy
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.interface.api.creation import CreationController
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.support.creation import capability
from tests.unit.compositions.test_creation import StageStore, stage_fixture
from tests.web.conftest import TEST_ACCESS_PASSWORD, TEST_AUTHORIZATION

CSRF_VALUE = "inert-creation-csrf-secret"


class HTTPStore(StageStore):
    async def cancel(self, _case_id: UUID) -> tuple[str, ...]:
        self.events.append("cancel")
        self.cancelled = True
        assert self.view is not None
        self.view = self.view.model_copy(update={"status": "cancelled", "slot_encumbered": False})
        return tuple(a["run_id"] for a in self.view.admissions if a["run_id"])

    async def read(self, case_id: UUID) -> CaseView:
        assert self.view is not None
        if self.view.case_id != case_id:
            code = "unknown_case"
            raise CreationRefused(code)
        return self.view


def api() -> tuple[Litestar, Any, LocalOperatorAccess]:
    store = HTTPStore()
    service, _common = stage_fixture(store)
    access = LocalOperatorAccess(access_password=TEST_ACCESS_PASSWORD)
    service.policy = LocalCreationPolicy(access)
    assert store.view is not None
    admission = {"admission_id": str(store.view.case_id), "run_id": str(uuid4())}
    store.view = store.view.model_copy(update={"admissions": (admission,)})
    services = SimpleNamespace(creation=service, run_engine=None, bridge_sessions=None)
    app = Litestar(
        route_handlers=[CreationController],
        state=State({"services": services}),
        middleware=[sigil_auth_middleware(operator_access=access)],
        csrf_config=CSRFConfig(secret=CSRF_VALUE, cookie_name="creation-csrf", header_name="x-creation-csrf"),
        plugins=[StrictPydanticSchemaPlugin()],
        openapi_config=build_openapi_config(title="Creation test", version="1", use_handler_docstrings=False),
    )
    return app, store, access


@pytest.mark.asyncio
async def test_creation_http_requires_credentials_origin_csrf_and_current_role() -> None:
    app, store, access = api()
    view = cast("CaseView", store.view)
    route = f"/api/v1/creation/investigations/{view.case_id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)), base_url="http://testserver.local"
    ) as client:
        assert (await client.get(route)).status_code == 401
        client.headers["authorization"] = TEST_AUTHORIZATION
        assert (await client.get(route)).status_code == 200
        body = canonical(view.request)
        assert (
            await client.post(
                "/api/v1/creation/investigations", content=body, headers={"content-type": "application/json"}
            )
        ).status_code == 403
        client.headers["x-creation-csrf"] = client.cookies["creation-csrf"]
        foreign = await client.post(
            "/api/v1/creation/investigations",
            content=body,
            headers={"content-type": "application/json", "origin": "https://foreign.invalid"},
        )
        assert foreign.status_code == 403
        replay = await client.post(
            "/api/v1/creation/investigations", content=body, headers={"content-type": "application/json"}
        )
        assert replay.status_code == 200, replay.text
        duplicated = body[:-1] + b',"question":"changed"}'
        refused = await client.post(
            "/api/v1/creation/investigations", content=duplicated, headers={"content-type": "application/json"}
        )
        assert refused.status_code == 409
        assert store.events == []
        access.revoke()
        assert (await client.get(route)).status_code == 401


def test_openapi_has_typed_submit_and_continuation_bodies() -> None:
    app, _store, _access = api()
    schema = app.openapi_schema.to_schema()
    submit = schema["paths"]["/api/v1/creation/investigations"]["post"]
    continuation = schema["paths"]["/api/v1/creation/investigations/{case_id}/continue"]["post"]
    assert "InvestigationRequest" in str(submit["requestBody"])
    assert "ContinueRequest" in str(continuation["requestBody"])
    assert schema["components"]["schemas"]["InvestigationRequest"]["additionalProperties"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["submit", "cancel", "continue"])
async def test_retired_profile_one_is_readable_but_all_writes_refuse_without_effects(action: str) -> None:
    app, store, _access = api()
    view = cast("CaseView", store.view)
    historical = decode(canonical(view.profile))
    historical.update(revision="1", profile="public-source-qwen@1", output_tokens=256)
    historical["capability"]["generation_profile"]["max_tokens"] = 256
    historical["pattern"].update(
        revision="1",
        implementation_revision="py.1",
        digest="b0662ed5b7eca305558ed27c964cea54f9c205ffaab53d41fb272d7fcd330fdc",
    )
    store.view = view.model_copy(
        update={
            "profile": historical,
            "profile_digest": digest(canonical(historical)),
            "status": "incomplete",
            "reason": "output_length",
            "slot_encumbered": False,
        }
    )
    before = canonical(store.view)
    engine = SimpleNamespace(submit=AsyncMock(), cancel=AsyncMock())
    sessions = SimpleNamespace(create_session=AsyncMock())
    app.state.services.run_engine, app.state.services.bridge_sessions = engine, sessions
    route = f"/api/v1/creation/investigations/{view.case_id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)), base_url="http://testserver.local"
    ) as client:
        client.headers["authorization"] = TEST_AUTHORIZATION
        read = await client.get(route)
        assert read.status_code == 200
        assert canonical(read.json()) == before
        client.headers["x-creation-csrf"] = client.cookies["creation-csrf"]
        continuation = ContinueRequest(
            admission_id=uuid4(),
            request_digest=view.request_digest,
            candidate_digest="a" * 64,
            profile_digest=store.view.profile_digest,
        )
        path, body, code = {
            "submit": ("/api/v1/creation/investigations", canonical(view.request), "conflicting_replay"),
            "cancel": (f"{route}/cancel", b"", "profile_changed"),
            "continue": (f"{route}/continue", canonical(continuation), "profile_changed"),
        }[action]
        response = await client.post(path, content=body, headers={"content-type": "application/json"})
        assert response.status_code == 409, response.text
        assert response.json()["extra"]["code"] == code
        assert canonical((await client.get(route)).json()) == before
    assert canonical(store.view) == before
    assert store.events == []
    assert not store.cancelled
    engine.submit.assert_not_awaited()
    engine.cancel.assert_not_awaited()
    sessions.create_session.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["missing", "changed"])
async def test_current_profile_cancel_fences_without_live_capability_admission(binding: str) -> None:
    app, store, _access = api()
    view = cast("CaseView", store.view)
    previous = capability()
    changed = previous.model_copy(
        update={"generation_profile": previous.generation_profile.model_copy(update={"max_tokens": 256})}
    )
    registry = SimpleNamespace(
        get_capability=Mock(return_value=None if binding == "missing" else changed),
        refresh_capability_state=AsyncMock(),
    )
    service = app.state.services.creation
    service.registry = registry
    engine = SimpleNamespace(submit=AsyncMock(), cancel=AsyncMock())
    sessions = SimpleNamespace(create_session=AsyncMock())
    app.state.services.run_engine, app.state.services.bridge_sessions = engine, sessions

    async def cancel_run(_run_id: str) -> None:
        assert store.cancelled
        assert store.events == ["cancel"]

    engine.cancel.side_effect = cancel_run
    route = f"/api/v1/creation/investigations/{view.case_id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", app)), base_url="http://testserver.local"
    ) as client:
        client.headers["authorization"] = TEST_AUTHORIZATION
        assert (await client.get(route)).status_code == 200
        client.headers["x-creation-csrf"] = client.cookies["creation-csrf"]
        response = await client.post(f"{route}/cancel")
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "cancelled"
    assert store.events == ["cancel"]
    assert store.cancelled
    engine.cancel.assert_awaited_once_with(view.admissions[0]["run_id"])
    engine.submit.assert_not_awaited()
    sessions.create_session.assert_not_awaited()
    registry.get_capability.assert_not_called()
    registry.refresh_capability_state.assert_not_awaited()
