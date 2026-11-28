"""Actual HTTP credential/Origin/CSRF/typed-body gates with process-only app custody."""

from __future__ import annotations

import asyncio
import json
from base64 import b64encode
from collections.abc import Callable
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest
from litestar import Litestar, get
from litestar.config.csrf import CSRFConfig
from litestar.datastructures import State
from litestar.plugins.structlog import StructlogPlugin

from lychd.compositions.scavenger.schemas import (
    REQUEST_BYTES,
    CampaignSeed,
    DeleteObservationRequest,
    LiteralFilter,
    MarketObservation,
    ObservationAdmission,
    ObserveMarketRequest,
    ScavengerRefused,
    canonical,
)
from lychd.compositions.scavenger.services import LocalScavengerPolicy, ScavengerService
from lychd.config.logging import build_log_config
from lychd.config.settings import Settings
from lychd.db.scavenger import DbScavengerStore, RetainedObservation
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.codex.middleware import sigil_auth_middleware
from lychd.domain.cortex.runs import RunStatus
from lychd.domain.scout.attempts import SCOUT_FEED_URL
from lychd.interface.api.scavenger import ScavengerController
from lychd.interface.web.openapi import StrictPydanticSchemaPlugin, build_openapi_config
from tests.unit.compositions.test_scavenger_values import observation_document, seed_document
from tests.webcrawler_feed_fixtures import Scenario, scenario

CSRF_VALUE = "synthetic-scavenger-csrf"
AUTHORIZATION = "Basic " + b64encode(b"magus:synthetic-feed-coordinator-credential").decode()


class HTTPStore:
    """An attributed field substitute, never SQL/atomicity/retention evidence."""

    def __init__(self, row: RetainedObservation, access: LocalOperatorAccess) -> None:
        self.row, self.access = row, access
        self.reads = 0
        self.deletes = 0
        self.revoke_after_wait = False

    async def read(self, *, admission_id: UUID, owner: str, authorize: Callable[[], None]) -> RetainedObservation:
        authorize()
        await asyncio.sleep(0)
        if self.revoke_after_wait:
            self.access.revoke()
        authorize()
        if admission_id != self.row.admission_id or owner != "magus":
            reason = "application_unavailable"
            raise ScavengerRefused(reason)
        self.reads += 1
        return self.row

    async def active(self, *, owner: str, authorize: Callable[[], None]) -> RetainedObservation | None:
        row = await self.read(admission_id=self.row.admission_id, owner=owner, authorize=authorize)
        return row if row.status != "deleted" else None

    async def delete(
        self,
        *,
        admission_id: UUID,
        owner: str,
        request_digest: str,
        observation_digest: str | None,
        authorize: Callable[[], None],
    ) -> None:
        row = await self.read(admission_id=admission_id, owner=owner, authorize=authorize)
        if (row.request_digest, row.observation_digest) != (request_digest, observation_digest):
            reason = "delete_identity"
            raise ScavengerRefused(reason)
        if row.terminal_disposition != "terminal":
            reason = "terminal_disposition_required"
            raise ScavengerRefused(reason)
        authorize()
        self.row = replace(
            row,
            status="deleted",
            seed=None,
            initial_filter=None,
            observation=None,
            run_status=None,
            acquisition_status=None,
        )
        self.deletes += 1


@dataclass
class API:
    app: Litestar
    source: Scenario
    service: ScavengerService
    store: HTTPStore


