"""Selected-Run Orb reads and bounded, retained-evidence live updates."""

from __future__ import annotations

import asyncio
import base64
import binascii
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any, cast

from litestar import Controller, Request, get
from litestar.datastructures import State
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException, ValidationException
from litestar.openapi.datastructures import ResponseSpec
from litestar.params import FromPath, QueryParameter
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_429_TOO_MANY_REQUESTS
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from lychd.agents.workflows import WorkflowRegistry, resolve_pinned_workflow
from lychd.domain.codex.guards import requires_scopes
from lychd.domain.cortex.events import InProcessEventBus
from lychd.domain.cortex.runs import TERMINAL_STATUSES
from lychd.domain.oculus.models import OrbRuntimeSnapshot
from lychd.domain.oculus.runtime import RuntimeCatalogue
from lychd.domain.web.contracts import (
    FrameworkError,
    OrbCreationSummary,
    OrbEventEnvelope,
    OrbRunPage,
    OrbRunSnapshot,
    OrbRunSummary,
)
from lychd.domain.web.orb import bridge_context_path, build_orb_snapshot
from lychd.domain.web.schemas import LoomView, build_loom_view
from lychd.interface.web.bridge_stream import BoundedRunEventStream

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Awaitable, Callable

    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.delegation.ports import DelegatedAgentCoordinatorPort
    from lychd.domain.web.orb import CaptureClass

_POLL_INTERVAL_S = 1.0
_KEEPALIVE_INTERVAL_S = 15.0
_LIVE_PAGE_SIZE = 100
# Step.seq is a PostgreSQL INTEGER; reject overflow before issuing a retained-row query.
_MAX_EVIDENCE_CURSOR = (1 << 31) - 1


class _RunCursor(BaseModel):
    """An opaque timestamp/id keyset; it carries no permission or private content."""

    model_config = ConfigDict(extra="forbid", strict=True)

    created_at: AwareDatetime
    run_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


def _workflow_view(run: RunRecord, workflows: WorkflowRegistry) -> LoomView | None:
    workflow = resolve_pinned_workflow(workflows, workflow_name=run.workflow_name, snapshot=run.pattern_manifest)
    return build_loom_view(workflow) if workflow is not None else None


async def _creation_summary(state: State, request: Request[Any, Any, Any], run_id: str) -> OrbCreationSummary | None:
    """Map the optional application's authorized, content-free record at HTTP."""
    service = getattr(state.services, "creation", None)
    if service is None:
        return None
    summary = await service.summary_for_run(run_id, authentication=request.auth, principal=request.user)
    if summary is None or summary.run_id != run_id:
        return None
    return OrbCreationSummary(
        case_id=summary.case_id,
        admission_id=summary.admission_id,
        run_id=summary.run_id,
        admission_current=summary.admission_current,
        native_status=summary.native_status,
        reason_code=summary.reason_code,
        deadline=summary.deadline,
        deadline_elapsed=summary.deadline_elapsed,
        slot_encumbered=summary.slot_encumbered,
        constructor_present=summary.constructor_present,
        constructor_adopted=summary.constructor_adopted,
        verifier_present=summary.verifier_present,
        verifier_adopted=summary.verifier_adopted,
        candidate_present=summary.candidate_present,
        verdict_present=summary.verdict_present,
        native_disposition=summary.native_disposition,
        external_disposition=summary.external_disposition,
        feedback_status=summary.feedback_status,
        current_assessment_id=summary.current_assessment_id,
        current_decision_id=summary.current_decision_id,
    )


