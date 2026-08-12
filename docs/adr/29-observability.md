---
title: 29. Observability
icon: material/telescope
---

# :material-telescope: 29. Observability

!!! abstract "Context and Problem Statement"
    Runs, consent, dispatch, delegated work, runtime transition, and failure need evidence. Logs
    and telemetry cannot authorize or settle them; a shared id supplies correlation, not causality
    or completeness. This Covenant defines evidence law, Oculus, and Orb.

## Requirements

- Acting offices retain state/effect receipts; Oculus owns observations and rebuildable projections.
- Every record identifies producer, subject, id, ordering domain, capture class; loss and uncertainty are explicit.
- Content is allowlisted; secrets prohibited. Signals retain distinct authority and retention.
- First Orb query is bounded authorized one-Run view. Eyes are one-way redacted exports without LychD authority.

## Considered Options

| Option | Result |
| --- | --- |
| Mandatory metrics/trace stack | Rejected: adds retention/control without evidence ownership. |
| Generic JSONB for all signal/body | Rejected: collapses records, telemetry, privacy, schemas. |
| Native contract, optional Eyes | Selected: LychD vocabulary remains authoritative and viewers replaceable. |

## Decision Outcome

[Oculus](../sepulcher/extensions/oculus.md) is designed native evidence domain; Orb is its Altar
instrument and scrying its use. Phoenix, Logfire, OpenTelemetry collector, or another viewer may
be an external Eye; names never change ownership.

!!! warning "Exact implementation state"
    Structured logging and bounded Orb exist at State scopes. Native Oculus is Designed: telemetry
    adapter is dormant, with no ingestion, trace/metric store, retention, health query,
    cross-process bus, resource telemetry, or multi-Run query. Optional Phoenix only contributes
    service; application export is unproved.

### 1. Evidence Ownership and Correlation

Evidence classes are authoritative record (its responsible transition/effect office), bounded
observation (producer/subject/method/times/freshness/limits), derivation (parents/algorithm/
uncertainty/invalidation), and interpretation/verdict (named criteria, e.g. Riddle). RunLedger owns
Run status; consent, grants, jobs, host transitions, artifacts, and evaluations retain theirs.
Step/RunEvent may report, never overwrite.

RunEvent identity is run_id plus UUID event_id; seq is monotonic per-Run emission order, ts producer
time. Live channel makes contiguous in-process seq and one terminal; non-token events tee to Step
ledger in order but best-effort append may gap; PostgreSQL enforces (run_id, seq) where used. Token
deltas are never Step evidence. Seq orders one producer, timestamps no global order. Cross-office
relations name typed Pattern revision, occurrence, grant, job, or transition id. Shared id/time is
correlation only; trace context never authenticates or authorizes.

### 2. Native Service and External Eyes

| Signal | Current shape | Authority |
| --- | --- | --- |
| Run events | in-process, 256 replay, best-effort non-token Step tee | observation |
| Logs | Structlog/stdlib human or JSON stderr | diagnostic, not audit |
| Traces | dormant Logfire/OTel; focused test disables headers/bodies | no ingest/export/retention/read |
| Metrics | no producer/registry/store/query | Designed |
| Orb | bounded selected-Run projection | read-only |

Future Oculus exposes typed event/query contracts; clients do not query tables. Eye sees allowlisted
export and has no canonical read-back. Phoenix legacy name = oculus compatibility cannot make it
native Oculus.

### 3. Interior Evidence Without Mind Reading

Oculus may hold first-person testimony, operated telemetry, declared interpretation. None is hidden
chain-of-thought: progress is testimony, tool/provider span observation, scored explanation
versioned interpretation. Prompt/completion, retrieved context, tool bodies, provider exchange,
media, credentials, and identity data are absent unless current policy admits; useful structural
view and missing-evidence result must remain possible.

### 4. Delegated-Agent Evidence

Observe delegated runtimes only at admitted adapter boundary. LychD job state/policy/settlement/
artifacts/adoption differs from provider-reported usage/protocol; neither reveals planner,
subagent tree, or private reasoning. Orb exposes at most 32 newest job summaries and 64 newest
lifecycle events/job, state/result-or-artifact presence but no prompt/output/private error, with
truncation explicit. Its bounded read asks the job store for one extra job and event as omission
sentinels; database `LIMIT`s select those newest suffixes before per-job event hydration, then
restore creation/sequence order for projection. Raw future protocol artifact is untrusted bounded
input; it cannot settle a job, authorize an effect, mutate Graph, or become training data by
default.

### 5. Orb Read Models

[Orb](../divination/altar/orb.md) reads one Run by direct URL: retained bounded non-token events,
separate ledger-head/page bounds, seq gaps, capture class process_local/durable_best_effort,
omissions, and Pattern link only if pinned manifest validates. LOG is summarized without raw
message; Nexus links only recorded transition ids. No run list, live tail, graph view, native Oculus
model, cross-process completeness, artifact custody, annotation, or multi-Run field. SSE RESYNC
instructs client to replace projection from snapshot; it is not browser-restored history.
Viewing/filtering/layout never changes Run. Annotation would be separate authorized record, never
retry/approval/cancel/publication/transition.

### 6. The Physical Body and Pulse

No Resource Snapshot exists for VRAM, thermal, power, ownership, pressure. Future node measurement
carries units, method, age, errors, freshness; failed/stale means unknown, never free. Orchestrator
consumes fresh truth under admission; Oculus may explain it. Rates/percentiles/trends are derivation,
not grants/reservations/health verdicts/promotion thresholds.

### 7. Privacy, Retention, and Failure

Each class declares purpose/fields/classification/visibility/retention/export. Redact before
serialization with policy version; Eye applies second filter; reject secret material. Privatization
telemetry stores opaque decision/receipt ids, `EvidenceDigest@1` keyed projections,
categories/counts, policy version, failure stage, and gaps—never canonical raw payload/source
digests, sensitive spans, or pseudonym reversal maps. Plain digests of low-entropy or stable private
values are linkage oracles, not anonymization. Security owns the local-only decision and keyed
evidence projection; Context owns receipts.

Current Orb allowlists structural fields and omits raw prompts, output, private errors, LOG
messages. Shared logging has no general redaction/storage/rotation/retention/correlation contract;
HTTP instrumentation disabling blanket body/header capture is not whole proof. A conforming Oculus
bounds producer/subscriber queues and batching/flush/shutdown. Today each live Run subscriber and
its replay window are bounded at 256 events; an overflow collapses pending deltas to an explicit
snapshot-resync boundary rather than applying producer backpressure. Persist failure logs and may
gap Step.
Correctness records remain acting-office transactions: lost telemetry harms diagnosis, never proves success.

## Consequences

!!! success "Accepted"
    - Rebuildable correlated observations leave authoritative records with their offices.
    - Capture class, gap, freshness, redaction, and uncertainty are evidence.
    - Eyes are replaceable.

!!! failure "Cost"
    - Oculus requires ingest, retention, query, migration, health, backpressure.
    - Partial-order correlation and privacy boundary cost more than arbitrary spans.
