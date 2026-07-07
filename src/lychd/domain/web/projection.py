"""`Projector` — the single renderer of run events, cards, and settled turns.

The Projection Law made concrete: the server renders every piece of UI. This one
service absorbs the template-render helper, the SSE event dispatch, the consent-card
block, and the settled-turn lookup that were duplicated across `bridge.py` and
`nexus.py`. Being engine-bound and controller-free, it is unit-testable without HTTP.

Escaping contract (spec-00-FINAL C2): the emitter emits *raw* token text; the
Projector escapes it here. Status/fragment/consent payloads are structured and are
escaped by Jinja autoescape at template-render time.
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING, Any

from litestar.enums import MediaType
from litestar.response import Response

from lychd.domain.web.fragments import ValidatedFragment
from lychd.domain.web.schemas import ConsentCard, SwapTicket

# HTMX swaps the response body *and* stops the element's `every` polling on this code.
_HTTP_286_STOP_POLLING = 286


def stop_polling(html_body: str, *, trigger_after_settle: str | None = None) -> Response[str]:
    """Return an HTTP 286 response that swaps the body and halts HTMX polling."""
    headers = {"HX-Trigger-After-Settle": trigger_after_settle} if trigger_after_settle else {}
    return Response(
        content=html_body,
        status_code=_HTTP_286_STOP_POLLING,
        media_type=MediaType.HTML,
        headers=headers,
    )


if TYPE_CHECKING:
    from litestar.contrib.jinja import JinjaTemplateEngine

    from lychd.domain.codex.ledger import ConsentLedger
    from lychd.domain.codex.schemas import ConsentView
    from lychd.domain.cortex.events import RunEvent
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import SessionStorePort
    from lychd.domain.web.tickets import TicketRecord

# ConsentView.status vocabulary → the frozen ConsentState the card template reads
# (so `bridge/consent_update.html.j2` ships unchanged). "expired" renders as a refusal,
# consistent with `verdict()` reading expired as False.
_CONSENT_STATE: dict[str, str] = {
    "pending": "pending_consent",
    "granted": "consented",
    "denied": "refused",
    "expired": "refused",
}


class Projector:
    """Renders `RunEvent`s and one-off fragments to HTML strings (Projection Law)."""

    def __init__(
        self,
        *,
        engine: JinjaTemplateEngine,
        fragments: FragmentRegistry,
        sessions: SessionStorePort,
        consents: ConsentLedger,
    ) -> None:
        """Bind the projector to the app's template engine, registry, sessions, consents."""
        self._engine = engine
        self._fragments = fragments
        self._sessions = sessions
        self._consents = consents

    # -- generic render seam ---------------------------------------------

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a Jinja template to an HTML string (autoescaped)."""
        return self._engine.get_template(template_name).render(context)

    # -- SSE event projection --------------------------------------------

    async def project(self, event: RunEvent) -> str:
        """Render one run event's SSE payload to HTML.

        token → escaped text passthrough; status/node → controlled keyword; fragment →
        validated genUI render; consent → card + OOB sigil (from the ConsentLedger);
        log → escaped line; done → settled turn (OOB). The `Projector` is the sole escaper.
        """
        kind = str(event.kind)
        if kind == "token":
            return html.escape(event.data)
        if kind in {"status", "node"}:
            # F8/H7: status is a RunStatus/progress keyword and node is a node key —
            # controlled vocabularies today, but escape them at the render boundary so
            # any future model-derived value routed through `emit.status()/emit.node()`
            # can never reflect raw HTML into the SSE stream.
            return html.escape(event.data)
        if kind == "log":
            return html.escape(event.data)
        if kind == "fragment":
            return self._project_fragment(event.data)
        if kind == "consent":
            return await self._project_consent(event.data)
        # done: replace the whole streaming slot with the settled turn (OOB).
        return await self._project_done(event.run_id)

    async def _project_consent(self, data: str) -> str:
        consent_id = data
        if data.startswith("{"):
            parsed: dict[str, Any] = json.loads(data)
            consent_id = str(parsed.get("consent_id", ""))
        view = await self._consents.get(consent_id)
        return (
            self.render("bridge/consent_update.html.j2", await self.consent_context(view)) if view is not None else ""
        )

    def _project_fragment(self, payload: str) -> str:
        parsed = json.loads(payload)
        definition = self._fragments.get(str(parsed.get("fragment", "")))
        if definition is None:
            return ""
        params = definition.params_model.model_validate(parsed.get("params", {}))
        validated = ValidatedFragment(key=definition.key, template=definition.template, params=params)
        return self._fragments.render(validated, engine=self._engine)

    async def _project_done(self, run_id: str) -> str:
        from lychd.domain.web.schemas import BridgeTurn

        turn = await self._sessions.settled_turn_for_run(run_id)
        if turn is None:
            turn = BridgeTurn(role="agent", content="The turn has settled.", run_id=run_id, state="settled")
        # `run_data_state` is registered as a Jinja filter (lifespan/conftest), so the
        # template maps the internal state to the frozen run `data-state` vocabulary.
        return self.render("bridge/turn_agent.html.j2", {"turn": turn, "oob": True})

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

    async def consent_context(self, view: ConsentView) -> dict[str, Any]:
        """Build the `bridge/consent_update.html.j2` context for a consent view."""
        return {
            "consent": self.consent_card_view(view),
            "pending": await self._consents.pending_count(),
        }

    # -- swap tickets -----------------------------------------------------

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
