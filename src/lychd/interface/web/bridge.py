"""Versioned Bridge JSON API and semantic run-event stream."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import NAMESPACE_URL, uuid5

from litestar import Controller, Request, get, post
from litestar.datastructures import State
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException, ValidationException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED

from lychd.agents.router import Intent
from lychd.agents.workflows import WORKFLOW_REGISTRY
from lychd.agents.workflows.base import pattern_snapshot_is_valid
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.codex.ledger import ConsentLedger
from lychd.domain.cortex.engine import RunEngine
from lychd.domain.cortex.events import InProcessEventBus, RunEvent, RunEventKind
from lychd.domain.cortex.runs import TERMINAL_STATUSES, RunRecord, RunStatus
from lychd.domain.web.contracts import (
    BridgeSnapshot,
    BridgeTurnView,
    ConsentDecisionIntent,
    ConsentDecisionResult,
    MessageAccepted,
    MessageIntent,
    RunEventEnvelope,
    RunProjectionSnapshot,
    SessionCreated,
    SessionInspector,
    SessionSummary,
    SessionView,
)
from lychd.domain.web.projection import EventProjector
from lychd.domain.web.schemas import BridgeTurn, ConsentCard
from lychd.domain.web.sessions import SessionRecord, SessionStorePort

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lychd.domain.codex.sigil import Sigil
    from lychd.domain.cortex.ledger import RunLedger

_SSE_KEEPALIVE_S = 15.0


def _parse_last_event_id(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _turn_view(turn: BridgeTurn) -> BridgeTurnView:
    return BridgeTurnView(
        role=turn.role,
        content=turn.content,
        run_id=turn.run_id,
        state=turn.state,
        fragments=list(turn.fragments),
        created_at=turn.created_at,
    )


def _session_summary(session: SessionRecord) -> SessionSummary:
    return SessionSummary(id=session.id, title=session.title, created_at=session.created_at)


def _session_view(session: SessionRecord) -> SessionView:
    return SessionView(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        turns=[_turn_view(turn) for turn in session.turns],
    )


async def _terminal_stream(
    projector: EventProjector,
    run_id: str,
    *,
    cursor: int,
) -> AsyncIterator[ServerSentEventMessage]:
    boundary = max(cursor, 0)
    reset_event = RunEvent(
        run_id=run_id,
        event_id=str(uuid5(NAMESPACE_URL, f"lychd:resync:{run_id}:{boundary}")),
        seq=boundary,
        kind=RunEventKind.RESYNC,
        data="snapshot_required",
    )
    envelope = await projector.project(reset_event)
    yield ServerSentEventMessage(
        event=envelope.kind,
        data=envelope.model_dump_json(),
        id=str(envelope.seq),
    )


class BridgeController(Controller):
    """Serve the Bridge through one typed `/api/v1` contract."""

    path = "/api/v1/bridge"

    @get("", name="bridge:snapshot", operation_id="getBridgeSnapshot", guards=[requires_scopes("altar:read")])
    async def snapshot(
        self,
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> BridgeSnapshot:
        """Return the newest session or an empty reconstructable Bridge."""
        sessions = await bridge_sessions.list_sessions()
        session = sessions[0] if sessions else None
        return await self._snapshot(
            sessions,
            session,
            bridge_sessions,
            consents,
            run_bus,
            projector,
            state,
        )

    @get(
        "/sessions/{session_id:str}",
        name="bridge:session",
        operation_id="getBridgeSession",
        guards=[requires_scopes("altar:read")],
    )
    async def session_snapshot(
        self,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> BridgeSnapshot:
        """Return one selected session and the full session rail."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        return await self._snapshot(
            await bridge_sessions.list_sessions(),
            session,
            bridge_sessions,
            consents,
            run_bus,
            projector,
            state,
        )

    @post(
        "/sessions",
        status_code=HTTP_201_CREATED,
        name="bridge:create",
        operation_id="createBridgeSession",
        guards=[requires_scopes("runs:submit")],
    )
    async def create_session(
        self,
        bridge_sessions: NamedDependency[SessionStorePort],
    ) -> SessionCreated:
        """Open a new séance and return its typed identity."""
        return SessionCreated(session=_session_view(await bridge_sessions.create_session()))

    @post(
        "/sessions/{session_id:str}/messages",
        status_code=HTTP_200_OK,
        name="bridge:send",
        operation_id="sendBridgeMessage",
        guards=[requires_scopes("runs:submit")],
    )
    async def send(
        self,
        request: Request[Any, Any, Any],
        data: MessageIntent,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        run_engine: NamedDependency[RunEngine],
    ) -> MessageAccepted:
        """Record a complete text command and admit one run."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        prompt = data.prompt.strip()
        if not prompt:
            raise ValidationException(detail="An empty offering cannot be spoken.")

        sigil = cast("Sigil", request.user)
        turn: BridgeTurn | None = None

        async def retain_user_turn(run_id: str) -> None:
            nonlocal turn
            turn = BridgeTurn(role="user", content=prompt, run_id=run_id)
            await bridge_sessions.add_turn(session_id, turn)

        handle = await run_engine.submit(
            Intent(
                session_id=session_id,
                prompt=prompt,
                source="bridge",
                sigil_name=sigil.name,
                sigil_scopes=frozenset(sigil.scopes),
            ),
            retain_before_publish=retain_user_turn,
        )
        if turn is None:  # pragma: no cover - RunEngine guarantees callback-before-return
            msg = "Bridge admission returned before retaining its user turn."
            raise RuntimeError(msg)
        return MessageAccepted(
            run_id=handle.run_id,
            pattern_id=handle.pattern_id,
            pattern_revision=handle.pattern_revision,
            loom_path=f"/loom/{handle.pattern_id}/{handle.pattern_revision}",
            orb_path=f"/orb/{handle.run_id}",
            evidence_capture=handle.evidence_capture,
            turn=_turn_view(turn),
        )

    @get(
        "/runs/{run_id:str}",
        name="bridge:run-snapshot",
        operation_id="getBridgeRunSnapshot",
        guards=[requires_scopes("altar:read")],
    )
    async def run_snapshot(
        self,
        run_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> RunProjectionSnapshot:
        """Return one replaceable run projection at an exact stream cursor."""
        run = await state.services.ledger.get(run_id)
        if run is None:
            raise NotFoundException(detail="Unknown run.")

        return await self._run_projection(
            run,
            bridge_sessions,
            run_bus,
            projector,
            state,
        )

    async def _run_projection(
        self,
        run: RunRecord,
        bridge_sessions: SessionStorePort,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> RunProjectionSnapshot:
        manifest = run.pattern_manifest
        pattern_id = str(manifest.get("key") or run.workflow_name)
        revision = str(manifest.get("revision") or "legacy-unversioned")
        digest = manifest.get("digest")
        registered = WORKFLOW_REGISTRY.get_revision(pattern_id, revision)
        loom_available = (
            pattern_snapshot_is_valid(manifest) and registered is not None and registered.manifest.digest == digest
        )
        loom_path = f"/loom/{pattern_id}/{revision}" if loom_available else None
        orb_path = f"/orb/{run.run_id}"
        ledger = cast("RunLedger", state.services.ledger)
        evidence_capture = cast(
            "Literal['process_local', 'durable_best_effort']",
            ledger.evidence_capture,
        )
        latest_node, latest_dispatch, latest_transition = await asyncio.gather(
            ledger.latest_event(run.run_id, RunEventKind.NODE),
            ledger.latest_event(run.run_id, RunEventKind.DISPATCH),
            ledger.latest_event(run.run_id, RunEventKind.TRANSITION),
        )
        retained_dispatch_occurrence_id = (
            latest_dispatch.meta.get("occurrence_id") if latest_dispatch is not None else None
        )
        retained_transition_occurrence_id = (
            latest_transition.meta.get("occurrence_id") if latest_transition is not None else None
        )
        retained_occurrence_id = (
            (latest_node.meta.get("occurrence_id") if latest_node is not None else None)
            or retained_dispatch_occurrence_id
            or retained_transition_occurrence_id
        )
        retained_grant_id = latest_dispatch.meta.get("grant_id") if latest_dispatch is not None else None
        retained_capability_key = (latest_dispatch.data if latest_dispatch is not None else None) or (
            latest_transition.meta.get("capability_key") if latest_transition is not None else None
        )
        retained_transition_request_id = latest_transition.data if latest_transition is not None else None
        retained_transition_phase = latest_transition.meta.get("phase") if latest_transition is not None else None
        retained_delegated_job_id = latest_node.meta.get("delegated_job_id") if latest_node is not None else None
        retained_delegated_runtime = latest_node.meta.get("delegated_runtime") if latest_node is not None else None
        delegates = getattr(state.services, "delegates", None)
        delegated_jobs = await delegates.jobs_for_run(run.run_id) if delegates is not None else ()
        delegated_job = delegated_jobs[-1] if delegated_jobs else None
        retained_delegated_job_id = retained_delegated_job_id or (
            delegated_job.ref.job_id if delegated_job is not None else None
        )
        retained_delegated_runtime = retained_delegated_runtime or (
            delegated_job.ref.runtime if delegated_job is not None else None
        )
        delegated_profile = delegated_job.ref.profile if delegated_job is not None else None
        delegated_status = delegated_job.status.value if delegated_job is not None else None
        live = run_bus.snapshot(run.run_id)
        if live is not None:
            fragments = [(await projector.project(fragment)).payload for fragment in live.fragments]
            return RunProjectionSnapshot(
                session_id=run.session_id,
                run_id=run.run_id,
                cursor=live.cursor,
                content=live.content,
                run_status=run.status.value,
                activity=live.activity,
                pattern_id=pattern_id,
                pattern_revision=revision,
                loom_path=loom_path,
                orb_path=orb_path,
                evidence_capture=evidence_capture,
                fragments=fragments,
                occurrence_id=live.occurrence_id or retained_occurrence_id,
                dispatch_occurrence_id=live.dispatch_occurrence_id or retained_dispatch_occurrence_id,
                grant_id=live.grant_id or retained_grant_id,
                capability_key=live.capability_key or retained_capability_key,
                transition_occurrence_id=live.transition_occurrence_id or retained_transition_occurrence_id,
                transition_request_id=live.transition_request_id or retained_transition_request_id,
                transition_phase=live.transition_phase or retained_transition_phase,
                delegated_job_id=live.delegated_job_id or retained_delegated_job_id,
                delegated_runtime=live.delegated_runtime or retained_delegated_runtime,
                delegated_profile=delegated_profile,
                delegated_status=delegated_status,
                terminal=live.terminal,
            )

        turn = await bridge_sessions.settled_turn_for_run(run.run_id)
        return RunProjectionSnapshot(
            session_id=run.session_id,
            run_id=run.run_id,
            cursor=(await state.services.ledger.next_seq(run.run_id)) - 1,
            content=turn.content if turn is not None else "",
            run_status=run.status.value,
            activity=run.status.value,
            pattern_id=pattern_id,
            pattern_revision=revision,
            loom_path=loom_path,
            orb_path=orb_path,
            evidence_capture=evidence_capture,
            fragments=[],
            occurrence_id=retained_occurrence_id,
            dispatch_occurrence_id=retained_dispatch_occurrence_id,
            grant_id=retained_grant_id,
            capability_key=retained_capability_key,
            transition_occurrence_id=retained_transition_occurrence_id,
            transition_request_id=retained_transition_request_id,
            transition_phase=retained_transition_phase,
            delegated_job_id=retained_delegated_job_id,
            delegated_runtime=retained_delegated_runtime,
            delegated_profile=delegated_profile,
            delegated_status=delegated_status,
            terminal=run.status in TERMINAL_STATUSES,
        )

    @get(
        "/runs/{run_id:str}/events",
        name="bridge:events",
        operation_id="streamBridgeRunEvents",
        guards=[requires_scopes("altar:read")],
        responses={
            HTTP_200_OK: ResponseSpec(
                RunEventEnvelope,
                generate_examples=False,
                media_type="text/event-stream",
                description="Versioned semantic run events.",
            ),
        },
    )
    async def events(
        self,
        request: Request[Any, Any, Any],
        run_id: FromPath[str],
        run_bus: NamedDependency[InProcessEventBus],
        projector: NamedDependency[EventProjector],
        state: State,
    ) -> ServerSentEvent:
        """Stream versioned JSON envelopes with replay and terminal synthesis."""
        from_seq = _parse_last_event_id(request.headers.get("Last-Event-ID"))
        run = await state.services.ledger.get(run_id)
        if run is None:
            raise NotFoundException(detail="Unknown run.")
        if run.status in TERMINAL_STATUSES:
            return ServerSentEvent(
                _terminal_stream(
                    projector,
                    run_id,
                    cursor=(await state.services.ledger.next_seq(run_id)) - 1,
                ),
            )

        async def stream() -> AsyncIterator[ServerSentEventMessage]:
            source = run_bus.subscribe(run_id, from_seq=from_seq)
            pending: asyncio.Task[Any] | None = None
            try:
                while True:
                    if pending is None:
                        pending = asyncio.ensure_future(source.__anext__())
                    done, _ = await asyncio.wait({pending}, timeout=_SSE_KEEPALIVE_S)
                    if not done:
                        yield ServerSentEventMessage(comment="keepalive")
                        continue
                    try:
                        event = pending.result()
                    except StopAsyncIteration:
                        return
                    finally:
                        pending = None
                    envelope = await projector.project(event)
                    yield ServerSentEventMessage(
                        event=envelope.kind,
                        data=envelope.model_dump_json(),
                        id=str(envelope.seq),
                    )
            finally:
                if pending is not None:
                    pending.cancel()
                    with contextlib.suppress(BaseException):
                        await pending
                aclose = getattr(source, "aclose", None)
                if aclose is not None:
                    with contextlib.suppress(Exception):
                        await aclose()

        return ServerSentEvent(stream())

    @post(
        "/consents/{consent_id:str}/decision",
        status_code=HTTP_200_OK,
        name="bridge:consent",
        operation_id="decideBridgeConsent",
        guards=[requires_scopes("runs:approve")],
    )
    async def consent(
        self,
        request: Request[Any, Any, Any],
        data: ConsentDecisionIntent,
        consent_id: FromPath[str],
        consents: NamedDependency[ConsentLedger],
        run_engine: NamedDependency[RunEngine],
        projector: NamedDependency[EventProjector],
    ) -> ConsentDecisionResult:
        """Commit one idempotent verdict before re-admitting the parked run."""
        view = await consents.get(consent_id)
        if view is None:
            raise NotFoundException(detail="Unknown consent.")
        if view.status == "pending":
            approved = data.verdict == "approve"
            sigil = cast("Sigil", request.user)
            decided = await consents.decide(consent_id, approved=approved, decided_by=sigil.name)
            await run_engine.approve(consent_id, approved=approved)
            view = decided or view
        return ConsentDecisionResult(
            consent=projector.consent_card_view(view),
            pending_count=await consents.pending_count(),
        )

    @get(
        "/sessions/{session_id:str}/inspector",
        name="bridge:inspector",
        operation_id="getBridgeSessionInspector",
        guards=[requires_scopes("altar:read")],
    )
    async def inspector(
        self,
        session_id: FromPath[str],
        bridge_sessions: NamedDependency[SessionStorePort],
        consents: NamedDependency[ConsentLedger],
    ) -> SessionInspector:
        """Return a compact contextual inspector."""
        session = await bridge_sessions.get_session(session_id)
        if session is None:
            raise NotFoundException(detail="Unknown session.")
        return SessionInspector(
            session_id=session_id,
            title=session.title,
            turn_count=len(session.turns),
            pending_count=await consents.pending_count(),
        )

    async def _snapshot(
        self,
        sessions: list[SessionRecord],
        session: SessionRecord | None,
        bridge_sessions: SessionStorePort,
        consents: ConsentLedger,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> BridgeSnapshot:
        return BridgeSnapshot(
            sessions=[_session_summary(item) for item in sessions],
            session=_session_view(session) if session is not None else None,
            active_runs=await self._active_run_projections(
                session,
                bridge_sessions,
                run_bus,
                projector,
                state,
            ),
            pending_consents=await self._pending_cards(consents, projector, state, session),
            pending_count=await consents.pending_count(),
        )

    async def _active_run_projections(
        self,
        session: SessionRecord | None,
        bridge_sessions: SessionStorePort,
        run_bus: InProcessEventBus,
        projector: EventProjector,
        state: State,
    ) -> list[RunProjectionSnapshot]:
        """Project the selected session's runs whose event channels live here."""
        if session is None:
            return []

        active: dict[str, RunRecord] = {}
        for status in RunStatus:
            if status not in TERMINAL_STATUSES:
                for run in await state.services.ledger.list_by_status(status):
                    active[run.run_id] = run

        projections: list[RunProjectionSnapshot] = []
        for run in sorted(active.values(), key=lambda item: item.created_at):
            if run.session_id != session.id or run_bus.snapshot(run.run_id) is None:
                continue
            projections.append(
                await self._run_projection(
                    run,
                    bridge_sessions,
                    run_bus,
                    projector,
                    state,
                ),
            )
        return projections

    async def _pending_cards(
        self,
        consents: ConsentLedger,
        projector: EventProjector,
        state: State,
        session: SessionRecord | None,
    ) -> list[ConsentCard]:
        if session is None:
            return []
        cards: list[ConsentCard] = []
        for view in await consents.pending_views():
            run = await state.services.ledger.get(view.run_id)
            if run is not None and run.session_id == session.id:
                cards.append(projector.consent_card_view(view))
        return cards
