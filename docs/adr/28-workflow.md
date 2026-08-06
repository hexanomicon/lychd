---
title: 28. Workflow
icon: material/tournament
---

# :material-tournament: 28. Workflow

!!! abstract "Context"
    Graph carries typed movement, not the answer to which graph serves an Intent, who owns its
    revision, or which score remains valid through pause and repair. Weaver supplies that logical
    jurisdiction without absorbing authority, execution, or application purpose.

[Weaver](../sepulcher/extensions/weaver/index.md) keeps the score through motion, pause, and return.

## Decision

Weaver is LychD's single logical workflow jurisdiction; Pattern is immutable executable score.

| Name | Office |
| --- | --- |
| Composition | Operator-visible purpose, records, effects, policies, projections, Pattern catalogue |
| Pattern | One versioned executable score owned by a Composition |
| Invocation | One admitted performance of exact Pattern revision |
| Run | Durable execution/ledger identity |
| Graph | Typed state topology |
| Loom | Read-only declared-score projection |
| Suite | Versioned coordination of separate Compositions |

Weaver owns validation, registration, routing, logical dependencies, Gates, schedules/overlap,
revision continuity, and contribution. Composition owns judgment; IAM/Ward/HitL authority;
Dispatcher capability; Orchestrator readiness; Workers delivery/retry; Phylactery/Graph stores and
checkpoints; Riddle evaluation; Soulforge promotion.

## Current material

Fixed source registry has bridge_chat@1 (Bridge conversation, context, Agent turn, optional consent
Gate, reply) and delegated_rite@1 (/delegate reference job, Durable Stasis, result/reply). The
latter proves no external coding-agent/Tomb plane. One boot-composed catalogue is shared by
admission, workers, Bridge, Loom, and Orb. It freezes after construction, rejects duplicate exact
revisions, requires an explicit active revision when alternatives exist, permits registered
revisions or whole names to remain retained but inactive, requires explicit non-default route
precedence whenever multiple names are active, and has one active default. Run commits selected
name and manifest; resume never routes Intent again. Loom exposes active/default/route-rank metadata
without making retained revisions admissible.

This is Core registry, not Extension contribution, Composition registry, Suite executor, scheduler,
editor, or durable Pattern publication store. State separately owns v1 adapter, delegation, stasis,
and Loom.

## Pattern identity

Manifest has schema, URL-safe key/revision, reviewed implementation revision, checkpoint schema,
a declared entry station, unique semantic station key/label/kind, permitted declared-endpoint edges, and deterministic
SHA-256 digest. Executable
stations map one-to-one with Python nodes; construction rejects missing/duplicate/unknown/mismatch,
duplicate semantic edges, Gate or delegate marker drift, dynamic `BaseNode` returns whose topology
cannot be proved, and any semantic transition set that differs from the public Graph node
definitions. The declared entry must name the actual executable start node and participates in the
digest. Exactly one terminal is required. Gate loops remain explicit Graph edges; a delegate
station additionally declares its durable same-station re-entry edge. Gate/delegate derives Durable
Stasis. The opaque implementation revision is a human-reviewed compatibility closure, not a hash
of Python bytes: behavior that would invalidate parked state or replay must bump it or the Pattern
revision. The manifest fingerprints source-adjacent declaration rather than compiling all semantics.

Admission persists snapshot/digest; execution/resume requires exact current registered equality or
fails pinned Pattern unavailable. Multiple exact source-registered revisions may coexist: new
admission uses only an active revision while an older Run resolves its retained pinned revision
directly. Removing old executable code still makes that revision unavailable. Compatibility
Automatic source-code drift detection, durable publication, drain, and migration remain future work.

## Admission and ownership

Weaver selects once from admitted Intent; Run ledger owns identity/status:

1. validate/select Pattern;
2. atomically create Run with exact manifest and its initial durable delivery;
3. retain caller initiating record while that delivery is held, then release it;
4. publish the exact job key; relay it later when the broker is unavailable.

The Run delivery outbox is transactional with Run truth, not with the external broker. Workers and
the relay publish, claim, and settle physical hops; Graph checkpoints; Weaver neither writes the
outbox directly nor operates containers. Weaver owns scheduling identity, eligibility, overlap,
and miss semantics; a separate clock/relay mechanism detects due work and publishes only the
ordinary delivery that Weaver has admitted. Weaver does not become that timer or broker.

## Pattern contribution

A publishable revision declares identity/revision/owner/provenance/support/parentage; typed
input/output/state/error/non-completion; topology and cancellation; capability/tool/plane/budget/
wait; Sigil/effect/privacy/egress/consent and secret-free durable state; checkpoint/idempotency/
receipt/compatibility/migration/drain/refusal; Loom metadata; and serialization/failure/recovery
evidence. Assembly uses explicitly selected shaped store, never package scanning; rejects duplicate
identity, ambiguous routes, unknown adapters, unreachable station, unsafe cycle, unserializable
state, missing continuity, forbidden effect, then freezes generation. Workflow dataclass is internal
pre-v1, not ABI. Creation/Assimilation/Extension law governs candidate publication; source/model/
Loom draft cannot publish without validation, review, evidence, immutable revision.

## Gates, effects, and Stasis

| Boundary | Rule |
| --- | --- |
| Live Stasis | Resident process waits and resumes itself. |
| Durable Stasis | Declared Gate/delegate exits after checkpoint; re-admission mandatory. |
| Terminal | Run truth commits before checkpoint cleanup. |

Checkpoint is Graph state, never process image or retroactive replay safety. Effect station declares
idempotency, receipt, cancellation, compensation/refusal, and illegal-repeat boundary. Consent
appears only where HitL/effect policy demands; a verdict covers exact effect, not Pattern promotion
or downstream authority. Archive, Ward, Dispatcher, provider, execution retain policy even when
coordinated.

