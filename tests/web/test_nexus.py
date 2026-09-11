"""Nexus JSON board, transition planning, and ticket lifecycle."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient


def _completed_task(*, fail: bool = False) -> asyncio.Task[None]:
    loop = asyncio.new_event_loop()

    async def _run() -> None:
        if fail:
            message = "boom"
            raise RuntimeError(message)

    task = loop.create_task(_run())
    with suppress(RuntimeError):
        loop.run_until_complete(task)
    loop.close()
    return task


def test_board_lists_covens(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/api/v1/nexus")

    assert response.status_code == 200
    board = response.json()["board"]
    assert any(row["capability_key"] == "chat:local" for _, rows in board["covens"] for row in rows)
    assert "portals" in board
    runtimes = response.json()["delegated_runtimes"]
    assert [runtime["runtime_id"] for runtime in runtimes] == ["reference"]
    assert runtimes[0]["registrant_id"] == "builtin:delegation"
    assert "provider_id" not in runtimes[0]
    assert runtimes[0]["runnable"] is True


def test_plan_is_json(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(
        "/api/v1/nexus/plan",
        params={"target": "chat:local"},
    )

    assert response.status_code == 200
    assert response.json()["action_type"] == "SOFT_SWAP"


def test_plan_unknown_target_404(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get(
        "/api/v1/nexus/plan",
        params={"target": "chat:unknown"},
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"request_id": "request-extra", "target": "chat:local", "unexpected": True},
        {"request_id": "../traversal", "target": "chat:local"},
        {"request_id": "", "target": "chat:local"},
        {"request_id": " leading-space", "target": "chat:local"},
    ],
)
def test_invalid_swap_identity_is_rejected_before_durable_claim_or_transition(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
    payload: dict[str, object],
) -> None:
    calls: list[tuple[str, str]] = []

    class ClaimProbe:
        async def claim(self, *, request_id: str, target: str) -> Any:
            calls.append((request_id, target))
            pytest.fail("invalid input reached the durable claim boundary")

    fake_services.swap_requests = ClaimProbe()

    response = altar_client.post("/api/v1/nexus/swaps", json=payload)

    assert response.status_code == 400
    assert calls == []
    assert fake_services.tickets.count == 0
    assert fake_services.orchestrator.requests == []


def test_swap_input_rules_are_published_by_runtime_openapi(
    altar_client: TestClient[Litestar],
) -> None:
    schema = cast("dict[str, Any]", altar_client.get("/schema/openapi.json").json())
    swap = schema["components"]["schemas"]["SwapIntent"]

    assert swap["additionalProperties"] is False
    assert swap["properties"]["request_id"]["pattern"] == r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"


def test_swap_status_exposes_failure(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    record = fake_services.tickets.open(
        target="chat:local",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=_completed_task(fail=True),
    )
    response = altar_client.get(f"/api/v1/nexus/swaps/{record.id}")

    assert response.status_code == 200
    assert response.json()["ticket"]["state"] == "failed"


def test_terminal_ticket_stream_reconnect_preserves_endpoint_truth(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    record = fake_services.tickets.open(
        target="chat:local",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=_completed_task(),
    )

    stream = altar_client.get(
        f"/api/v1/nexus/swaps/{record.id}/events",
        headers={"Last-Event-ID": "99"},
    )
    status = altar_client.get(f"/api/v1/nexus/swaps/{record.id}")

    assert stream.status_code == 200
    assert "id: 1" in stream.text
    assert '"state": "settled"' in stream.text
    assert status.status_code == 200
    assert status.json()["ticket"]["state"] == "settled"


def test_swap_status_unknown_404(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.get("/api/v1/nexus/swaps/nope")
    assert response.status_code == 404


def test_transition_request_id_resolves_retained_ticket(
    altar_client: TestClient[Litestar],
) -> None:
    accepted = altar_client.post(
        "/api/v1/nexus/swaps",
        json={"request_id": "request-resolve", "target": "chat:local"},
    )
    assert accepted.status_code == 202
    assert accepted.json()["ticket"]["state"] == "warming"
    assert accepted.json()["ticket"]["target"] == "chat:local"
    request_id = accepted.json()["ticket"]["request_id"]

    resolved = altar_client.get(f"/api/v1/nexus/transitions/{request_id}")

    assert resolved.status_code == 200
    assert resolved.json()["request_id"] == request_id
    assert resolved.json()["source"] == "operator"


def test_swap_retry_reuses_the_first_ticket_and_transition(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    payload = {"request_id": "request-retry", "target": "chat:local"}

    first = altar_client.post("/api/v1/nexus/swaps", json=payload)
    second = altar_client.post("/api/v1/nexus/swaps", json=payload)

    assert first.status_code == second.status_code == 202
    assert first.json()["ticket"]["id"] == second.json()["ticket"]["id"]
    assert fake_services.orchestrator.requests.count("chat:local") == 1


def test_swap_request_identity_cannot_change_target(altar_client: TestClient[Litestar]) -> None:
    request_id = "request-conflict"
    accepted = altar_client.post(
        "/api/v1/nexus/swaps",
        json={"request_id": request_id, "target": "chat:local"},
    )
    conflict = altar_client.post(
        "/api/v1/nexus/swaps",
        json={"request_id": request_id, "target": "chat:other"},
    )

    assert accepted.status_code == 202
    assert conflict.status_code == 400
    assert request_id in conflict.json()["detail"]


def test_expired_ticket_cannot_relaunch_a_durably_admitted_request(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    from lychd.domain.web.tickets import TicketStore

    now = [100.0]
    fake_services.tickets = TicketStore(terminal_retention_s=1.0, clock=lambda: now[0])
    payload = {"request_id": "request-retired", "target": "chat:local"}

    accepted = altar_client.post("/api/v1/nexus/swaps", json=payload)
    ticket_id = accepted.json()["ticket"]["id"]
    settled = altar_client.get(f"/api/v1/nexus/swaps/{ticket_id}")
    now[0] = 101.0
    retry = altar_client.post("/api/v1/nexus/swaps", json=payload)

    assert accepted.status_code == 202
    assert settled.json()["ticket"]["state"] == "settled"
    assert retry.status_code == 409
    assert set(retry.json()) == {"status_code", "detail"}
    assert "no transition was relaunched" in retry.json()["detail"]
    assert fake_services.orchestrator.requests.count("chat:local") == 1


@pytest.mark.asyncio
async def test_concurrent_capacity_is_reserved_before_durable_claim(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    from lychd.domain.web.swap_requests import InMemorySwapRequestLedger, SwapRequestClaim
    from lychd.domain.web.tickets import TicketStore

    entered = asyncio.Event()
    release = asyncio.Event()
    backing = InMemorySwapRequestLedger()

    class BlockingLedger:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def claim(self, *, request_id: str, target: str) -> SwapRequestClaim:
            self.calls.append(request_id)
            entered.set()
            await release.wait()
            return await backing.claim(request_id=request_id, target=target)

    blocking = BlockingLedger()
    fake_services.tickets = TicketStore(capacity=1)
    fake_services.swap_requests = blocking
    transport = httpx.ASGITransport(app=altar_client.app)  # type: ignore[attr-defined]
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver.local", headers=dict(altar_client.headers)
    ) as client:
        first_request = asyncio.create_task(
            client.post(
                "/api/v1/nexus/swaps",
                json={"request_id": "request-race-first", "target": "chat:local"},
            )
        )
        await entered.wait()
        second = await client.post(
            "/api/v1/nexus/swaps",
            json={"request_id": "request-race-second", "target": "chat:local"},
        )
        release.set()
        first = await first_request

    assert first.status_code == 202
    assert second.status_code == 503
    assert set(second.json()) == {"status_code", "detail"}
    assert blocking.calls == ["request-race-first"]
