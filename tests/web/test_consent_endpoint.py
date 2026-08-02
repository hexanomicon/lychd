"""Bridge consent JSON contract and verdict-before-resume ordering."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lychd.domain.codex.schemas import ConsentView
from lychd.domain.codex.sigil import Sigil

if TYPE_CHECKING:
    from types import SimpleNamespace

    from litestar import Litestar
    from litestar.testing import TestClient

    from lychd.domain.web.projection import EventProjector


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
    response = altar_client.post(
        "/api/v1/bridge/consents/nope/decision",
        json={"verdict": "approve"},
    )
    assert response.status_code == 404


def test_consent_verdict_commits_before_resume(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    consent_id = _park(fake_services)
    response = altar_client.post(
        f"/api/v1/bridge/consents/{consent_id}/decision",
        json={"verdict": "approve"},
    )

    assert response.status_code == 200
    assert response.json()["consent"]["state"] == "consented"
    assert response.json()["pending_count"] == 0
    assert _verdict(fake_services, consent_id) is True
    approvals = fake_services.run_engine.approvals
    assert len(approvals) == 1
    assert approvals[0][0] == consent_id
    assert approvals[0][2] is True


def test_consent_retry_replays_the_authoritative_first_verdict(
    altar_client: TestClient[Litestar],
    fake_services: SimpleNamespace,
) -> None:
    consent_id = _park(fake_services, run_id="run_y")
    altar_client.post(
        f"/api/v1/bridge/consents/{consent_id}/decision",
        json={"verdict": "deny"},
    )
    again = altar_client.post(
        f"/api/v1/bridge/consents/{consent_id}/decision",
        json={"verdict": "approve"},
    )

    assert again.status_code == 200
    assert again.json()["consent"]["state"] == "refused"
    assert _verdict(fake_services, consent_id) is False
    assert fake_services.run_engine.approvals == [
        (consent_id, False, False),
        (consent_id, False, False),
    ]


def test_cancelled_consent_remains_distinct_from_human_refusal(projector: EventProjector) -> None:
    card = projector.consent_card_view(
        ConsentView(
            id="consent-cancelled",
            run_id="run-cancelled",
            tool_name="request_coven_swap",
            status="cancelled",
        )
    )

    assert card.state == "cancelled"
