"""Bounded selected-Run evidence in ledger order.

Sequence establishes recorded order, not causal edges. Delegated job event
sequences remain separate from the Run sequence. Capture and gaps qualify the
account; a projection does not infer missing history or execute work.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import quote

from lychd.agents.workflows.base import pattern_snapshot_is_valid
from lychd.domain.web.contracts import (
    DelegatedJobEventView,
    DelegatedJobSummary,
    EvidenceGap,
    EvidenceItem,
    OrbBridgePreferenceRoute,
    OrbBridgePreferenceSummary,
    OrbRunSnapshot,
    OrbRunSummary,
    PatternReference,
)
from lychd.domain.webcrawler.feed import WebcrawlerFeedBinding

if TYPE_CHECKING:
    from lychd.domain.cortex.events import RunEvent
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord
    from lychd.domain.delegation.ports import DelegatedAgentCoordinatorPort
    from lychd.domain.web.schemas import LoomView

_CAPTURES = {"process_local", "durable_best_effort"}
_MAX_DELEGATED_JOBS = 32
_MAX_DELEGATED_EVENTS_PER_JOB = 64
_MAX_CONSENT_EVENT_LENGTH = 4096
_CONSENT_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._~-]{0,127}")
type CaptureClass = Literal["process_local", "durable_best_effort"]


def bridge_context_path(session_id: str, workflow_name: str) -> str | None:
    """Do not invent a Bridge Session for the application-only observation Pattern."""
    return None if workflow_name == "scavenger.observe_market" else f"/bridge/{session_id}"


def _application_path(run: RunRecord) -> str | None:
    binding = run.admitted_webcrawler
    if (
        run.source == "scavenger"
        and run.workflow_name == "scavenger.observe_market"
        and type(binding) is WebcrawlerFeedBinding
    ):
        return f"/scavenger?observation={binding.consumer.application_admission_id}"
    return None


def _bridge_preference_view(run: RunRecord) -> OrbBridgePreferenceSummary | None:
    """Project retained selection facts without config reads, probes or reselection."""
    decision = run.admitted_bridge_preference
    if decision is None:
        return None
    if decision.selected_capability_key != run.admitted_capability_key:
        msg = "Retained Bridge preference does not match its admitted capability."
        raise ValueError(msg)
    weights = {route.capability_key: route.weight for route in decision.policy.routes}
    return OrbBridgePreferenceSummary(
        policy_schema_version=decision.policy.schema_version,
        policy_digest=decision.policy_digest,
        batch_started_at=decision.batch_started_at,
        batch_finished_at=decision.batch_finished_at,
        selected_capability_key=decision.selected_capability_key,
        routes=[
            OrbBridgePreferenceRoute(
                capability_key=observation.capability_key,
                weight=weights[observation.capability_key],
                phase=observation.phase.value if observation.phase is not None else None,
                observed_at=observation.observed_at,
                admission_open=observation.admission_open,
                exclusion_code=observation.exclusion_code,
            )
            for observation in decision.observations
        ],
    )


async def build_orb_snapshot(
    ledger: RunLedger,
    run: RunRecord,
    *,
    after_seq: int = -1,
    limit: int = 100,
    workflow: LoomView | None = None,
    delegates: DelegatedAgentCoordinatorPort | None = None,
) -> OrbRunSnapshot:
    """Build one bounded evidence page without explaining absent rows by guesswork."""
    bounded = min(max(limit, 1), 500)
    page = await ledger.list_events(run.run_id, after_seq=after_seq, limit=bounded)
    probe_after = page[-1].seq if page else after_seq
    has_more = bool(await ledger.list_events(run.run_id, after_seq=probe_after, limit=1))
    capture = ledger.evidence_capture
    if capture not in _CAPTURES:
        msg = f"Unsupported evidence capture class: {capture}"
        raise ValueError(msg)
    typed_capture = cast("CaptureClass", capture)
    manifest = run.pattern_manifest
    digest = manifest.get("digest")
    exact = pattern_snapshot_is_valid(manifest)
    pattern_id = str(manifest.get("key") or run.workflow_name)
    revision = str(manifest.get("revision") or "legacy-unversioned")
    ledger_head_seq = (await ledger.next_seq(run.run_id)) - 1
    delegated_job_window = (
        await delegates.jobs_for_run(
            run.run_id,
            limit=_MAX_DELEGATED_JOBS + 1,
            event_limit=_MAX_DELEGATED_EVENTS_PER_JOB + 1,
        )
        if delegates is not None
        else ()
    )
    delegated_jobs = delegated_job_window[-_MAX_DELEGATED_JOBS:]
    known_omissions = ["Token deltas are live Bridge projection and are not retained as structural evidence."]
    if len(delegated_job_window) > len(delegated_jobs):
        known_omissions.append("Older delegated job summaries are outside this bounded Orb snapshot.")
    return OrbRunSnapshot(
        snapshot_at=datetime.now(UTC),
        run=OrbRunSummary(
            run_id=run.run_id,
            session_id=run.session_id,
            status=run.status.value,
            workflow_name=run.workflow_name,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_present=run.error is not None,
            bridge_path=bridge_context_path(run.session_id, run.workflow_name),
            application_path=_application_path(run),
        ),
        pattern=PatternReference(
            pattern_id=pattern_id,
            revision=revision,
            digest=str(digest) if exact else None,
            exact=exact,
            loom_path=(
                f"/loom/{pattern_id}/{revision}?run={quote(run.run_id, safe='')}"
                if exact and workflow is not None
                else None
            ),
        ),
        workflow=workflow,
        bridge_preference=_bridge_preference_view(run),
        capture=typed_capture,
        ledger_head_seq=ledger_head_seq,
        page_end_seq=page[-1].seq if page else None,
        has_more=has_more,
        known_omissions=known_omissions,
        gaps=_gaps(page, after_seq=after_seq),
        evidence=[_item(event, capture=typed_capture) for event in page],
        delegated_jobs=[
            DelegatedJobSummary(
                job_id=job.ref.job_id,
                request_id=job.ref.request_id,
                step_id=job.request.step_id,
                runtime=job.ref.runtime,
                profile=job.ref.profile,
                status=job.status.value,
                output_present=job.result is not None and job.result.output is not None,
                error_present=job.result is not None and job.result.error is not None,
                artifact_count=len(job.result.artifacts) if job.result is not None else 0,
                events_truncated=len(job.events) > _MAX_DELEGATED_EVENTS_PER_JOB,
                events=[
                    DelegatedJobEventView(
                        event_id=event.event_id,
                        seq=event.seq,
                        kind=event.kind.value,
                        status=event.status.value,
                        occurred_at=event.ts,
                    )
                    for event in job.events[-_MAX_DELEGATED_EVENTS_PER_JOB:]
                ],
            )
            for job in delegated_jobs
        ],
        next_after_seq=page[-1].seq if has_more and page else None,
    )


def _gaps(events: list[RunEvent], *, after_seq: int) -> list[EvidenceGap]:
    """Name missing intervals while refusing to infer token omission or persistence failure."""
    gaps: list[EvidenceGap] = []
    expected = after_seq + 1
    for event in events:
        if event.seq > expected:
            gaps.append(EvidenceGap(start_seq=expected, end_seq=event.seq - 1))
        expected = event.seq + 1
    return gaps


def _historical_consent_id(event: RunEvent) -> str | None:
    """Read a bounded historical reference without resolving a current Consent owner."""
    if event.kind.value != "consent" or len(event.data) > _MAX_CONSENT_EVENT_LENGTH:
        return None
    try:
        parsed: object = json.loads(event.data)
    except (json.JSONDecodeError, RecursionError):
        # Legacy events retained the plain id instead of the emitter's JSON object.
        candidate = event.data
    else:
        candidate = cast("dict[str, object]", parsed).get("consent_id") if isinstance(parsed, dict) else None
    return candidate if isinstance(candidate, str) and _CONSENT_REFERENCE.fullmatch(candidate) else None


def _item(event: RunEvent, *, capture: CaptureClass) -> EvidenceItem:
    """Project only allowlisted structural detail; raw prompts/logs never leak here."""
    phase = (
        event.meta.get("phase")
        if event.kind.value in {"node", "dispatch", "transition"}
        else event.data
        if event.kind.value in {"status", "done"}
        else None
    )
    transition_request_id = event.data if event.kind.value == "transition" else event.meta.get("transition_request_id")
    summaries = {
        "status": f"Run progress recorded: {event.data}",
        "node": f"Pattern station {event.data}: {phase or 'observed'}",
        "dispatch": f"Dispatcher granted capability: {event.data}",
        "transition": f"Engine transition request: {event.meta.get('phase', 'observed')}",
        "fragment": "Validated interface fragment recorded.",
        "consent": "Consent wait recorded.",
        "log": f"Log record captured ({event.meta.get('level', 'info')}).",
        "done": f"Run terminal status recorded: {event.data}",
        "resync": "Live projection required a snapshot replacement.",
    }
    return EvidenceItem(
        event_id=event.event_id,
        seq=event.seq,
        kind=event.kind.value,
        occurred_at=event.ts,
        summary=summaries.get(event.kind.value, "Structural event recorded."),
        subject_key=event.data if event.kind.value in {"node", "dispatch"} else None,
        phase=phase,
        occurrence_id=event.meta.get("occurrence_id"),
        transition_request_id=transition_request_id,
        nexus_path=f"/nexus?transition={transition_request_id}" if transition_request_id else None,
        animator_name=event.meta.get("animator") if event.kind.value == "dispatch" else None,
        capability_family=event.meta.get("family") if event.kind.value == "dispatch" else None,
        model_id=event.meta.get("model_id") if event.kind.value == "dispatch" else None,
        grant_id=event.meta.get("grant_id") if event.kind.value == "dispatch" else None,
        consent_id=_historical_consent_id(event),
        capture=capture,
    )
