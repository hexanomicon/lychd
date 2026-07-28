"""Pure, honest selected-Run evidence projections for the Orb."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import quote

from lychd.agents.workflows.base import pattern_snapshot_is_valid
from lychd.domain.web.contracts import (
    EvidenceGap,
    EvidenceItem,
    OrbRunSnapshot,
    OrbRunSummary,
    PatternReference,
)

if TYPE_CHECKING:
    from lychd.domain.cortex.events import RunEvent
    from lychd.domain.cortex.ledger import RunLedger
    from lychd.domain.cortex.runs import RunRecord

_CAPTURES = {"process_local", "durable_best_effort"}
type CaptureClass = Literal["process_local", "durable_best_effort"]


async def build_orb_snapshot(
    ledger: RunLedger,
    run: RunRecord,
    *,
    after_seq: int = -1,
    limit: int = 100,
    loom_available: bool = False,
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
            bridge_path=f"/bridge/{run.session_id}",
        ),
        pattern=PatternReference(
            pattern_id=pattern_id,
            revision=revision,
            digest=str(digest) if exact else None,
            exact=exact,
            loom_path=(
                f"/loom/{pattern_id}/{revision}?run={quote(run.run_id, safe='')}"
                if exact and loom_available
                else None
            ),
        ),
        capture=typed_capture,
        ledger_head_seq=ledger_head_seq,
        page_end_seq=page[-1].seq if page else None,
        has_more=has_more,
        known_omissions=["Token deltas are live Bridge projection and are not retained as structural evidence."],
        gaps=_gaps(page, after_seq=after_seq),
        evidence=[_item(event, capture=typed_capture) for event in page],
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
        capture=capture,
    )
