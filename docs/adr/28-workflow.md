---
title: 28. Workflow
icon: material/tournament
---

# :material-tournament: 28. Workflow

!!! abstract "Context"
    Graph carries typed movement, not the answer to which graph serves an Intent, who owns its
    revision, or which score remains valid through pause and repair. Spellweaver supplies that
    logical jurisdiction without absorbing authority, execution, or application purpose.

[Spellweaver](../sepulcher/extensions/weaver/index.md) keeps the score through motion, pause, and return.

## Decision

**Spellweaver** is LychD's single logical workflow jurisdiction; `Weaver` remains its short,
code-facing name and the compatibility spelling used by existing paths.

| Name | Office |
| --- | --- |
| Composition | Operator-visible purpose, records, effects, policies, projections, Pattern catalogue |
| Pattern | One named executable-score lineage owned by a Composition |
| Scroll | The mythic name for one immutable Pattern revision: the whole score, not one node |
| Spell | One independently named semantic action contract: what a station may do |
| Spell placement | One Scroll-local station that invokes an exact Spell contract |
| Invocation | One admitted bounded world—the Circle—in which identity, Context, authority, and consequence meet |
| Casting | The performance of one exact Scroll within that Invocation |
| Run | Durable execution/ledger identity |
| Graph | Typed state topology |
| Loom | Read-only declared-score projection |
| Suite | Versioned coordination of separate Compositions |

Spellweaver owns validation, registration, routing, logical dependencies, Gates, schedules/overlap,
revision continuity, and contribution. Composition owns judgment; IAM/Ward/HitL authority;
Dispatcher capability; Orchestrator readiness; Workers delivery/retry; Phylactery/Graph stores and
checkpoints; Riddle evaluation; Soulforge promotion.

## Spells, Scrolls, and casting

The mythic grammar is exact: a **Scroll** is one immutable workflow score; each semantic station is
a placement of a **Spell**; a **casting** performs that Scroll inside one admitted Invocation and
its [Circle](../divination/altar/circle.md). These names do not create duplicate schemas or let
imagery replace engineering identity.

A Spell is the smallest independently named, discoverable, teachable action at the workflow
boundary: ask an Agent, anonymize material, await consent, write an artifact, delegate work, or
send through a Portal. “Smallest” is semantic, not mechanical. Its implementation may involve
model calls, tools, syscalls, retries, or adapter machinery. An internal operation becomes another
Spell placement only when the Scroll must independently type, route, authorize, checkpoint,
retry, inspect, or recover it.

The **Spell contract** defines typed input, output, errors and non-completion; semantic
requirements; authority and effect demands; and continuity obligations. A provider-owned **Spell
implementation** claims to realize one exact contract revision and has separate code, package,
adapter, provenance, checkpoint, and evidence identity. A Spell is not an uppercase Dispatcher
`Capability`, tool, Agent, credential, grant, Python type, or live handle. Its name requests a
bounded action and grants no power to perform it.

A Scroll declares its placements, edges, entry, termination, configuration, budgets, requirements,
and authority/effect/privacy ceilings; receiving the artifact conveys none of that authority. Each
placement names an exact authority-qualified Spell contract revision and digest. A receiver-owned,
immutable **Resolution Lock** binds it to an exact local implementation, adapter, code/artifact,
Agent/Posture requirement, tool/effect contracts, checkpoint codec, and registry generation where
needed. The Run pins both the Scroll snapshot and Resolution Lock digest. Contract identity,
implementation identity, and placement identity never substitute for one another.

A one-Spell Scroll is valid. A larger workflow or batch is simply a Scroll with several placements;
the same Spell may appear more than once under distinct placement identities and bindings. This
uses the existing workflow identity rather than inventing another batch object.

