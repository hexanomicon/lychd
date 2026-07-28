"""Nexus JSON board, transition planning, and ticket lifecycle."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

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


def test_swap_returns_accepted_ticket(altar_client: TestClient[Litestar]) -> None:
    response = altar_client.post(
        "/api/v1/nexus/swaps",
        json={"target": "chat:local"},
    )

    assert response.status_code == 202
    assert response.json()["ticket"]["state"] == "warming"
    assert response.json()["ticket"]["target"] == "chat:local"


def test_swap_status_settles(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    record = fake_services.tickets.open(
        target="chat:local",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=_completed_task(),
    )
    response = altar_client.get(f"/api/v1/nexus/swaps/{record.id}")

    assert response.status_code == 200
    assert response.json()["ticket"]["state"] == "settled"


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


@pytest.mark.parametrize("last_event_id", ["0", "1", "99"])
def test_terminal_ticket_stream_reconnect_preserves_endpoint_truth(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
    last_event_id: str,
) -> None:
    record = fake_services.tickets.open(
        target="chat:local",
        action_type="SOFT_SWAP",
        total_metabolic_cost=1.0,
        task=_completed_task(),
    )

    stream = altar_client.get(
        f"/api/v1/nexus/swaps/{record.id}/events",
        headers={"Last-Event-ID": last_event_id},
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
