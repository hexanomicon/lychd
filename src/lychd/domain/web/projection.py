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

    from lychd.domain.cortex.stasis import RunEvent
    from lychd.domain.web.fragments import FragmentRegistry
    from lychd.domain.web.sessions import BridgeSessionStore, ConsentRecord
    from lychd.domain.web.tickets import TicketRecord


class Projector:
    """Renders `RunEvent`s and one-off fragments to HTML strings (Projection Law)."""

    def __init__(
        self,
        *,
        engine: JinjaTemplateEngine,
        fragments: FragmentRegistry,
        sessions: BridgeSessionStore,
    ) -> None:
        """Bind the projector to the app's template engine, registry, and sessions."""
        self._engine = engine
        self._fragments = fragments
        self._sessions = sessions

    # -- generic render seam ---------------------------------------------

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a Jinja template to an HTML string (autoescaped)."""
        return self._engine.get_template(template_name).render(context)

    # -- SSE event projection --------------------------------------------

    def project(self, event: RunEvent) -> str:
        """Render one run event's SSE payload to HTML.

        token → escaped text passthrough; status → controlled keyword; fragment →
        validated genUI render; consent → card + OOB sigil; done → settled turn (OOB).
        """
        if event.kind == "token":
            return html.escape(event.payload)
        if event.kind == "status":
            return event.payload
        if event.kind == "fragment":
            return self._project_fragment(event.payload)
        if event.kind == "consent":
            record = self._sessions.get_consent(event.payload)
            return self.consent_update(record) if record is not None else ""
        # done: replace the whole streaming slot with the settled turn (OOB).
        return self._project_done(event.run_id)

    def _project_fragment(self, payload: str) -> str:
        parsed = json.loads(payload)
        definition = self._fragments.get(str(parsed.get("key", "")))
        if definition is None:
            return ""
        params = definition.params_model.model_validate(parsed.get("params", {}))
        validated = ValidatedFragment(key=definition.key, template=definition.template, params=params)
        return self._fragments.render(validated, engine=self._engine)

    def _project_done(self, run_id: str) -> str:
        from lychd.domain.web.schemas import BridgeTurn

        turn = self._sessions.settled_turn_for_run(run_id)
        if turn is None:
            turn = BridgeTurn(role="agent", content="The turn has settled.", run_id=run_id, state="settled")
        # `run_data_state` is registered as a Jinja filter (lifespan/conftest), so the
        # template maps the internal state to the frozen run `data-state` vocabulary.
        return self.render("bridge/turn_agent.html.j2", {"turn": turn, "oob": True})

    # -- consent ----------------------------------------------------------

    def consent_card_view(self, record: ConsentRecord) -> ConsentCard:
        """Build the Seat-of-Consent view-model from a parked consent record."""
        vision = str(record.args.get("reason") or "This action requires the Magus's consent before it may proceed.")
        return ConsentCard(
            id=record.id,
            run_id=record.run_id,
            session_id=record.session_id,
            tool_name=record.tool_name,
            args=record.args,
            vision=vision,
            state=record.status,
        )

    def consent_context(self, record: ConsentRecord) -> dict[str, Any]:
        """Build the `bridge/consent_update.html.j2` context for a consent record."""
        return {
            "consent": self.consent_card_view(record),
            "pending": self._sessions.pending_consent_count(),
        }

    def consent_update(self, record: ConsentRecord) -> str:
        """Render the consent card + OOB sigil (the single de-duplicated block)."""
        return self.render("bridge/consent_update.html.j2", self.consent_context(record))

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