Admission distinguishes parseable, contract-conformant, locally bound, available, authorized, and
admissible. A claim at one level proves none of the later levels. Unknown, unavailable,
incompatible, revoked, or unauthorized placements block casting; no similar name, version range,
provider, or newer revision may be substituted. A future Loom may render an **inert resolution
report** with grey placements and redacted reasons, but such a view is not an executable Graph.

The current fixed manifests expose station key, label, kind, one workflow-wide implementation
closure, and edges, with each executable station bound one-to-one to a Python Graph node. A current
station therefore behaves like a legacy inline Spell placement plus implementation binding, but it
has no independent Spell identity. The runtime does not ship a Spell catalogue, Resolution Lock,
portable Scroll ABI, remote compatibility negotiation, teaching surface, or package contribution
store.

Policy for an unknown Spell may choose only among refusal, a request for an attributed teaching
candidate, or use of an already admitted exact contract with an exact local binding. A teaching
candidate is hostile foreign craft: it enters [Assimilation](35-assimilation.md), not the live
registry. Smith may re-express it locally, but Spellweaver validates and the target owner publishes
it only after evidence and authorization. Publication creates new catalogue truth and a later
casting; it never mutates or resumes the refused Invocation under changed law.

## Portable declaration

Portable `SpellContract`, `Scroll`, and `TeachingBundle` artifacts use versioned, restricted UTF-8
JSON. Hash and signature inputs use the pinned
[JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785.html); duplicate keys,
non-interoperable numeric values, unknown unnamespaced fields, YAML tags/aliases/merge semantics,
and source-language object construction are refused. Semantically unordered arrays define and
verify their own deterministic order. Identity includes schema reference, authority-qualified name,
exact revision, algorithm-tagged digest, and domain-separated artifact kind.

YAML may serve as a friendly Loom or repository authoring projection, but it must compile through
the same typed validator into canonical JSON. YAML text is never portable identity and is never the
signed object. A different wire encoding requires a separately versioned adapter and conformance
corpus; it cannot claim byte identity with JSON.

`core` contract namespaces are reserved to their canonical owner. Built-in, Crypt, operator, and
foreign publishers retain distinct authority-qualified identities. A private implementation may
prove conformance to a public contract without acquiring its publisher's name. Learned material is
private by default and preserves `derived_from` or `implements` lineage; promotion cannot squat a
canonical namespace.

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
is proved only by exact registered equality and the reviewed closure. Automatic source-code drift
detection, durable publication, drain, and migration remain future work.

## Migration without rewritten history

Portable Spells and Scrolls arrive additively:

1. Freeze current Pattern schema v2 digests and persisted-Run fixtures.
2. Introduce Spell-contract, implementation, placement, and Resolution-Lock types without changing
   v2 snapshots.
3. Adapt each v2 station at assembly as a Scroll-private `legacy_inline` Spell identity; it is
   neither reusable nor portable.
4. Add separate provider-attributed Spell-contract, implementation, and Scroll stores, then build
   one immutable registry generation shared by admission, workers, Bridge, Loom, and Orb.
5. Introduce a new Scroll schema with exact Spell references and a Resolution Lock while dispatching
   v2 and the new schema through separate validators and resolvers.
6. Publish built-ins only as new revisions. Never rewrite `bridge_chat@1` or `delegated_rite@1`, and
   retain their executable closures until pinned Runs drain or settle honestly unavailable.

No compatibility shim may present a v2 Python node as a canonical public Spell merely because its
label resembles one.

## Admission and ownership

Spellweaver selects once from admitted Intent; Run ledger owns identity/status:

1. validate/select Pattern;
2. atomically create Run with exact manifest and its initial durable delivery;
3. retain caller initiating record while that delivery is held, then release it;
4. publish the exact job key; relay it later when the broker is unavailable.

The Run delivery outbox is transactional with Run truth, not with the external broker. Workers and
the relay publish, claim, and settle physical hops; Graph checkpoints; Spellweaver neither writes the
outbox directly nor operates containers. Spellweaver owns scheduling identity, eligibility, overlap,
and miss semantics; a separate clock/relay mechanism detects due work and publishes only the
ordinary delivery that Spellweaver has admitted. Spellweaver does not become that timer or broker.