async def _orb_events(
    ledger: RunLedger,
    run_id: str,
    workflows: WorkflowRegistry,
    *,
    after_seq: int,
    delegates: DelegatedAgentCoordinatorPort | None = None,
    read_creation: Callable[[], Awaitable[OrbCreationSummary | None]] | None = None,
) -> AsyncGenerator[ServerSentEventMessage]:
    """Poll retained truth without a queue or any dependency on live token delivery.

    Each pull retains at most one page. A slow reader delays its own next read;
    it never queues producer events or prevents Run execution. Terminal status
    settles the currently retained account, whose capture remains best effort.
    Later external reviews require a fresh snapshot after terminal settlement.
    """
    cursor = after_seq
    previous_metadata: tuple[object, ...] | None = None
    loop = asyncio.get_running_loop()
    keepalive_at = loop.time() + _KEEPALIVE_INTERVAL_S
    while True:
        run = await ledger.get(run_id)
        if run is None:
            return
        snapshot = await build_orb_snapshot(
            ledger,
            run,
            after_seq=cursor,
            limit=_LIVE_PAGE_SIZE,
            workflow=_workflow_view(run, workflows),
            delegates=delegates,
        )
        snapshot.creation = await read_creation() if read_creation is not None else None
        if cursor > snapshot.ledger_head_seq:
            envelope = OrbEventEnvelope(
                run_id=run_id,
                kind="reset",
                after_seq=cursor,
                cursor=snapshot.ledger_head_seq,
                snapshot=snapshot,
            )
            yield ServerSentEventMessage(event=envelope.kind, data=envelope.model_dump_json(), id=str(envelope.cursor))
            return
        next_cursor = snapshot.page_end_seq if snapshot.page_end_seq is not None else cursor
        pending_evidence = snapshot.has_more or snapshot.ledger_head_seq > next_cursor
        terminal = run.status in TERMINAL_STATUSES and not pending_evidence
        metadata = (
            snapshot.run,
            snapshot.pattern,
            snapshot.capture,
            snapshot.delegated_jobs,
            snapshot.bridge_preference,
            snapshot.creation,
            snapshot.known_omissions,
        )
        if snapshot.evidence or metadata != previous_metadata or terminal:
            envelope = OrbEventEnvelope(
                run_id=run_id,
                kind="settled" if terminal else "evidence",
                after_seq=cursor,
                cursor=next_cursor,
                snapshot=snapshot,
            )
            yield ServerSentEventMessage(event=envelope.kind, data=envelope.model_dump_json(), id=str(envelope.cursor))
            previous_metadata = metadata
            keepalive_at = loop.time() + _KEEPALIVE_INTERVAL_S
        elif loop.time() >= keepalive_at:
            yield ServerSentEventMessage(comment="keepalive")
            keepalive_at = loop.time() + _KEEPALIVE_INTERVAL_S
        cursor = next_cursor
        if terminal:
            return
        if not pending_evidence:
            await asyncio.sleep(_POLL_INTERVAL_S)


