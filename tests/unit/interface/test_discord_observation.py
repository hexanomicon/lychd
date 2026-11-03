"""Actual custom REST attempts are distinct from cached results and effect settlement."""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from lychd.interface.discord.rest import DiscordRest, DiscordRestError, EffectJournal
from lychd.interface.observation import OperationObservation, OperationObserver, observation_context


def rest_at(tmp_path: Path, client: httpx.AsyncClient, events: list[OperationObservation]) -> DiscordRest:
    return DiscordRest(
        token="synthetic-secret",  # noqa: S106 - synthetic fixture credential
        application_id="101",
        bot_user_id="102",
        guild_id="103",
        journal=EffectJournal(tmp_path / "effects"),
        client=client,
        observer=OperationObserver(
            generation=str(uuid4()),
            producer_id="fixture.rest",
            source="fixture.rest",
            target="fixture.api",
            sink=events.append,
        ),
    )


def identity(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"id": "102", "bot": True} if request.url.path.endswith("/users/@me") else {"id": "101"}
    )


@pytest.mark.asyncio
async def test_non_run_get_cache_refusal_and_late_run_delivery(tmp_path: Path) -> None:
    events: list[OperationObservation] = []
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return identity(request) if request.method == "GET" else httpx.Response(201, json={"id": "104"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rest = rest_at(tmp_path, client, events)
        refused = await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="one", scope="one")
        assert refused.status == "rejected"
        assert not events
        assert not requests
        await rest.verify_identity()
        assert len(events) == 4
        assert all(event.run_id is None for event in events)
        run_id = str(uuid4())
        # An explicit completed Run may correlate delivery after its own stream has closed.
        with observation_context(run_id=run_id):
            first = await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="one", scope="one")
        before = len(events)
        cached = await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="one", scope="one")
        refused = await rest.write("POST", "/guilds/103/roles", {"name": "changed"}, effect_key="one", scope="one")
    assert first == cached
    assert refused.status == "rejected"
    assert len(events) == before
    assert len(requests) == 3
    assert [event.activity_kind for event in events[-3:]] == [
        "transport_attempt",
        "transport_result",
        "operation_result",
    ]
    assert len({event.attempt_id for event in events[-3:]}) == 1
    assert all(event.run_id == run_id for event in events[-3:])
    assert events[-2].http_status == 201
    assert events[-2].effect_outcome is None
    assert events[-1].effect_outcome == "succeeded"


@pytest.mark.parametrize("failure", ["timeout", "cancel", "invalid_body", "http_403"])
@pytest.mark.asyncio
async def test_failure_preserves_seen_status_and_settlement(tmp_path: Path, failure: str) -> None:
    events: list[OperationObservation] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return identity(request)
        if failure == "timeout":
            msg = "private provider text"
            raise httpx.ReadTimeout(msg)
        if failure == "cancel":
            raise asyncio.CancelledError
        return httpx.Response(403 if failure == "http_403" else 201, content=b"not-json private body")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        rest = rest_at(tmp_path, client, events)
        await rest.verify_identity()
        events.clear()
        if failure == "cancel":
            with pytest.raises(asyncio.CancelledError):
                await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="one", scope="one")
        else:
            result = await rest.write("POST", "/guilds/103/roles", {"name": "safe"}, effect_key="one", scope="one")
            assert result.status == ("rejected" if failure == "http_403" else "unknown")
    assert len(events) == 3
    assert events[1].http_status == (403 if failure == "http_403" else 201 if failure == "invalid_body" else None)
    assert events[-1].effect_outcome == ("failed" if failure == "http_403" else "unknown")
    assert "private" not in "".join(event.model_dump_json() for event in events)
    assert rest.journal.inspect()[0].status == ("rejected" if failure == "http_403" else "unknown")


@pytest.mark.asyncio
async def test_read_decode_error_keeps_http_status(tmp_path: Path) -> None:
    events: list[OperationObservation] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"bad"))
    ) as client:
        rest = rest_at(tmp_path, client, events)
        with pytest.raises(DiscordRestError, match="invalid_response"):
            await rest.verify_identity()
    assert len(events) == 2
    assert events[-1].http_status == 200
    assert events[-1].error_category == "protocol"
