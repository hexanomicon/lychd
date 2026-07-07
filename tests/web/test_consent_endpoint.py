"""Consent endpoint (4C-5): 404, idempotent re-render, verdict-order via fake engine."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient

_HX = {"HX-Request": "true"}


def _park(fake_services: SimpleNamespace, run_id: str = "run_x") -> str:
    async def _do() -> str:
        decision = await fake_services.consents.park(
            run_id=run_id,
            tool_name="request_coven_swap",
            tool_call_id="c1",
            call_ids=("c1",),
            args={"reason": "swap"},
            sigil=Sigil(name="magus", scopes=frozenset({"*"})),
        )
        return decision.consent_id

    return asyncio.run(_do())


def _verdict(fake_services: SimpleNamespace, consent_id: str) -> Any:
    return asyncio.run(fake_services.consents.verdict(consent_id))


def test_consent_unknown_404(altar_client: TestClient[Litestar]) -> None:
    """An unknown consent id is 404."""
    response = altar_client.post("/bridge/consents/nope", headers=_HX, data={"verdict": "approve"})
    assert response.status_code == 404


def test_consent_verdict_renders_and_orders_before_approve(
    altar_client: TestClient[Litestar], fake_services: SimpleNamespace
) -> None:
    """Approve re-renders the consented card; the verdict commits BEFORE engine.approve."""
    consent_id = _park(fake_services)
    response = altar_client.post(f"/bridge/consents/{consent_id}", headers=_HX, data={"verdict": "approve"})
    assert response.status_code == 200
    assert 'data-state="consented"' in response.text
    assert "hx-swap-oob" in response.text
    assert _verdict(fake_services, consent_id) is True
    # Ordering (C3): at approve-call time the ledger verdict was already non-None.
    approvals = fake_services.run_engine.approvals
    assert len(approvals) == 1
    assert approvals[0][0] == consent_id
    assert approvals[0][2] is True  # verdict seen at approve time


def test_consent_idempotent_rerender(altar_client: TestClient[Litestar], fake_services: SimpleNamespace) -> None:
    """A second verdict POST re-renders without re-resolving; fake engine sees no 2nd approve."""
    consent_id = _park(fake_services, run_id="run_y")
    altar_client.post(f"/bridge/consents/{consent_id}", headers=_HX, data={"verdict": "deny"})
    again = altar_client.post(f"/bridge/consents/{consent_id}", headers=_HX, data={"verdict": "approve"})
    assert again.status_code == 200
    # the first verdict (denied) stands — the second POST does not overturn it
    assert _verdict(fake_services, consent_id) is False
    # exactly one approve reached the engine (the idempotent re-render did not re-approve)
    assert len(fake_services.run_engine.approvals) == 1
