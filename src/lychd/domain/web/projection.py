"""Semantic run-event projection for every typed client.

The Vessel validates event payloads and emits inert JSON. It does not render HTML.
Svelte, Android, and future clients project the same versioned envelope.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import ValidationError

from lychd.domain.web.contracts import RunEventEnvelope
from lychd.domain.web.fragments import ValidatedFragment
from lychd.domain.web.schemas import ConsentCard, SwapTicket

if TYPE_CHECKING:
    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.codex.schemas import ConsentView
    from lychd.domain.cortex.events import RunEvent
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort
    from lychd.domain.web.tickets import TicketRecord

# ConsentView.status vocabulary → the stable client consent state.
_CONSENT_STATE: dict[str, str] = {
    "pending": "pending_consent",
    "granted": "consented",
    "denied": "refused",
    "expired": "refused",
}
EventKind = Literal["token", "status", "node", "fragment", "consent", "log", "done", "resync"]


class EventProjector:
    """Validate and shape `RunEvent` values into versioned JSON envelopes."""

    def __init__(
        self,
        *,
        fragments: FragmentRegistry,
        sessions: SessionStorePort,
        consents: ConsentLedger,
    ) -> None:
        """Bind the projector to the descriptor registry, sessions, and consent ledger."""
        self._fragments = fragments
        self._sessions = sessions
        self._consents = consents

    async def project(self, event: RunEvent) -> RunEventEnvelope:
        """Project one internal run event without interpreting data as markup."""
        kind = cast("EventKind", str(event.kind))
        payload: dict[str, Any]
        if kind in {"token", "status", "node", "log"}:
            payload = {"text": event.data, **event.meta}
        elif kind == "fragment":
            payload = self._project_fragment(event.data)
        elif kind == "consent":
            payload = await self._project_consent(event.data)
        elif kind == "done":
            payload = await self._project_done(event.run_id, event.data)
        else:  # explicit `resync`: replace through this stream boundary
            payload = {"reason": event.data, "cursor": event.seq}
        return RunEventEnvelope(
            run_id=event.run_id,
            seq=event.seq,
            kind=kind,
            occurred_at=event.ts,
            payload=payload,
        )

    async def _project_consent(self, data: str) -> dict[str, Any]:
        consent_id = data
        if data.startswith("{"):
            try:
                parsed: dict[str, Any] = json.loads(data)
                consent_id = str(parsed.get("consent_id", ""))
            except json.JSONDecodeError:
                consent_id = ""
        view = await self._consents.get(consent_id)
        return {"consent": asdict(self.consent_card_view(view))} if view is not None else {}

    def _project_fragment(self, payload: str) -> dict[str, Any]:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return {"kind": "genui.unknown", "schema_version": 1, "props": {}, "actions": []}
        definition = self._fragments.get(str(parsed.get("fragment", "")))
        if definition is None:
            return {"kind": "genui.unknown", "schema_version": 1, "props": {}, "actions": []}
        try:
            params = definition.params_model.model_validate(parsed.get("params", {}))
        except ValidationError:
            return {"kind": "genui.unknown", "schema_version": 1, "props": {}, "actions": []}
        validated = ValidatedFragment(key=definition.key, params=params)
        return self._fragments.descriptor(validated)

    async def _project_done(self, run_id: str, status: str) -> dict[str, Any]:
        from lychd.domain.web.schemas import BridgeTurn

        turn = await self._sessions.settled_turn_for_run(run_id)
        if turn is None:
            turn = BridgeTurn(role="agent", content="The turn has settled.", run_id=run_id, state="settled")
        return {
            "status": status,
            "turn": {
                "role": turn.role,
                "content": turn.content,
                "run_id": turn.run_id,
                "state": turn.state,
                "fragments": list(turn.fragments),
                "created_at": turn.created_at.isoformat(),
            },
        }

    # -- consent ----------------------------------------------------------

    def consent_card_view(self, view: ConsentView) -> ConsentCard:
        """Build the Seat-of-Consent view-model from a `ConsentView` (status-mapped)."""
        vision = str(view.args.get("reason") or "This action requires the Magus's consent before it may proceed.")
        state: Any = _CONSENT_STATE.get(view.status, "refused")
        return ConsentCard(
            id=view.id,
            run_id=view.run_id,
            tool_name=view.tool_name,
            args=view.args,
            vision=vision,
            state=state,
        )

    def ticket_view(
        self,
        record: TicketRecord,
        *,
        settled: bool = False,
        failed: bool = False,
    ) -> SwapTicket:
        """Project a ticket record into its `SwapTicket` view-model."""
        if failed:
            state = "failed"
        elif settled:
            state = "settled"
        else:
            state = "warming"
        return SwapTicket(
            id=record.id,
            target=record.target,
            state=state,
            action_type=record.action_type,
            total_metabolic_cost=record.total_metabolic_cost,
        )
