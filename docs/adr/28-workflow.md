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
| Composition | Reusable application capability owning domain records, judgment, effects, policies, projections, and a Pattern catalogue |
| Product | Named professional or market package selecting Composition or Suite revisions, profiles, projections, and concrete use cases |
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
revision continuity, and contribution. Composition owns domain judgment. Product owns its customer
promise, supported-use-case catalogue, packaging, and defaults, but none of its members' records,
policy, secrets, consent, or effect authority. IAM/Ward/HitL own authority; Dispatcher capability;
Orchestrator readiness; Workers delivery/retry; Phylactery/Graph stores and checkpoints; Riddle
evaluation; Soulforge promotion.

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
Gate, reply) and delegated_rite@1 (exact `/delegate` command token, reference job, Durable Stasis,
result/reply). The latter proves no external coding-agent/Tomb plane. One boot-composed catalogue
is shared by admission, workers, Bridge, Loom, and Orb. It freezes after construction, rejects
duplicate exact revisions, requires an explicit active revision when alternatives exist, permits
registered revisions or whole names to remain retained but inactive, requires explicit non-default
route precedence whenever multiple names are active, and has one active default. Run commits selected
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

## Authorship provenance and protected regions

Authorship and approval are different records. A human may approve model-written text without
having written it; an Agent may commit through a human-configured VCS identity. Git author,
committer, account name, prose style, detector score, and absence of model metadata are evidence at
most. None may mint human provenance.

An **Authorship Attestation** binds one artifact revision and stable region id to its canonical
content digest, locator, origin class, attesting Principal, and evidence references:

| Origin | Meaning |
| --- | --- |
| `human_attested` | An authorized human Principal explicitly claims authorship of the exact bound content. Approval alone is insufficient. |
| `agent_generated` | Host-observed Agent or model lineage produced the bound content. |
| `mixed` | Human and Agent contribution are materially interleaved and cannot be separated honestly. |
| `unknown` | No admissible record establishes authorship. |

The attestation is an attributable claim, not proof of private cognition. A trusted local or
authenticated human surface may create `human_attested`; an Agent, provider assertion, imported
commit, or style classifier may not. Agent outputs receive `agent_generated` from the host job and
artifact lineage even when a human later approves them. Approval changes authority to promote, not
the history of who composed the bytes.

Attestations append; they do not overwrite inconvenient lineage. Contradictory or inseparable
human and Agent evidence resolves to `mixed`, while insufficient evidence remains `unknown`. A
trusted human surface may attest a new human-written replacement only when it binds that editing
boundary and exact result. Copying unchanged Agent output through the human surface cannot launder
its origin.

A **Protected Region** binds a stable region id, target artifact revision, canonical content digest,
locator, and `live_change_only` policy. Accepting a human authorship attestation protects that region
by default; an authorized human may also protect material of another or unknown origin. Line numbers
are only a projection. Document block ids, syntax-aware symbols, structured field paths, or
media-specific selectors locate the region, while the digest catches drift. Moving, deleting,
splitting, reformatting, changing its marker, or changing the protection record itself counts as a
touch.

Source comments, front matter, editor decoration, and VCS notes may display the mark but are not its
authority. The target owner retains the base-revision attestation and protection manifest outside
the candidate's control. An Agent cannot unprotect text by deleting its visible marker.

For a candidate that may replace an artifact, Spellweaver orders one admission path:

1. bind the exact base revision, candidate digest, and target-owner diff;
2. resolve touched regions against the base-revision protection manifest;
3. continue normally when none overlap, or enter Durable Stasis for one live HitL verdict naming
   every affected region, old and replacement digests, and an authorized exact-diff artifact;
4. after approval, revalidate base, candidate, region set, and effect identity before the target
   owner writes a successor artifact and manifest.

Protected-region change never accepts Codex preauthorization, a previous verdict, a broad “edit
this repository” grant, or approval of a different patch. Base or candidate drift creates a new
call. Denial preserves the candidate as inert evidence; it does not mutate the active artifact.
An Agent may prepare a suggested replacement in Lab, but cannot apply it to the protected body.

An approved Agent edit remains `agent_generated` when it wholly replaces a region and `mixed` when
it interleaves with retained human material. Unchanged human-attested content retains its
provenance across an approved move. A human may later rewrite and freshly attest the exact result;
the approval itself never performs that relabelling.