class OrbController(Controller):
    """Discover bounded Run identities and scry each Run's retained evidence."""

    path = "/api/v1/orb"

    @get("/runtime", name="orb:runtime", operation_id="getOrbRuntime", guards=[requires_scopes("altar:read")])
    async def runtime(
        self,
        workflows: NamedDependency[WorkflowRegistry],
        runtime_observations: NamedDependency[RuntimeCatalogue],
    ) -> OrbRuntimeSnapshot:
        """Read bounded topology and non-Run or post-Run activity from selected sources."""
        return await asyncio.to_thread(runtime_observations.snapshot, workflows)

    @get("/runs", name="orb:runs", operation_id="getOrbRuns", guards=[requires_scopes("altar:read")])
    async def runs(
        self,
        state: State,
        cursor: Annotated[str | None, QueryParameter(name="cursor", max_length=512)] = None,
        limit: Annotated[int, QueryParameter(name="limit", ge=1, le=50)] = 20,
    ) -> OrbRunPage:
        """List safe Run metadata across statuses without hydrating retained private content."""
        before = None
        if cursor is not None:
            try:
                decoded = _RunCursor.model_validate_json(base64.b64decode(cursor, altchars=b"-_", validate=True))
                before = decoded.created_at, decoded.run_id
            except (ValueError, binascii.Error) as exc:
                raise ValidationException(detail="Invalid Orb Run catalogue cursor.") from exc
        ledger: RunLedger = state.services.ledger
        records = await ledger.list_run_summaries(before=before, limit=limit + 1)
        page = records[:limit]
        next_cursor = None
        if len(records) > limit:
            last = page[-1]
            key = _RunCursor(created_at=last.created_at, run_id=last.run_id)
            next_cursor = base64.urlsafe_b64encode(key.model_dump_json().encode()).decode("ascii")
        capture = ledger.evidence_capture
        if capture not in {"process_local", "durable_best_effort"}:
            msg = f"Unsupported evidence capture class: {capture}"
            raise ValueError(msg)
        return OrbRunPage(
            snapshot_at=datetime.now(UTC),
            runs=[
                OrbRunSummary(
                    run_id=run.run_id,
                    session_id=run.session_id,
                    workflow_name=run.workflow_name,
                    status=run.status.value,
                    created_at=run.created_at,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    error_present=run.error_present,
                    bridge_path=bridge_context_path(run.session_id, run.workflow_name),
                )
                for run in page
            ],
            next_cursor=next_cursor,
            capture=cast("CaptureClass", capture),
        )

    @get(
        "/runs/{run_id:str}",
        name="orb:run",
        operation_id="getOrbRun",
        guards=[requires_scopes("altar:read")],
        responses={HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False)},
    )
    async def run(
        self,
        request: Request[Any, Any, Any],
        run_id: FromPath[str],
        state: State,
        workflows: NamedDependency[WorkflowRegistry],
        after_seq: Annotated[int, QueryParameter(name="after_seq", ge=-1, le=_MAX_EVIDENCE_CURSOR)] = -1,
        limit: Annotated[int, QueryParameter(name="limit", ge=1, le=500)] = 100,
    ) -> OrbRunSnapshot:
        """Return a bounded selected-Run evidence snapshot."""
        try:
            record = await state.services.ledger.get(run_id)
        except ValueError as exc:
            raise NotFoundException(detail="Unknown run.") from exc
        if record is None:
            raise NotFoundException(detail="Unknown run.")
        snapshot = await build_orb_snapshot(
            state.services.ledger,
            record,
            after_seq=after_seq,
            limit=limit,
            workflow=_workflow_view(record, workflows),
            delegates=getattr(state.services, "delegates", None),
        )
        snapshot.creation = await _creation_summary(state, request, run_id)
        return snapshot

    @get(
        "/runs/{run_id:str}/events",
        name="orb:events",
        operation_id="streamOrbRunEvents",
        guards=[requires_scopes("altar:read")],
        responses={
            HTTP_200_OK: ResponseSpec(
                OrbEventEnvelope,
                generate_examples=False,
                media_type="text/event-stream",
                description="Bounded retained-evidence updates for one selected Run.",
            ),
            HTTP_404_NOT_FOUND: ResponseSpec(FrameworkError, generate_examples=False),
            HTTP_429_TOO_MANY_REQUESTS: ResponseSpec(FrameworkError, generate_examples=False),
        },
    )
    async def events(
        self,
        request: Request[Any, Any, Any],
        run_id: FromPath[str],
        state: State,
        workflows: NamedDependency[WorkflowRegistry],
        run_bus: NamedDependency[InProcessEventBus],
        after_seq: Annotated[int, QueryParameter(name="after_seq", ge=-1, le=_MAX_EVIDENCE_CURSOR)] = -1,
    ) -> ServerSentEvent:
        """Tail retained rows; Last-Event-ID takes precedence on transport reconnect."""
        raw_cursor = request.headers.get("Last-Event-ID")
        if raw_cursor is not None:
            try:
                after_seq = int(raw_cursor)
            except ValueError as exc:
                raise ValidationException(detail="Invalid Orb evidence cursor.") from exc
            if not -1 <= after_seq <= _MAX_EVIDENCE_CURSOR:
                raise ValidationException(detail="Invalid Orb evidence cursor.")
        try:
            run = await state.services.ledger.get(run_id)
        except ValueError as exc:
            raise NotFoundException(detail="Unknown run.") from exc
        if run is None:
            raise NotFoundException(detail="Unknown run.")

        async def read_creation() -> OrbCreationSummary | None:
            return await _creation_summary(state, request, run_id)

        return BoundedRunEventStream(
            _orb_events(
                state.services.ledger,
                run_id,
                workflows,
                after_seq=after_seq,
                delegates=getattr(state.services, "delegates", None),
                read_creation=read_creation,
            ),
            bus=run_bus,
            run_id=run_id,
        )