## Pattern contribution

A publishable Scroll revision declares identity/revision/owner/provenance/support/parentage;
every required Spell contract and placement; typed
input/output/state/error/non-completion; topology and cancellation; capability/tool/plane/budget/
wait; Sigil/effect/privacy/egress/consent and secret-free durable state; checkpoint/idempotency/
receipt/compatibility/migration/drain/refusal; Loom metadata; and serialization/failure/recovery
evidence. Assembly uses explicitly selected shaped store, never package scanning; rejects duplicate
identity, ambiguous routes, unknown adapters, unreachable station, unsafe cycle, unserializable
state, missing continuity, forbidden effect, then freezes generation. Workflow dataclass is internal
pre-v1, not ABI. Creation/Assimilation/Extension law governs candidate publication; source/model/
Loom draft cannot publish without validation, review, evidence, immutable revision.

Spell-contract publication, executable implementation registration, Scroll publication, and
activation are separate acts and shaped stores. Deactivation of an implementation closes dependent
Scrolls to new admission; already pinned Runs may use an explicitly retained closure, while security
revocation forbids even retained execution. Installing code or replacing a process-built catalogue
is [Evolution](18-evolution.md), not Reanimation; Reanimation restores an exact whole-body
checkpoint. A future declarative-only Scroll may activate without Vessel replacement only when all
implementations are already admitted and an atomic durable catalogue-generation mechanism exists.

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
application contract and worked example. It does not prove executable delivery;
[State of Work](../state-of-the-work.md) keeps the shared whole-system envelope, while a
Composition mentions local delivery only when it materially changes how the contract is read.
Suite may coordinate separate Compositions
with typed ArtifactRef/Intent handoffs, pinned revisions/correlation/ceilings/dependencies/partial
completion, never merge ownership/secrets/Sigils/HitL/domain judgment. Suite execution is Designed:
child identity/revision/closure/fan-out/join/budget/cancel/stasis/retry/effect/compensation/partial
must be defined first.

A Schedule makes one durable, deduplicated **Occurrence** for each firing and enters ordinary
admission. Spellweaver owns calendar/event meaning, service class, temporal eligibility,
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
as evidence, not reverse edges. Spellweaver admits a Correction Request only as new forward Invocation
under validation/budget/authority/consent; it cannot resume arbitrary old station, mutate artifact,
inherit consumer authority, or turn recurrence into training. Repair starts from smallest supported
cut; reuse requires full input/evaluation closure; unresolved attribution/exhausted budget terminates honestly.

## Loom projection and drafting

[Loom](../divination/altar/loom.md) reads the fixed immutable Pattern manifest: semantic stations,
edges, Gate/delegate,
revision, implementation revision, checkpoint schema, digest. Mermaid/canvas are views. Charcoal remains inert until canonical
declarative Pattern has typed ports/state/effects/authority/termination/continuity. Drawn grouping
does not nest Pattern or execute Suite. Publication alone makes new immutable revision; Invocations
stay pinned. Model prose, browser gesture, renderer state are not authority.

## Rejected alternatives

### Unversioned procedural chains

Functions suit a bounded station, not long-lived identity with parking, projection, contribution, or revision continuity.

### A second application scheduler

It fragments admission, priority, recovery, and inspection; applications contribute to Spellweaver.

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

The portable profile additionally requires golden and negative fixtures consumed by two independent
implementations: canonical bytes/digests; duplicate and unknown fields; numeric and ordering edge
cases; namespace collision; exact contract resolution; repeated Spell placement; missing,
unauthorized, unavailable, retained, and revoked implementations; v2 coexistence; and refusal of
similar-name, version-range, or newer-revision substitution.
