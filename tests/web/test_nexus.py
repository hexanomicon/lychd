"""Nexus board, plan drawer, and swap lifecycle (202 → poll → 286 settle)."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient

_HX = {"HX-Request": "true"}


def _completed_task(*, fail: bool = False) -> asyncio.Task[None]:
    """Build an already-finished asyncio task (settled or faulted) for a fake ticket."""
    loop = asyncio.new_event_loop()

    async def _run() -> None:
        if fail:
            msg = "boom"
            raise RuntimeError(msg)

    task = loop.create_task(_run())
    with suppress(RuntimeError):
        loop.run_until_complete(task)
    loop.close()
    return task


def test_board_lists_covens(altar_client: TestClient[Litestar]) -> None:
    """The board fragment renders the fake covens and the portals column."""
    response = altar_client.get("/nexus/board", headers=_HX)
    assert response.status_code == 200
    assert "chat:local" in response.text
    assert "Portals" in response.text


def test_plan_htmx_vs_json(altar_client: TestClient[Litestar]) -> None:
    """Plan is a drawer fragment under HTMX and a JSON TransitionPlan otherwise."""
    fragment = altar_client.get("/nexus/plan", params={"target": "chat:local"}, headers=_HX)
    assert fragment.status_code == 200
    assert 'data-fragment="nexus.plan"' in fragment.text

    as_json = altar_client.get("/nexus/plan", params={"target": "chat:local"})
    assert as_json.status_code == 200
    assert as_json.json()["action_type"] == "SOFT_SWAP"


def test_plan_unknown_target_404(altar_client: TestClient[Litestar]) -> None:
    """An unknown capability target is 404."""
    response = altar_client.get("/nexus/plan", params={"target": "chat:unknown"}, headers=_HX)
    assert response.status_code == 404


def test_swap_returns_202_retargeted_ticket(altar_client: TestClient[Litestar]) -> None:
    """A swap launches (202) and retargets the warming ticket to #nexus-plan."""
    response = altar_client.post("/nexus/swap", headers=_HX, data={"target": "chat:local"})
    assert response.status_code == 202
    assert response.headers["hx-retarget"] == "#nexus-plan"
    assert 'data-state="warming"' in response.text


def test_swap_requires_htmx(altar_client: TestClient[Litestar]) -> None:
    """Swap is HTMX-only."""
    response = altar_client.post("/nexus/swap", data={"target": "chat:local"})
    assert response.status_code == 400


def test_swap_status_settles_with_286(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A finished swap settles with HTTP 286 + board-refresh trigger and pops the ticket."""
    record = fake_services.tickets.open(
        target="chat:local", action_type="SOFT_SWAP", total_metabolic_cost=1.0, task=_completed_task()
    )
    response = altar_client.get(f"/nexus/swap/{record.id}")
    assert response.status_code == 286
    assert response.headers["hx-trigger-after-settle"] == "nexus:swap-settled"
    assert 'data-state="settled"' in response.text
    assert fake_services.tickets.get(record.id) is None


def test_swap_status_failed_task(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A faulted swap settles as failed (matte, law §1.5)."""
    record = fake_services.tickets.open(
        target="chat:local", action_type="SOFT_SWAP", total_metabolic_cost=1.0, task=_completed_task(fail=True)
    )
    response = altar_client.get(f"/nexus/swap/{record.id}")
    assert response.status_code == 286
    assert 'data-state="failed"' in response.text


def test_swap_status_unknown_404(altar_client: TestClient[Litestar]) -> None:
    """An unknown ticket id is 404."""
    response = altar_client.get("/nexus/swap/nope")
    assert response.status_code == 404