A protected Portal score joins labels, locally transforms, may ask local Privacy Agent, verifies
TransformationReceipt, creates Privacy Cut, gets exact EgressDecision, calls Portal, quarantines
return. Censor/Agent proposes only. Context owns cut; Security owns declassification.

## Parallelism and delegation

Built-ins are serial BaseNode. Parallel map/fork/join/reduce needs branch identity, declared
reduction, bounded concurrency, cancellation, Gate behavior, completed-effect receipts, and
crash-recovery on both join sides. A bounded durability adapter cannot replace ledger, Ward,
Dispatcher, Orchestrator, HitL, or revision. Delegated station declares request/result,
containment, budget, timeout, cancellation, artifact boundary, downstream use; provider adapter
invokes foreign runtime, never embedded CLI/credential/private graph.

## Compositions, Suites, and schedules

Portfolio membership marks an accepted **Native Reference Composition**: a first-party supported
application contract and worked example. It does not prove executable delivery; each Composition
leaf states its current material against tracked evidence, while [State of Work](../state-of-the-work.md)
keeps the shared whole-system envelope. Suite may coordinate separate Compositions
with typed ArtifactRef/Intent handoffs, pinned revisions/correlation/ceilings/dependencies/partial
completion, never merge ownership/secrets/Sigils/HitL/domain judgment. Suite execution is Designed:
child identity/revision/closure/fan-out/join/budget/cancel/stasis/retry/effect/compensation/partial
must be defined first.

A Schedule makes one durable, deduplicated **Occurrence** for each firing and enters ordinary
admission. Weaver owns calendar/event meaning, service class, temporal eligibility,
priority/overlap/coalescing/revision, and the decision to admit or settle a missed firing. Workers
deliver and retry exact admitted hops; Dispatcher resolves capability; Orchestrator owns readiness.
A timer never calls a Graph node, model, Animator, or container.

Three semantic service classes govern admission; they are not broker queues:

| Service class | Contract |
| --- | --- |
| `foreground` | Eligible now and latency-sensitive. It receives preference, not a promise of immediate start or unsafe preemption. |
| `deadline_windowed` | Eligible no earlier than `not_before` and governed by `latest_start_at` plus optional `finish_by`; expiry settles explicitly rather than running silently late. |
| `spare_capacity` | No completion-time promise. Scarce-resource work requires a proved bounded yield/containment contract or an operator-approved quiet window. |

Class is orthogonal to doctrine priority and physical queue. Continuous foreground demand must not
silently starve a declared deadline; approaching deadline feasibility may outrank ordinary latency
preference under the pinned policy. `spare_capacity` defaults to already-WARM/NO_OP-compatible
capability and may not trigger a disruptive hard swap merely to keep iron busy.

Cron is one trigger grammar, not a service class. A calendar Schedule pins its revision, Pattern
revision, IANA time zone, ambiguous/nonexistent civil-time policy, overlap and misfire policy,
bounded catch-up, budgets, and authority owner. Jitter changes eligibility, never Occurrence
identity. An overlap remains live while its prior Invocation is nonterminal, including Stasis;
coalescing requires a Pattern-owned typed merge and preserves every member Occurrence.

Canonical **Occurrence** means the schedule or external-trigger firing before Invocation admission.
The delivered Graph runtime's `occurrence_id` field is a legacy name for a station-attempt
correlation; it is not this durable trigger identity. No Occurrence store, timer, eligibility
engine, service-class persistence, safe preemption, or periodic workflow scheduler exists.

## Returning findings

Riddle returns SuiteFindingSet@1, AttributionCandidate@1, InvalidationSet@1, CorrectionRequest@1
as evidence, not reverse edges. Weaver admits a Correction Request only as new forward Invocation
under validation/budget/authority/consent; it cannot resume arbitrary old station, mutate artifact,
inherit consumer authority, or turn recurrence into training. Repair starts from smallest supported
cut; reuse requires full input/evaluation closure; unresolved attribution/exhausted budget terminates honestly.

## Loom projection and drafting

[Loom](../divination/altar/loom.md) reads fixed immutable manifest: stations, edges, Gate/delegate,
revision, implementation revision, checkpoint schema, digest. Mermaid/canvas are views. Charcoal remains inert until canonical
declarative Pattern has typed ports/state/effects/authority/termination/continuity. Drawn grouping
does not nest Pattern or execute Suite. Publication alone makes new immutable revision; Invocations
stay pinned. Model prose, browser gesture, renderer state are not authority.

## Rejected alternatives

### Unversioned procedural chains

Functions suit a bounded station, not long-lived identity with parking, projection, contribution, or revision continuity.

### A second application scheduler

It fragments admission, priority, recovery, and inspection; applications contribute to Weaver.

### Visual source as executable law

Renderer state cannot state all type, authority, effect, and recovery invariants; Loom projects and may draft candidates.

## Consequences

!!! success "Accepted"
    - Exact Pattern identity, waits, contributions, Suites, schedules, and Loom share one future admission law.
    - Ownership stays split and immutable revision prevents substitution.

!!! failure "Cost"
    - Automatic compatibility proof, durable Pattern publication, scheduling, parallel durability, and editing are separate programs.
    - Construction proves declared Graph topology only; effect, recovery, and compatibility semantics still need their own evidence.

## Acceptance evidence

Registry, route-once, manifest, serialization, Loom, admission, claim, consent, delegation, and
recovery tests prove the floor. Each future surface needs focused ambiguity, compatibility, failure,
cancellation, replay, and projection evidence before State promotion.
