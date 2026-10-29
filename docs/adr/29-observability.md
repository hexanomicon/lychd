---
title: 29. Observability
icon: material/telescope
---

# :material-telescope: 29. Observability

A Run can finish while an observer misses an event. A provider can report success while the
owning ledger still has an unresolved effect. Observability must let a reader distinguish those
situations without making a log, timestamp, or convincing picture authoritative.

## Requirements

Every record identifies its producer, subject, identity, ordering domain, and capture class.
Missing material, stale observations, and uncertain outcomes remain visible. Content is
allowlisted and secrets are prohibited. The office performing an effect keeps its authoritative
record; observations and rebuildable projections retain their own purpose and retention.

The first Orb query is a bounded, authorized view of one Run. An external viewer receives only
redacted exports and gains no LychD authority.

## Considered Options

| Option | Result |
| --- | --- |
| Require an external metrics and tracing stack | Rejected: deployment and retention would precede a clear account of evidence ownership. |
| Put every signal and body in generic JSONB | Rejected: authoritative records, diagnostics, privacy, and schema boundaries would become indistinguishable. |
| Keep a native evidence contract and optional external Eyes | Selected: tools may change while LychD retains its own record meanings. |

## Decision Outcome

[Oculus](../sepulcher/extensions/oculus.md) is the designed native evidence Domain. Its Altar
instrument is **Orb**, and using that instrument is **scrying**. An external **[Eye](../lexicon/iron-tongue.md#e)**
may be Phoenix, Logfire, an OpenTelemetry collector, or another viewer. Each supplies a way to
inspect evidence without becoming a second source of truth.

Structured logging and the bounded Orb have current repository evidence. Native Oculus has no
ingestion or telemetry adapter, trace/metric store, retention, health query, cross-process bus,
resource telemetry, or multi-Run query. The optional Phoenix contribution supplies a service;
application trace export remains unproved. [State of Work](../state-of-the-work.md#altar-and-observability)
owns those delivery boundaries.

### 1. Evidence Ownership and Correlation

| Evidence class | What the reader can establish |
| --- | --- |
| Authoritative record | The responsible office committed this transition or effect state. |
| Bounded observation | This producer observed this subject by a named method, at stated times, with explicit freshness and limits. |
| Derivation | A named algorithm used these parents; uncertainty and invalidation remain attributable. |
| Interpretation or verdict | An evaluator applied declared criteria, as in Drift. |

RunLedger owns Run status. Consent, grants, jobs, host transitions, artifacts, and evaluations each
keep their own records. Step and RunEvent observations may describe that truth but cannot
supersede it.

A RunEvent names `run_id`, UUID `event_id`, monotonic per-Run `seq`, and producer timestamp `ts`.
The live channel emits a contiguous process-local sequence and one terminal event. Non-token
events tee to the Step ledger in order, but append is best-effort and may leave gaps; PostgreSQL
enforces `(run_id, seq)` where that store is used. Token deltas never become Step evidence.

Sequence orders one producer. Timestamps do not establish a global order, and a shared identifier
proves correlation rather than causality or completeness. Cross-office relations name the exact
Pattern revision, trigger Occurrence, station attempt, grant, job, or transition. A trigger
Occurrence and a station attempt remain distinct identities; ADR 28 owns their relationship.
Trace context never authenticates a caller or authorizes an effect.

### 2. Native Service and External Eyes

| Signal | Current shape | Authority |
| --- | --- | --- |
| Run events | Process-local channel, 256-event replay, best-effort non-token Step tee | Observation |
| Logs | Structlog/stdlib human or JSON stderr | Diagnostic |
| Traces | No producer or export adapter | No native ingestion, export, retention, or read contract |
| Metrics | No producer, registry, store, or query | Designed |
| Orb | Bounded Run catalogue, graph lenses, and retained-evidence feeds | Read-only |

Future Oculus exposes typed query and event ports; clients do not inspect its tables directly.
An Eye receives a one-way allowlisted export, with no canonical read-back. The legacy Phoenix
service spelling `oculus` is a compatibility name and cannot make that service native Oculus.

### 3. Interior Evidence Without Mind Reading

Interior evidence needs an attributed source and a declared kind. Progress text is first-person
testimony, a tool/provider span is an operated observation, and a scored explanation is a
versioned interpretation. These remain separate sources; none exposes hidden chain-of-thought.

Prompts and completions, retrieved Context, tool bodies, provider exchanges, media, credentials,
and identity data remain absent unless the applicable policy admits them. A useful structural
view must remain possible without that content. It must also be able to say that the evidence
needed for a stronger conclusion was not captured.

### 4. Delegated-Agent Evidence

For delegated work, observation stops at the admitted adapter. LychD records admission, policy,
settlement, artifacts, and adoption. Usage and protocol messages reported by the provider stay
attributed to that provider. Neither source reveals the foreign planner, subagent tree, or
private reasoning.

Orb displays at most **32 newest job summaries** and **64 newest lifecycle events per job**. It
shows state and result-or-artifact presence while withholding prompts, output, and private errors.
The store queries one extra job and event as omission sentinels. Database `LIMIT`s select the
newest suffixes before per-job event hydration; projection then restores creation/sequence order
and marks truncation explicitly.

Any later raw protocol artifact remains bounded untrusted input. It cannot settle the job,
authorize an effect, mutate Graph, or become training material by default.

### 5. Orb Read Models

[Orb](../divination/altar/orb.md) discovers Runs through a bounded metadata catalogue and opens
one Run by direct URL. It keeps ledger-head and page bounds separate, reports sequence gaps and
omissions, and names capture as `process_local` or
`durable_best_effort`. A Pattern link and declared workflow graph require a valid pinned manifest
equal to the registered revision; a Nexus link requires a recorded transition identity.
LOG events are summarized without their raw message.

The parallel field retains at most three live lenses of 100 records each. Its graph folds supplied
Run, station/subject, occurrence, and record identities; counts describe loaded membership.
Retained-evidence SSE polls the owning ledger in bounded batches, preserves explicit gaps, and
resets an invalid future cursor through an authoritative snapshot. A ledger-terminal settlement
drains currently retained evidence without claiming completeness. This feed is distinct from the
process-local Bridge token channel. [Frontend](15-frontend.md#snapshots-streams-and-recovery)
owns its browser recovery and lifecycle contract.

Current Orb has no native Oculus model, nested subworkflow identity, cross-process completeness,
artifact custody, or annotation. A reset requests snapshot replacement; it does not recover history
inside the browser.

Viewing, filtering, and layout never change a Run. A future annotation is a separately authorized
record, not an implicit retry, approval, cancellation, publication, or transition.

### Exact-Run Archive selection explanation

A separate Archive-authorized read may join one retained Run to its exact expected recall request.
It requires the supported pinned Pattern and complete admitted/current Archive binding, then
current local metadata-inspection authority; `altar:read` alone is insufficient. The bounded view
contains historical receipt identities, selected source revisions, scores, character/result bounds
and recorded budget omissions, with no prompt, source body, answer or provider payload.

The capture class is a matching retained request. Public recall accepts caller-supplied identities,
so even an exactly matching receipt may precede workflow execution. The view cannot claim actual
consumption, provider transmission, complete Context, or restored process-local assembly. Missing,
unsupported, denied, failed and successfully empty selections remain distinguishable. Later source
revocation does not rewrite the old selection or grant access to its former content. This read
neither appends structural evidence nor changes a Run; Archive owns its retained metadata.

### 6. The Physical Body and Pulse

A future Resource Snapshot records the node, units, measurement method, age, errors, and freshness
of VRAM, thermal, power, ownership, and pressure observations. No such snapshot exists today.
Stale or failed measurement means unknown capacity, never free capacity.

Orchestrator may consume fresh physical truth during admission; Oculus can help explain it.
Rates, percentiles, and trends are derived observations. They confer no grant, reservation,
health verdict, or promotion threshold.

### 7. Privacy, Retention, and Failure

Each evidence class declares its purpose, fields, classification, visibility, retention, and export
policy. Redaction occurs before serialization under a named policy version; an Eye applies another
filter. Secret material is rejected.

Privatization telemetry may retain opaque decision/receipt identities, keyed
`EvidenceDigest@1` projections, categories and counts, policy version, failure stage, and gaps.
It carries no canonical raw payload/source digest, sensitive span, or pseudonym reversal map.
Plain hashes of stable or low-entropy private values allow linkage; hashing alone does not
anonymize them. Security owns local-only decisions and keyed evidence projections; Context owns
transformation receipts.

Current Orb allowlists structural fields and omits raw prompts, output, private errors, and LOG
messages. Shared logging has no general redaction, storage, rotation, retention, or correlation
contract. Disabling blanket HTTP body/header capture establishes only that instrumentation choice.

A conforming Oculus must bound producer/subscriber queues, batching, flush, and shutdown. Today's
live Run replay and each subscriber queue are bounded at **256 events**. On overflow, pending
deltas collapse to an explicit snapshot-resync boundary; the channel does not apply producer
backpressure. Failed Step persistence is logged and may leave a gap. A lost observation impairs
diagnosis; authoritative correctness records still commit through their owning transactions.

## Consequences

The evidence contract lets a reader distinguish an authoritative event, an observation, a
derivation, and someone's conclusion. Capture class, gaps, freshness, and uncertainty remain
visible parts of that evidence. An external Eye can be replaced without replacing those meanings.

The cost is explicit ingestion, retention, query, migration, health, and queue work. Privacy and
partial-order correlation require more care than arbitrary tracing spans, and some questions must
remain unanswered when their evidence was never retained.