async def api(*, body_logging: bool = False) -> API:
    source = await scenario()
    seed = CampaignSeed.model_validate(seed_document() | {"need": "PRIVATE-SEED-HTTP-SENTINEL"})
    document = observation_document()
    document.update(
        observation_id=document["admission_id"],
        seed_digest=seed.digest,
        requested_url=SCOUT_FEED_URL,
        contacted_url=SCOUT_FEED_URL,
    )
    observation = MarketObservation.model_validate(document)
    row = RetainedObservation(
        admission_id=observation.admission_id,
        request_digest="a" * 64,
        status="committed",
        run_id=observation.run_id,
        seed=seed,
        initial_filter=LiteralFilter(query=""),
        observation=observation,
        observation_digest=observation.digest,
        run_status=RunStatus.DONE,
        acquisition_status="succeeded",
        terminal_disposition="terminal",
    )
    store = HTTPStore(row, source.access)
    service = ScavengerService(
        store=cast("DbScavengerStore", store),
        policy=LocalScavengerPolicy(access=source.access, profile=source.binding.profile, owner="magus"),
        webcrawler=source.service,
    )
    plugins: list[Any] = [StrictPydanticSchemaPlugin()]
    routes: list[Any] = [ScavengerController]
    if body_logging:
        settings = Settings()
        settings.server.logging.request_fields = ["path", "body"]
        settings.server.logging.response_fields = ["status_code", "body"]
        plugins.append(StructlogPlugin(build_log_config(render_as_json=True, settings=settings)))

        @get("/logging-control")
        async def control() -> str:
            return "PUBLIC-LOG-CONTROL-VISIBLE"

        routes.append(control)
    app = Litestar(
        route_handlers=routes,
        state=State({"services": SimpleNamespace(scavenger=service, feed_admission=source.admission, run_engine=None)}),
        middleware=[sigil_auth_middleware(operator_access=source.access)],
        csrf_config=CSRFConfig(secret=CSRF_VALUE, cookie_name="scavenger-csrf", header_name="x-scavenger-csrf"),
        plugins=plugins,
        openapi_config=build_openapi_config(title="Scavenger test", version="1", use_handler_docstrings=False),
    )
    return API(app, source, service, store)


@pytest.mark.asyncio
async def test_http_field_read_and_filter_require_current_credentials_and_leave_whole_field_unchanged() -> None:
    a = await api()
    route = f"/api/v1/scavenger/observations/{a.store.row.admission_id}"
    before = canonical(cast("MarketObservation", a.store.row.observation))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)), base_url="http://testserver.local"
    ) as client:
        assert (await client.get(route)).status_code == 401
        assert a.store.reads == 0
        client.headers["authorization"] = AUTHORIZATION
        state = await client.get("/api/v1/scavenger")
        assert state.status_code == 200, state.text
        assert state.json()["current"]["status"] == "observed"
        read = await client.get(route)
        assert read.status_code == 200, read.text
        assert read.headers["cache-control"] == "no-store"
        assert read.json()["observation"]["items"][0]["title"] == "Straße GPU"
        assert read.json()["seed"]["need"] == "PRIVATE-SEED-HTTP-SENTINEL"
        headers = {"content-type": "application/json"}
        body = canonical(LiteralFilter(query="STRASSE"))
        assert (await client.post(f"{route}/view", content=body, headers=headers)).status_code == 403
        client.headers["x-scavenger-csrf"] = client.cookies["scavenger-csrf"]
        assert (
            await client.post(f"{route}/view", content=body, headers=headers | {"origin": "https://foreign.invalid"})
        ).status_code == 403
        filtered = await client.post(f"{route}/view", content=body, headers=headers)
        assert filtered.status_code == 200, filtered.text
        assert filtered.json()["visible_ordinals"] == [0]
        assert filtered.json()["unmatched_count"] == len(cast("MarketObservation", a.store.row.observation).items) - 1
        assert filtered.json()["casefold_unicode_version"]
        assert canonical(cast("MarketObservation", a.store.row.observation)) == before
        assert "PRIVATE-SEED" not in filtered.text
        a.source.access.revoke()
        assert (await client.get(route)).status_code == 401
        assert (await client.post(f"{route}/view", content=body, headers=headers)).status_code == 401