For legacy material, history and stylometry may nominate likely regions for review. They remain
`unknown` until a human explicitly attests the exact current digest. Spellweaver owns the Gate and
ordering; the artifact/effect owner owns region resolution and mutation; [Creation](16-creation.md)
owns candidate isolation and target-owner promotion; [HitL](25-hitl.md) owns the live verdict.
No Authorship Attestation store, protected-region manifest, trusted authoring surface, overlap
resolver, or candidate-bound review card is delivered. [State of
Work](../state-of-the-work.md#smith-forge-promotion) owns that boundary.

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

A protected remote score joins labels, selects a minimum disclosure projection, locally transforms,
may ask a local Privacy Agent, independently verifies transformation evidence, creates a consumer-
specific Privacy Cut, gets an exact tagged-target EgressDecision, transmits once, and quarantines
the return. Censor/Agent proposes only. Context owns the Cut; Security owns declassification.

## Execution-road planning

Portal, A2A, and delegated coding are not interchangeable provider names. Spellweaver first closes
the labor boundary, then any cognition boundary inside it:

- a native Spell or Agent keeps decomposition in LychD and may use deterministic work, a local
  Soulstone, or one admitted Portal capability;
- an A2A placement delegates one public task schema to a sovereign peer, which owns its private
  decomposition and provider choice; and
- a delegated coding placement gives one foreign runtime a contained `read`, `candidate`, or
  `verify` workspace and tool loop. A child model call is a nested Portal boundary.

Each eligible placement pins `ExecutionRoadPolicy@1`: exact Pattern/Spell/placement revisions;
semantic input/output and non-completion; permitted labor and cognition roads with explicit branch
predicates; classification, lineage, Cut, consent, quarantine, and validators; effect demands;
deadlines and request/token/concurrency/spend ceilings; durability and idempotency; permitted
fallback edges; and result-adoption evidence. Economics and readiness may eliminate an eligible
branch, never make an ineligible one lawful.

Before road admission, Spellweaver creates immutable `ExecutionRoadDecision@1`; the Run ledger
stores it before any road-owned submission, and the later dispatch event, `ServiceJobAttempt`,
Intercom task, or `AgentJob` references its id. The decision binds Run, station attempt, parent
decision/retry generation, exact input/export digest, artifact-reference-set digest, opaque
custody refs, and canonical content-digest/media-type/size/classification evidence,
source-manifest and influence-label digests, safe residual-disclosure summary/digest, opaque
restricted lineage refs, purpose, policy and expiry, chosen road, budgets, expected
result/quarantine, record classification/visibility/retention, and the expected road binding. It
contains no caller-supplied full `ArtifactRef`, raw subject, filename, material-parent, source span,
reversal value, credential, or live grant/lease handle:

The complete decision is restricted, deployment-local, non-exportable evidence. Loom, logs, and
external receipts receive only an opaque decision id or Security-owned `EvidenceDigest@1`
projection; canonical raw digests never leave local decision/attempt custody and are not anonymous.

| Road | Exact authority retained by its owner |
| --- | --- |
| local capability | dispatch event records demand plus observed grant/lease identity only; asynchronous or effectful work transfers to `ServiceJobAttempt` |
| Portal | bounded immediate `ModelGrant`/`CallGrant` uses the decision, exact `EgressDecision`, lease, and dispatch/security events; Reach, asynchronous, paid, autonomously retriable, or post-submit-reconcilable work uses `ServiceJobAttempt` |
| A2A | enrolled peer, outbound peer-task/outbox identity, Durable Stasis, authenticated terminal adoption |
| delegated coding | `AgentJob`, runtime/profile, Coffin containment, workspace/artifact boundary, terminal adoption |

The decision records selection only; it never replaces those ledgers, observes a terminal, or
settles their truth. Durable road admission commits the decision and its road record atomically when
they share one Phylactery transaction; otherwise the decision commits first and the idempotent road
record adopts its id. A local
deterministic road-selection Spell may choose only among manifest-declared branches using pinned
policy and admitted observations. Dispatcher then binds an already eligible capability; it does
not rank price, privacy, peer trust, or coding runtimes. Orchestrator makes managed local substrate
ready; it does not change the road. Gateway `auto`, model-written routing, or a foreign runtime's
provider choice cannot substitute for this decision.

A semantic retry, fallback, changed payload, target, peer, model, workspace projection, or
delegated child call creates a new road decision, then its road owner creates the appropriate
attempt/task/job and every required Cut/egress decision. Exact transport redelivery within one
admitted road-owned attempt instead preserves sealed bytes, target, external/idempotency identity,
road decision, and Cut/token namespace; the adapter must prove atomic same-key/same-payload
idempotent replay or no prior effect, road-specific retry/reconciliation law must permit it, and
each physical transmission receives a fresh EgressDecision and consumes its bounded disclosure
use. A submitted attempt is first reconciled under its existing identity; uncertainty cannot
activate an alternate branch by pretending the first effect did not happen. Every remote return
stays attributed and quarantined until the Composition owner validates and adopts it.

[Execution roads](../sepulcher/extensions/weaver/execution-roads.md) carries this law through the
operator-facing selection and failure journey.

## Parallelism and delegation

Built-ins are serial BaseNode. Parallel map/fork/join/reduce needs branch identity, declared
reduction, bounded concurrency, cancellation, Gate behavior, completed-effect receipts, and
crash-recovery on both join sides. A bounded durability adapter cannot replace ledger, Ward,
Dispatcher, Orchestrator, HitL, or revision. Delegated station declares request/result,
containment, budget, timeout, cancellation, artifact boundary, downstream use; provider adapter
invokes foreign runtime, never embedded CLI/credential/private graph.

## Compositions, Products, Suites, and schedules

Portfolio membership marks an accepted **Native Reference Composition**: a first-party supported
application contract and worked example. It does not prove executable delivery;
[State of Work](../state-of-the-work.md) keeps the shared whole-system envelope, while a
Composition mentions local delivery only when it materially changes how the contract is read.

A **Product** gives a profession or market one named operator door. It pins eligible Composition
or Suite revisions, service profiles, projections, supported use cases, defaults, and its customer
and support envelope. A Product may use one Composition or coordinate several through a Suite; it
does not become another workflow executor, merge member ownership, or convert packaging into
authority. Deployment instantiates a Product under one operator's configuration without creating a
new Product identity merely because its host, customer, or credentials differ.

A Native Reference Composition may also publish an exact reference deployment profile without
becoming a Product. Such a profile binds an implementation and acceptance target; it creates no
service until Configuration selects a delivered registered revision and Containers admits its
complete deployment manifest.

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

### Git identity or an AI detector as authorship proof

Commit identity can be borrowed by an Agent, and style classification is probabilistic. Both may
nominate legacy material for review; neither can create a human authorship attestation.

### A prompt warning or source comment as protection

An effectful Agent can ignore the prompt or delete the marker. Protection is enforced by
target-owner comparison with the base manifest and an exact live Gate, outside candidate control.

## Consequences

!!! success "Accepted"
    - Exact Pattern identity, waits, contributions, Suites, schedules, and Loom share one future admission law.
    - Ownership stays split and immutable revision prevents substitution.
    - Human authorship remains distinct from human approval, and protected material cannot be
      promoted through an Agent edit without one exact live verdict.

!!! failure "Cost"
    - Automatic compatibility proof, durable Pattern publication, scheduling, parallel durability, and editing are separate programs.
    - Construction proves declared Graph topology only; effect, recovery, and compatibility semantics still need their own evidence.
    - Trusted human identity, stable media-specific selectors, retained manifests, and exact diff
      review add storage, UI, and recovery work.

## Acceptance evidence

Registry, route-once, manifest, serialization, Loom, admission, claim, consent, delegation, and
recovery tests prove the floor. Each future surface needs focused ambiguity, compatibility, failure,
cancellation, replay, and projection evidence before State promotion.

The portable profile additionally requires golden and negative fixtures consumed by two independent
implementations: canonical bytes/digests; duplicate and unknown fields; numeric and ordering edge
cases; namespace collision; exact contract resolution; repeated Spell placement; missing,
unauthorized, unavailable, retained, and revoked implementations; v2 coexistence; and refusal of
similar-name, version-range, or newer-revision substitution.

The authorship-protection profile additionally requires fixtures for every origin class;
conflicting and inherited lineage; unchanged moves, splits, marker deletion, and manifest drift;
base and candidate races; live-only refusal of preauthorization; exact affected-region review; and
proof that approving Agent output never relabels it `human_attested`.

The execution-road profile additionally requires complete local/Portal/A2A/delegated matrices;
manifest-undeclared and model-selected road refusal; consumer-specific Cut and target binding;
nested coding-agent child egress; capability/peer/runtime unavailability; pre- and post-submit
failure at every edge; new-attempt fallback; indeterminate reconciliation; quarantine/adoption; and
proof that a decision commits before admission, contains no live handle, is referenced by the
road-owned record/event, and never settles that ledger.