@pytest.mark.asyncio
async def test_submit_binds_typed_raw_body_and_never_reflects_seed_in_admission_receipt() -> None:
    a = await api()
    row = a.store.row
    assert row.seed is not None
    assert row.initial_filter is not None
    assert row.run_id is not None
    request = ObserveMarketRequest(request_id=row.admission_id, seed=row.seed, initial_filter=row.initial_filter)
    submit = AsyncMock(
        return_value=ObservationAdmission(admission_id=row.admission_id, run_id=row.run_id, run_status=RunStatus.QUEUED)
    )
    a.service.submit = submit
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)), base_url="http://testserver.local"
    ) as client:
        client.headers["authorization"] = AUTHORIZATION
        await client.get("/api/v1/scavenger")
        client.headers["x-scavenger-csrf"] = client.cookies["scavenger-csrf"]
        headers = {"content-type": "application/json"}
        response = await client.post("/api/v1/scavenger/observations", content=canonical(request), headers=headers)
        assert response.status_code == 200, response.text
        assert "PRIVATE-SEED" not in response.text
        assert response.json()["run_id"] == str(row.run_id)
        submit.assert_awaited_once()
        assert submit.await_args is not None
        assert submit.await_args.args == (request,)
        assert submit.await_args.kwargs["authentication"] is a.source.authentication
        duplicate = canonical(request)[:-1] + b',"request_id":"' + str(row.admission_id).encode() + b'"}'
        assert (
            await client.post("/api/v1/scavenger/observations", content=duplicate, headers=headers)
        ).status_code == 409
        oversized = canonical(request) + b" " * REQUEST_BYTES
        assert (
            await client.post("/api/v1/scavenger/observations", content=oversized, headers=headers)
        ).status_code == 413
        missing = request.model_dump(mode="json")
        missing["seed"].pop("budget_minor")
        invalid = await client.post("/api/v1/scavenger/observations", content=json.dumps(missing), headers=headers)
        assert invalid.status_code == 400
        assert "PRIVATE-SEED-HTTP-SENTINEL" not in invalid.text
        assert submit.await_count == 1


@pytest.mark.asyncio
async def test_terminal_delete_has_distinct_current_authority_and_deleted_is_not_empty_market() -> None:
    a = await api()
    row = a.store.row
    route = f"/api/v1/scavenger/observations/{row.admission_id}"
    body = canonical(
        DeleteObservationRequest(request_digest=row.request_digest, observation_digest=row.observation_digest)
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)), base_url="http://testserver.local"
    ) as client:
        client.headers["authorization"] = AUTHORIZATION
        await client.get(route)
        client.headers["x-scavenger-csrf"] = client.cookies["scavenger-csrf"]
        headers = {"content-type": "application/json"}
        a.store.row = replace(row, terminal_disposition="unknown", acquisition_status="unknown_after_crash")
        refused = await client.post(f"{route}/delete", content=body, headers=headers)
        assert refused.status_code == 409
        assert a.store.deletes == 0
        a.store.row = row
        deleted = await client.post(f"{route}/delete", content=body, headers=headers)
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["status"] == "deleted"
        after = await client.get(route)
        assert after.json()["status"] == "deleted"
        assert after.json()["observation"] is None
        assert after.json()["seed"] is None
        assert (await client.get("/api/v1/scavenger")).json()["current"] is None
        assert "PRIVATE-SEED" not in after.text


@pytest.mark.asyncio
async def test_revocation_during_read_prevents_content_response_and_disabled_state_has_no_db_read() -> None:
    a = await api()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)), base_url="http://testserver.local"
    ) as client:
        client.headers["authorization"] = AUTHORIZATION
        a.app.state.services.scavenger = None
        response = await client.get("/api/v1/scavenger")
        assert response.json() == {"configured": False, "profile": None, "current": None}
        assert a.store.reads == 0
        a.app.state.services.scavenger = a.service
        a.store.revoke_after_wait = True
        refused = await client.get(f"/api/v1/scavenger/observations/{a.store.row.admission_id}")
        assert refused.status_code == 403
        assert "Straße" not in refused.text
        assert "PRIVATE-SEED" not in refused.text


@pytest.mark.asyncio
async def test_openapi_exposes_the_actual_closed_request_and_whole_field_contracts() -> None:
    a = await api()
    schema = a.app.openapi_schema.to_schema()
    paths = schema["paths"]
    submit = paths["/api/v1/scavenger/observations"]["post"]
    assert "ObserveMarketRequest" in str(submit["requestBody"])
    definitions = schema["components"]["schemas"]
    assert definitions["ObserveMarketRequest"]["additionalProperties"] is False
    assert definitions["CampaignSeed"]["additionalProperties"] is False
    assert definitions["CampaignSeed"]["properties"]["inventory"]["items"] == {"type": "string"}
    assert definitions["CampaignSeed"]["properties"]["inventory"]["maxItems"] == 16
    assert definitions["MarketObservation"]["properties"]["items"]["items"] == {
        "$ref": "#/components/schemas/ObservationItem"
    }
    assert definitions["MarketObservation"]["properties"]["items"]["maxItems"] == 100
    assert "observation" in definitions["ObservationDocument"]["properties"]
    assert "terminal_disposition" in definitions["ObservationDocument"]["properties"]
    for path, operations in paths.items():
        if path.startswith("/api/v1/scavenger"):
            for method in ("get", "post"):
                if method in operations:
                    for code in ("400", "401", "403", "404", "409", "413", "503"):
                        assert operations[method]["responses"][code]["content"]["application/json"]["schema"] == {
                            "$ref": "#/components/schemas/FrameworkError"
                        }


@pytest.mark.asyncio
async def test_storage_refusal_is_a_closed_unavailable_response(monkeypatch: pytest.MonkeyPatch) -> None:
    a = await api()

    async def refused(**_kwargs: Any) -> RetainedObservation:
        reason = "application_storage"
        raise ScavengerRefused(reason) from None

    monkeypatch.setattr(a.store, "read", refused)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)),
        base_url="http://testserver.local",
        headers={"authorization": AUTHORIZATION},
    ) as client:
        response = await client.get(f"/api/v1/scavenger/observations/{a.store.row.admission_id}")
    assert response.status_code == 503
    assert response.json()["extra"] == {"code": "application_storage"}
    assert response.json()["detail"] == "Scavenger operation refused."
    assert "PRIVATE-SEED-HTTP-SENTINEL" not in response.text


@pytest.mark.asyncio
async def test_exact_campaign_document_preserves_int64_facts_for_browser_text_display() -> None:
    a = await api()
    assert a.store.row.seed is not None
    seed = a.store.row.seed.model_copy(update={"budget_minor": 2**63 - 1})
    a.store.row = replace(a.store.row, seed=seed)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)),
        base_url="http://testserver.local",
        headers={"authorization": AUTHORIZATION},
    ) as client:
        response = await client.get(f"/api/v1/scavenger/observations/{a.store.row.admission_id}")
    assert response.status_code == 200
    assert response.json()["seed_document"] == canonical(seed).decode("utf-8")
    assert '"budget_minor":9223372036854775807' in response.json()["seed_document"]


@pytest.mark.asyncio
async def test_private_http_bodies_are_excluded_even_when_operator_body_diagnostics_are_enabled(
    capsys: pytest.CaptureFixture[str],
) -> None:
    a = await api(body_logging=True)
    route = f"/api/v1/scavenger/observations/{a.store.row.admission_id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=cast("Any", a.app)),
        base_url="http://testserver.local",
        headers={"authorization": AUTHORIZATION},
    ) as client:
        assert (await client.get(route)).status_code == 200
        client.headers["x-scavenger-csrf"] = client.cookies["scavenger-csrf"]
        assert a.store.row.seed is not None
        body = {
            "request_id": str(a.store.row.admission_id),
            "seed": a.store.row.seed.model_dump(mode="json"),
            "initial_filter": {"query": "PRIVATE-FILTER-BODY-SENTINEL"},
        }
        assert (
            await client.post("/api/v1/scavenger/observations", json=body, headers={"authorization": "Basic invalid"})
        ).status_code == 401
        assert (
            await client.post("/api/v1/scavenger/observations", json=body, headers={"x-scavenger-csrf": "invalid"})
        ).status_code == 403
        assert (await client.post(f"{route}/view", json={"query": "PRIVATE-FILTER-BODY-SENTINEL"})).status_code == 200
        assert (await client.get("/logging-control")).status_code == 200
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert "PUBLIC-LOG-CONTROL-VISIBLE" in output
    assert "PRIVATE-SEED-HTTP-SENTINEL" not in output
    assert "PRIVATE-FILTER-BODY-SENTINEL" not in output
    assert "Straße GPU" not in output
