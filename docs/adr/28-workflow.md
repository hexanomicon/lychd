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

For one casting, follow [score identity](#spells-scrolls-and-casting), [exact road selection](#execution-road-planning), [admission](#admission-and-ownership), and [Stasis](#gates-effects-and-stasis). To change what may be cast, follow [migration](#migration-without-rewritten-history), [contribution](#pattern-contribution), and [protected authorship](#authorship-provenance-and-protected-regions). [Application and coordination ownership](#compositions-products-suites-and-schedules) keeps those scores accountable to their Compositions, Products, and Suites.

The contracts below connect application ownership to one exact casting. [Current material](#current-material) relates them to the source registry; [State of Work](../state-of-the-work.md#topology-a-local-runs) collects implementation evidence and outstanding work.

## Decision

**Spellweaver** is LychD's single logical workflow jurisdiction; `Weaver` remains its short,
code-facing name and the compatibility spelling used by existing paths.

| Name | Office |
| --- | --- |
| Area | Non-exclusive thematic grouping for discovering Compositions, without application or runtime ownership |
| Composition | Reusable application capability owning domain records, judgment, effects, policies, projections, and a Pattern catalogue |
| Composition Revision | One immutable version of a stable Composition contract; a materially different application capability requires another identity |
| Product | Named professional or market package selecting Composition or Suite revisions, owner-qualified profiles, projections, and concrete use cases |
| Pattern | One named executable-score lineage published by an application owner: a Composition, or a Suite for coordination only |
| Scroll | The mythic name for one immutable Pattern revision: the whole score, not one node |
| Spell | One independently named semantic action contract: what a station may do |
| Spell placement | One Scroll-local station that invokes an exact Spell contract |
| Invocation | One admitted bounded world—the Circle—in which identity, Context, authority, and consequence meet |
| Casting | The performance of one exact Scroll within that Invocation |
| Run | Durable execution/ledger identity |
| Graph | Typed state topology |
| Loom | Read-only declared-score projection |
| Suite | Versioned live coordination of separate Composition-owned Invocations, independent of Product packaging |

Spellweaver owns validation, registration, routing, logical dependencies, Gates, schedules/overlap,
revision continuity, and contribution.

Composition owns domain judgment. Product owns its customer
promise, supported-use-case catalogue, packaging, and defaults, but none of its members' records,
policy, secrets, consent, or effect authority.

IAM/Ward/HitL own authority; Dispatcher capability;
Orchestrator readiness; Workers delivery/retry; Phylactery/Graph stores and checkpoints; Drift
evaluation; Soulforge corpus and training lineage. Promotion remains with the receiving policy,
required HitL, and target effect owner under [Training](33-training.md).

## Spells, Scrolls, and casting

The grammar follows a performance: a **Scroll** is one immutable workflow score; each semantic
station places a **Spell**; a **casting** performs the Scroll inside one admitted Invocation and
its [Circle](../divination/altar/circle.md). These names preserve distinct engineering identities.
They create no duplicate schemas, and imagery cannot replace those identities.

A Spell is the smallest independently named, discoverable, teachable action at the workflow
boundary: ask an Agent, anonymize material, await consent, write an artifact, delegate work, or
send through a Portal. “Smallest” is semantic, not mechanical. Its implementation may involve
model calls, tools, syscalls, retries, or adapter machinery. An internal operation becomes another
Spell placement only when the Scroll must independently type, route, authorize, checkpoint,
retry, inspect, or recover it.

The **Spell contract** defines typed input, output, errors and non-completion; semantic
requirements; authority and effect demands; and continuity obligations. A **Spell implementation**
Contribution claims to realize one exact contract revision, retains its Registrant provenance, and
separately names any concrete Provider it binds. It has distinct code, package, adapter,
checkpoint, and evidence identity. A Spell is not an uppercase Dispatcher
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
has no independent public Spell identity. The runtime does not ship a Spell catalogue, persisted Resolution Lock,
portable Scroll ABI, remote compatibility negotiation, teaching surface, or package contribution
store.

Policy for an unknown Spell may choose only among refusal, a request for an attributed teaching
candidate, or use of an already admitted exact contract with an exact local binding. A teaching
candidate is hostile foreign craft: it enters [Assimilation](35-assimilation.md), not the live
registry. Smith may re-express it locally, but Spellweaver validates and the target owner publishes
it only after evidence and authorization. Publication creates new catalogue truth and a later
casting; it never mutates or resumes the refused Invocation under changed law.

### Language is typed, not global

Canonical Composition, Pattern, Scroll, Spell, placement, schema, field, route, status, and event
identities are locale-neutral and never translated. Human-facing labels and explanations may use
versioned catalogues, but changing their locale cannot change the signed declaration, Resolution
Lock, Graph topology, or Run. [Frontend](15-frontend.md#interface-locale-and-content-language) owns
Altar locale; [Vision](36-vision.md) and [Audio](37-audio.md#engine-model-protocol-and-language)
own their media-language boundaries.

A Spell contract carries exact language or locale fields only where its semantics require them:
ordered input/output preferences, original language, requested result language, permitted
detection, fallback, and refusal. Translation is a separately named, attributed Spell or
owner-declared transformation; it retains source and derived text, implementation revision, and
declared loss. A model, engine, browser, peer, or Persona may not infer a host-global language or
silently translate another station's material.

Translation does not become a freestanding Composition merely because several Patterns can reuse
it. A versioned Translation Spell has an authority-qualified publisher that owns the contract's
semantics and revision; Spellweaver owns registration, placement, resolution, and casting law,
not linguistic truth or application acceptance. The Composition placing it retains the source and
attributed derivative and owns fit for its domain.

For example, [Language Edition](../compositions/language-edition/index.md) may place Translation inside a timed-media
language edition while retaining scene, speaker, glossary, timing, and localization judgment.
Another application may place the same exact contract under different records and finish law
without inheriting Language Edition's project or becoming part of a global Translation workflow.

### Progressive finish and forward continuation

A Scroll may declare several typed finish boundaries and an exact admission-time finish policy,
including a bounded interactive policy whose possible Gates and terminal routes are already in the
score. For example, one visual score may permit an accepted still, an animated sequence, or a
sealed visual package. Reaching the requested still boundary is successful completion of that
Invocation, not a Run left in Stasis. Failing to reach a requested motion boundary is partial or
non-complete according to the pinned score; an intermediate image cannot be relabelled as the
requested video.

A Gate may pause the same casting for an exact review or a declared choice to continue. Live or
Durable Stasis exists only while an admitted owner, capability transition, consent, or delegated
result remains outstanding. Once the operator settles at a valid finish boundary, the Run becomes
terminal. Later animation, soundtrack, edit, or publication begins a new forward Invocation over
immutable `ArtifactRef` inputs and preserves the prior result.

Different prompts, source artifacts, requested language, target profiles, or a declared finish
boundary are new Invocation inputs when the exact Scroll schema permits them. Different stations,
edges, Spell contracts, authority ceilings, or model requirements create another Scroll revision.
Several steps owned by one Composition may inhabit one Scroll; separate Composition-owned work is
coordinated by a Suite through typed handoffs, never by nesting or silently resuming another
Pattern.

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

Fixed source registry retains bridge_chat@1 (Bridge conversation, context, Agent turn, optional consent
Gate, reply), adds bridge_chat@2 with an admission-pinned exact capability key and bridge_chat@3
with that key plus an explicit public-note Archive profile. Opt-in bridge_chat@4 binds one
authenticated public-page declaration and Scout profile. The registry also retains
delegated_rite@1 (exact `/delegate` command token, reference job, Durable Stasis,
result/reply). Optional delegated_rite@2 retains one configured runtime/profile through Run admission
and checkpoint validation; neither revision supplies an external coding-agent/Tomb plane. One boot-composed catalogue
is shared by admission, workers, Bridge, Loom, and Orb. It freezes after construction, rejects
duplicate exact revisions, requires an explicit active revision when alternatives exist, permits
registered revisions or whole names to remain retained but inactive, requires explicit non-default
route precedence whenever multiple names are active, and has one active default. Run commits selected
name and manifest; resume never routes Intent again. Loom exposes active/default/route-rank metadata
without making retained revisions admissible.

This is a retained Core-owned legacy Pattern registry, not Extension contribution, Composition or
Suite publication, scheduler, editor, or durable Pattern store. The `bridge_chat` lineage and
`delegated_rite` lineage are the explicit pre-Portfolio exception: new application Patterns require a
Composition owner, while a Suite may publish only its coordination Pattern. State separately owns
v1 adapter, delegation, stasis, and Loom.

The opt-in `bridge_chat@3` revision is a read-only public-note answer profile within that retained
lineage. Admission pins the exact local chat capability and Archive profile, namespace, subject,
and policy revision before queue publication. Its score recalls once, resolves the exact retained
receipt for inference, and settles an attributed answer. It admits no model tools, consent Gate,
or settled-history replay. A restarted casting keeps its admitted bindings and receipt; changed
current authority or source eligibility refuses continuation. The receipt's identifiers and
digests may enter Graph state, while recalled bytes remain transient Context data. Revisions 1
and 2 keep their existing manifests and recovery contracts. State of Work separately records
whether the new revision's runtime and PostgreSQL acceptance have passed.

The separately opt-in `bridge_chat@5` semantic source-answer casting belongs to the same retained
Bridge lineage. Its immutable score is `RecallSemanticNotes` → `AnswerSemanticNotes` →
`SettleSemanticAnswer`, with a separate checkpoint schema. Typed `weaver.bridge.semantic` selects
explicit threshold and bounds; the existing independently enabled Archive semantic generation
supplies the manifest/reference. Boot composition requires PostgreSQL, the actual local Archive
caller mapping and an exact local chat capability, without readiness probing, startup derivation,
registration or inference. Admission pins all bindings before queue publication; restored state
must match the persisted Run and current source authority. The [Memory](27-memory.md#native-semantic-source-answer-consumer)
and [Context](21-context.md#explicit-archive-projection) owners govern retrieval and outbound data.
Existing revisions keep their identity, manifests and history contracts. Omission does not change
the ordinary conversation route. This boot selector does not supply a per-message mode switch;
Altar guidance describes the configured default independently of historical Runs and readiness.
State separately owns executable and native answer acceptance.

The opt-in `bridge_chat@4` revision answers one explicitly declared public page. Its
command is `/read-public <exact HTTPS URL>` followed by a newline and a nonblank question. The
authenticated operator separately declares the complete locator public under the current local
Scout classification policy; an ordinary message or model-produced URL cannot supply that
declaration. Admission retains the declaration, exact Scout profile and local chat capability.
This revision refuses other command forms rather than falling back to another Bridge revision.

Its score is `PreparePageReview` → `AwaitPageConsent` → `AcquireAndAnswerPage` →
`SettlePageAnswer`. Preparation atomically retains the acquisition request and complete native
review with its consent. The consent Gate parks without acquiring material. The acquisition station
resolves and verifies the exact local chat grant before claiming Scout's durable, bounded attempt;
hardware re-entry cannot repeat an issued acquisition. Fetch, extraction and inference share that
station. Scout rechecks current authority after awaited preparation and before each network handoff,
extraction and material consumption, including token counting. No remote model or model tool is
admitted by this profile.

State contains admitted identities, preparation/receipt references, dispositions and the ordinary
answer. Acquired bytes remain bounded attributed Context data, with influence and budget accounted
for; they cannot become instructions or authority. A receipt without its transient material cannot
authorize refetch after a park, retry or restart. Such a continuation reports material unavailable
unless the answer already reached its retained settlement checkpoint. An answer may quote source
text and is retained as ordinary Bridge history; transient acquisition is not a promise that no
derived text persists. The first profile follows no redirects. Revisions 1–3 retain their manifests
and recovery contracts. State of Work owns delivery and end-to-end qualification separately.

The explicitly configured `creation.investigate@2` belongs to the accepted
[Creation investigation](../compositions/creation/index.md) contract. Its fixed serial score
retains a source-bound candidate and fresh attributed verdict through the existing Run road.
Application records own stage claims, uncertainty, cancellation and separately admitted
continuation; the registry and Graph create no second scheduler or general SDLC owner.
Its local typed selector fixes the exact capability, while case custody additionally retains
resolved role bindings. State of Work owns delivered registration and end-to-end evidence.

The initial revision 1 prototype remains historical. Revision 2 is the sole selected closure;
current-role reads retain old cases, while retired-contract policy refuses their write actions.
Full profile matching gates admission, continuation and stages. Current-revision cancellation
uses retained contract identity and current local authority without requiring a live model binding.
No old Run, claim, response or reservation is reinterpreted or renewed.

## Pattern identity

The manifest binds:

- schema, URL-safe key and revision;
- reviewed implementation revision and checkpoint schema;
- the declared entry station;
- semantic stations, each with a unique key, a label, and a kind;
- permitted edges between declared endpoints; and
- a deterministic SHA-256 digest.

Executable stations map one-to-one with Python nodes. Construction rejects missing, duplicate,
unknown, or mismatched station mappings; unknown station kinds or edge relations; duplicate semantic
edges; Gate or delegate marker mismatches; dynamic `BaseNode` returns whose topology cannot be
proved; and any semantic transition set that differs from the public Graph node definitions.

The declared entry names the actual executable start node and participates in the digest. Exactly
one terminal is required. Gate loops remain explicit Graph edges; a delegate station additionally
declares its durable same-station re-entry edge. A Gate or delegate derives Durable Stasis.

The opaque implementation revision is a human-reviewed compatibility closure, not a hash of Python
bytes. Behavior that would invalidate parked state or replay must bump it or the Pattern revision.
The manifest fingerprints source-adjacent declaration rather than compiling all semantics.

Admission persists snapshot/digest; execution/resume requires exact current registered equality or
fails pinned Pattern unavailable. Multiple exact source-registered revisions may coexist: new
admission uses only an active revision while an older Run resolves its retained pinned revision
directly. Removing old executable code still makes that revision unavailable. Compatibility
is proved only by exact registered equality and the reviewed closure. Automatic source-code change
detection, durable publication, drain, and migration remain future work.

## Migration without rewritten history

Portable Spells and Scrolls arrive additively:

1. Freeze current Pattern schema v2 digests and persisted-Run fixtures.
2. Introduce Spell-contract, implementation, placement, and Resolution-Lock types without changing
   v2 snapshots.
3. Adapt each v2 station at assembly as a Scroll-private `legacy_inline` Spell identity; it is
   neither reusable nor portable.
4. Add separate receiving-owner-governed Spell-contract, implementation, and Scroll stores whose
   Contributions retain Registrant provenance and any separate concrete Provider reference, then
   build one immutable registry generation shared by admission, workers, Bridge, Loom, and Orb.
5. Introduce a new Scroll schema with exact Spell references and a Resolution Lock while dispatching
   v2 and the new schema through separate validators and resolvers.
6. Publish built-ins only as new revisions. Never rewrite `bridge_chat@1` or `delegated_rite@1`, and
   retain their executable closures until pinned Runs drain or settle honestly unavailable.

No compatibility shim may present a v2 Python node as a canonical public Spell merely because its
label resembles one.

### Private v2 adapter

The internal adapter for steps 2–3 gives every executable v2
station a deliberately private identity: derive a Scroll-private contract from `(pattern_id,
pattern_revision, manifest_digest, station_id, legacy_inline)`, place it under the station key and
kind, and bind it to the manifest's exact `implementation_revision`, `checkpoint_schema`, and Python
node fingerprint `module:qualname`. Contract, placement, and implementation identities must remain
separate and form a one-to-one set over executable stations. The declarative terminal maps to Graph
`End` and must not become a fictional Spell or implementation.

The boot-derived `legacy_inline` Resolution Lock must have a deterministic **internal-v0** digest.
It is not JCS portable identity, a signature input, a public Spell contract, or proof of Python
source equivalence. It must change when the exact local node binding changes without altering the
frozen v2 Pattern snapshot or digest. During this migration step, in-process exact revision lookup
must use the lock; the lock must not be stored on Run, exposed by Loom/Orb, or claimed as the future
persisted Resolution Lock. Persisting and projecting it begins only with a new schema and migration
under steps 4–5.

### Configuration-to-casting spine

The extensibility path is one directional assembly, not runtime reflection:

```text
typed local configuration selection of exact registered refs and bounded policy
→ explicitly selected shaped contribution stores
→ one immutable contract / implementation / Scroll registry generation
→ exact resolution and Resolution Lock
→ registered Scroll-version adapter and Graph binding
→ per-placement AgentSpec, Context contributions, and effect demands
→ Run admission pins executable truth before queue publication
```

TOML may later select authority-qualified ids, exact revisions/digests, activation, placement
policy, budgets, and registered Context projection profiles already admitted by the selected
Extensions. It remains a local typed selector, not the portable Scroll identity owned by canonical
JSON. It may not contain a Python module/class path, callable, Graph node or edge, arbitrary prompt,
raw source material, credential, live Connector/grant, or fallback implementation. Registering a
Rune schema, Spell contract, implementation, Scroll, adapter, AgentSpec, Context formatter, or
effect handler is a separate shaped contribution; none implies another and duplicate or unresolved
exact identity fails before activation.

The Graph binder consumes only an admitted Scroll-version adapter and its exact lock. It never
imports code named by configuration, scans packages for subclasses, or guesses an implementation
from a similar label. Placement-specific Agent and Context assembly occurs after resolution so a
Reader may receive an exact `structure` or `verbatim` projection without acquiring Writer tools,
while a Writer must separately satisfy its declared effect and authority contract. The current
source delivers the fixed v2 registry and a bounded `[weaver.bridge]` selector for `bridge_chat@2`,
public-note `bridge_chat@3`, public-page `bridge_chat@4`, or explicitly boot-selected semantic-source
`bridge_chat@5`. Revision 5 binds the independently enabled Archive semantic generation's exact
manifest/reference and embedding binding, an explicit cosine threshold and finite recall bounds,
and one exact local Soulstone Chat capability. Boot composition checks declaration metadata without
readiness probes, model work, generation registration or derivation; Run admission retains the
complete semantic binding before queue publication. Omitting configuration keeps revision 1 for
new admissions, and a changed selection cannot redirect older Runs.
Its exact capability key is server-admitted Run intent, copied into typed Graph state; a missing key refuses admission or checkpoint decoding,
and an unavailable target never falls back to another runtime. The worker binds the revision's
state validator to persisted Run intent; the Graph runner checks fresh and restored state before
node execution, including hardware re-entry. A differing key, Run/session identity, prompt, or
admitted priority refuses the checkpoint. Retried admissions first read
existing Run truth, so configuration changes cannot rewrite queued or parked work. Revision 1
applies the same admitted-state checks while keeping its eligible-pool behavior and manifest.
Private `legacy_inline` assembly now binds in-process exact lookup while preserving v2 snapshots.
Portable stores, Resolution Lock persistence, placement profiles, and dynamic registration remain
undelivered.

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

Cache reuse is an execution-road optimization, not Execution Projection, Agent memory, continuity,
authority, or recovery. After semantic input, road, and exact capability binding are pinned, a
future execution profile may carry an opaque cache-affinity preference only for connector reuse or
physical placement of that same admitted call. The preference carries no prompt, history, plain
prompt-derived digest, or authority and cannot select another model, road, or input policy. No
current Dispatcher or Orchestrator contract implements it; future declared support remains a
Dispatcher capability fact and local placement remains inside Orchestrator's physical boundary.

Provider cache eligibility, identity and lifetime scope, retention, and current tariff remain
dated [Portal Roads](../sepulcher/animator/portal-roads.md) selection-receipt facts; local prefix or
KV behavior remains an exact Soulstone engine/profile fact. A provider, model, or engine name alone
proves no cache fact. An exact launch flag or provider declaration is declared capability or
intent, not observed residency, hit, or savings; `prefix_digest` witnesses LychD content only, and
a projected discount is not a receipt. When available, provider-reported cached-token usage is
attributed billing evidence under [Oculus](29-observability.md) law, not proof of physical KV reuse.

Cache availability cannot be required for correctness, input sufficiency, budget admission, or
recovery. Before first submission—or after the road owner proves no prior effect—an ordinary cache
miss, eviction, or process restart executes the same admitted call without cache reuse on the same
pinned binding. The miss alone causes neither refusal, fallback, nor input-policy change. After
submission, existing reconciliation and idempotent-redelivery law governs; a changed target,
model, or runtime still requires the existing fresh road decision. Only a separately admitted
provider live-session road may require its exact session binding and opaque handle; its owner
defines loss and reconciliation. Tool and consent continuation retain their existing Graph and
HitL contracts and never become cache affinity.

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

### Execution projections for procedural Agent placements

For a declared long-horizon procedural region, a Composition may define a bounded, versioned
**Execution Projection**. The Composition owns its meaning; the exact Scroll revision pins its
schema and initialization, placement mappings, required unknown and omission fields, admitted
observation inputs, permitted candidate operations, applicator binding, history policy, and hard
field, cardinality, and byte limits. A changed meaning, schema, mapping, operation set, applicator,
or history policy is a new Scroll revision. The projection contains only working material required
by later placements. It is not the whole Graph continuation, an authoritative domain record, an
effect receipt, an audit trail, Archive memory, or conversation history.

The placement history policy selects exactly `transcript`, `projection`, or `hybrid`. `transcript`
means [Context](21-context.md)-governed bounded settled message groups. A hybrid pins the
deterministic selection profile and bounds for attributed history retained beside the projection;
the assembled call records the exact groups selected at runtime. It is not an undeclared fallback
to all settled history. Any required provider, tool, or consent continuation remains orthogonal
and indivisible; it does not turn `projection` into `hybrid`. Semantic sufficiency and continuity
select the pinned shape before cache, latency, or price. Cache availability cannot change it.

At an explicitly declared Agent placement, [Context](21-context.md) may assemble immutable
instructions, the recipient-specific current Execution Projection, the exact station request, and
fresh admitted observation projections without replaying settled reasoning, actions, or
observations into that model call. Every observation retains its source, revision or cursor,
freshness, classification, and lineage. The placement may omit settled history only when its
contract declares the projection sufficient for continuation; required material that does not fit
refuses before inference. Declared bounds make this input independent of prior-turn count, not
independent of the actual size of its projection and observation.

The Agent returns typed, bounded candidate operations and, when allowed, an action intent. It does
not replace the projection, extend its schema, or mutate workflow control, authority, privacy,
domain truth, or effect settlement. A deterministic workflow-owned applicator binds the candidate
to the exact current projection value and revision plus its admitted observations, validates the
permitted fields and invariants, and alone creates the next committed projection value and revision
for that Casting. An action intent remains inert until the owning effect boundary authorizes,
executes, and settles it; confirmed world-facing fields follow owner observations or receipts,
while indeterminate consequence remains `UNKNOWN`.

Canonical sources, full attributable artifacts, receipts, events, and any retained history remain
with their existing owners even when excluded from a later model call. Exact conversational
history and an in-progress provider/tool or consent continuation are not replaced by an Execution
Projection. When no fixed sufficient schema is known, earlier material may become relevant only
later, or the historical trajectory is itself the requested evidence, the Scroll must admit the
necessary attributed history or artifacts—or stop with an explicit unknown or non-completion.

[SKILL.state v2](https://arxiv.org/html/2608.26263v2) reports that its projection-only,
state-plus-latest-observation variant can preserve or improve benchmark performance while
materially reducing repeated transcript tokens in long sequential single-agent tasks, including
budget-matched controls. That evidence motivates the accepted shape; it does not establish LychD
delivery, universal model performance, shared mutable multi-Agent state, concurrent merge law,
privacy, effect safety, checkpoint recovery, or LychD-specific token savings, cache-aware billing
savings, cache-hit rates, time-to-first-token improvements, or latency gains. The current Pattern
v2 manifests and built-in workflows do not deliver Execution Projections.

## Parallelism and delegation

Built-ins are serial BaseNode. Parallel map/fork/join/reduce needs branch identity, declared
reduction, bounded concurrency, cancellation, Gate behavior, completed-effect receipts, and
crash-recovery on both join sides. A bounded durability adapter cannot replace ledger, Ward,
Dispatcher, Orchestrator, HitL, or revision. Delegated station declares request/result,
containment, budget, timeout, cancellation, artifact boundary, downstream use; provider adapter
invokes foreign runtime, never embedded CLI/credential/private graph.

### Scoped context handoff

A handoff begins a fresh, recipient-specific Context for the receiving Agent placement. The
parent's conversation, loaded documents, tool outputs, and sibling work do not enter implicitly.
Loading a scope into an existing conversation can narrow its task, but cannot remove material
already present; a handoff therefore needs a new assembly boundary. The parent keeps the wider
purpose, dependencies, shared budget, ordering, and responsibility for assessing the return
against the owning acceptance contract.

The exact Scroll pins the handoff's input and return contracts. The parent supplies the smallest
sufficient packet: task and role, acceptance target, relevant operator decisions and constraints,
allowed inputs and effects, exact source/artifact revisions, dependencies and unresolved unknowns,
and the applicable scope routes. A scope routes the recipient to canonical owners and the smallest
useful evidence slice; it is neither a replacement for those owners nor the task specification.
The recipient may load further material within the admitted boundary. A missing prerequisite
requires a bounded request or explicit non-completion, never an automatic copy of the parent's
entire context.

Spellweaver declares the handoff and its continuity requirements;
[Context](21-context.md) owns assembly, ordering, attribution, and budgeting. Applicable governing
instructions and authority constraints survive the handoff. Required provider/tool or consent
continuation remains indivisible; work that requires it must use its declared continuation path.
When historical material is itself necessary evidence, the contract selects bounded, attributed
history or artifacts explicitly. Excluding material from a child call never deletes the parent's
history or canonical records, and prompt isolation alone proves no tool or workspace containment.

The return contains the candidate result or artifact references, observed verification evidence,
and remaining unknowns or blockers. The parent admits the useful return under the existing
acceptance and effect boundaries; no complete child transcript is implicitly appended to its
Context. Independent review receives its own sufficient packet.
[Delegation evidence](../state-of-the-work.md#delegated-agent-execution) records the runtime
boundaries established by the reference adapter.

### Bounded Inquiry in an engineering workflow

**Inquiry** is a reusable design form in the
[Creation workflow](../sepulcher/extensions/weaver/creation.md): bounded Explore is followed by
independent coverage and sufficiency judgment, then Crucible for material alternatives. It can
examine both direction and later implementation boundaries. This method is neither a registered
global Pattern nor evidence of delivered subgraph composition.

The owning score declares the question, required evidence, omissions, judge independence, probe
budget, stopping conditions, and typed return. Sufficiency means enough evidence for the declared
decision, never exhaustive knowledge. A judge may request a bounded source probe or return
non-decision; another judge is not an unlimited escape from missing evidence. Factual disagreement
calls for an admitted discriminating test where one can settle it. The receiving owner retains
acceptance and residual-risk judgment under its law.

Human decision assistance presents a concrete unresolved choice and its consequences. Inquiry
does not add blanket approval requirements to already admitted work; exact live-only and Protected
Region rules remain with [HitL](25-hitl.md). Evaluation of a changed procedure produces evidence
for a new immutable revision and later Invocation, never mutation of a pinned Run.

### Crucible choreography

[Crucible](../sepulcher/extensions/weaver/crucible.md) is the canonical adversarial choreography
for forming a decision candidate: frame one question and common evidence; run separately biased
first-round Postures; join their strongest claims, citations, concessions, defeat conditions, and
unknowns; return that attributed projection for a second-round rebuttal; synthesize without a
vote; then stop at an exact Magus Gate or inert dossier boundary. Logical independence is required;
physical concurrency is optional. A serial implementation must preserve the same isolation and
must not leak an earlier advocate's output into another first-round Context.

Bias is declared input, never authority or a substitute for evidence. Compression between rounds
retains source references, every advocate's nominated strongest claims, concessions, dissent,
unknowns, and omissions; the full reports remain attributable artifacts. Missing evidence may
produce `UNKNOWN`, a bounded evidence request, or honest non-decision. Majority, confidence,
eloquence, model identity, or survival through summarization cannot adopt the result.

Crucible is a reusable score form, not an ownerless global Pattern. A Composition that uses it must
publish its exact Pattern and dossier contract and apply ordinary revision, road, budget, and
authority law. When the receiving decision belongs to another office, that office retains judgment
and the Composition only coordinates the dossier. The choreography neither evaluates a capability
in Drift's place, materializes Shadow branches, nor promotes its own recommendation. A downstream
mutation or Covenant edit begins only through its target owner's workflow and applicable
authority. Where its law requires an exact human verdict, the dossier cannot substitute for that
verdict; where standing policy is eligible, Crucible does not introduce a second universal live
Gate. Protected Regions remain live-only.

## Pattern contribution

A publishable Scroll revision declares:

- identity, revision, owner, provenance, support, and parentage;
- every required Spell contract and placement;
- typed inputs, outputs, state, errors, and non-completion;
- topology and cancellation;
- capabilities, tools, planes, budgets, and waits;
- Sigil, effect, privacy, egress, and consent requirements, with secret-free durable state;
- checkpoint, idempotency, receipt, compatibility, migration, drain, and refusal contracts;
- Loom metadata; and
- serialization, failure, and recovery evidence.

Assembly uses an explicitly selected shaped store, never package scanning. It rejects duplicate
identities, ambiguous routes, unknown adapters, unreachable stations, unsafe cycles, unserializable
state, missing continuity, and forbidden effects before freezing the generation.

The workflow dataclass is internal and pre-v1, not an ABI. Creation, Assimilation, and Extension law
govern candidate publication. Source, model output, and Loom drafts require validation, review,
evidence, and an immutable revision before publication.

Spell-contract publication, executable implementation registration, Scroll publication, and
activation are separate acts and shaped stores. Deactivation of an implementation closes dependent
Scrolls to new admission; already pinned Runs may use an explicitly retained closure, while security
revocation forbids even retained execution. Installing code or replacing a process-built catalogue
is [Evolution](18-evolution.md). Reanimation reconstructs the same body from committed records
after process death; restoring a whole-body cut additionally follows the
[Snapshot Protocol](07-snapshots.md). A future declarative-only Scroll may activate without Vessel replacement only when all
implementations are already admitted and an atomic durable catalogue-generation mechanism exists.

## Authorship provenance and protected regions

Authorship records who wrote material; approval records who accepted it. A human can approve
model-written text without becoming its author, just as an Agent can commit through a
human-configured VCS identity. Git author, committer, account name, prose style, detector score,
and missing model metadata can serve as evidence at most. None may mint human provenance.

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
media-specific selectors locate the region, while the digest detects changes. Moving, deleting,
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
this repository” grant, or approval of a different patch. A change to the base or candidate creates a new
call. Denial preserves the candidate as inert evidence; it does not mutate the active artifact.
An Agent may prepare a suggested replacement in Lab, but cannot apply it to the protected body.

An approved Agent edit remains `agent_generated` when it wholly replaces a region and `mixed` when
it interleaves with retained human material. Unchanged human-attested content retains its
provenance across an approved move. A human may later rewrite and freshly attest the exact result;
the approval itself never performs that relabelling.

For legacy material, history and stylometry may nominate likely regions for review. They remain
`unknown` until a human explicitly attests the exact current digest. Spellweaver owns the Gate and
ordering; the artifact/effect owner owns region resolution and mutation; [SDLC](16-sdlc.md)
owns candidate isolation and target-owner promotion; [HitL](25-hitl.md) owns the live verdict.
No Authorship Attestation store, protected-region manifest, trusted authoring surface, overlap
resolver, or candidate-bound review card is delivered. [State of
Work](../state-of-the-work.md#smith-forge-promotion) owns that boundary.

## Compositions, Products, Suites, and schedules

### Concerns and application design

[Atlas](15-frontend.md#independent-concerns-decomposition-and-addressing) maps independent
Concerns, their decomposition, and where they are addressed. An idea or application can take shape
through that account without first becoming a Project or native Composition. Its own Covenants
can record its adopted decisions. Work outside LychD may use LychD's Covenants as one optional
source of inspiration.

When the design concerns a native Composition, the map explains why its parts exist and exposes
unresolved needs. The Composition still owns its accepted reusable records, judgment, effects,
policies, projections, and Pattern catalogue. Addressing links do not publish or revise those
contracts. Concern decomposition also creates no Scroll transitions or Suite coordination; those
remain separately declared and admitted under their execution owners.

### Composition identity, revision, and retirement

A Composition keeps one stable URL-safe identity across immutable numbered revisions. Each
revision pins its reusable application contract: owned record and request/result families,
Pattern catalogue, judgment and policy boundaries, effect and authority seams, projections,
terminal outcomes, and recovery law. Pattern and Scroll have their own revision identities.
Changing a Scroll cannot silently revise the Composition that selected its catalogue contract.

Publication freezes a Composition revision independently of its implementation. A material
change to any pinned part creates a new revision under the same stable identity. A change that
creates a materially different reusable application capability, transfers its defining durable
records or judgment, or replaces its authority, finish, or recovery boundary requires a new
Composition identity rather than stretching the old one. Editorial clarification that preserves
the complete contract may update its current explanation without claiming another revision.

Retirement never reinterprets an old identity or revision. The owning Composition record names the
retired revision, successor or absence of one, reason, compatibility boundary, and any required
migration or explicit lack of executable migration. If no registry, Run, or stored application
record ever used a revision, there may be no runtime migration to perform; its historical
meaning and retirement still remain explicit. [State of Work](../state-of-the-work.md) separately
records whether any revision is registered, executable, persisted, or supported.

Portfolio membership marks an accepted **Native Reference Composition**: a first-party maintained
application contract and worked example. It does not prove executable delivery;
[State of Work](../state-of-the-work.md) keeps the shared whole-system envelope, while a
Composition mentions local delivery only when it materially changes how the contract is read.

Portfolio acceptance is deliberately rare but not numerically capped. It requires durable reusable
application truth with its own records, judgment, terminal outcomes, and recovery boundary; reuse
of a mechanism or provider is insufficient. Two independently motivated Products or use cases are
strong corroborating evidence, neither a necessary threshold nor proof by themselves. Portfolio
acceptance remains distinct from runtime registration and from delivery.

<span id="areas-for-discovery"></span>An **Area** is a non-exclusive thematic grouping for
discovering Compositions. Areas name the Portfolio's editorial reader views; their directories
and indexes provide documentation routes. They have no runtime identity, revision, domain
records, authority, application namespace, code-layout consequence, dependency meaning, delivery
state, or runtime/Product selection role. A Composition may be discoverable through several
Areas while retaining one canonical route and its own contract. Renaming an Area or changing
its membership does not revise those contracts. Guides organize explanations; Candidate studies
organize proposals by acceptance status. Neither is a thematic Area.

Suites may coordinate live Composition-owned Invocations within one Area or across several Areas.
Sharing or crossing an Area boundary alone creates no Suite requirement; the live-coordination
contract below determines that need.

A **Product** gives a profession or market one named operator door. It pins eligible Composition
or Suite revisions, owner-qualified profiles, projections, supported use cases, defaults, and its
customer and support envelope. A Product may use one Composition or coordinate several through a
Suite; it does not become another workflow executor, merge member ownership, or convert packaging
into authority. Deployment instantiates either a Product revision or an exact Composition-owned
reference deployment profile under one operator's configuration. A Productless reference
deployment creates no market promise or Product identity; changing a Product-backed deployment's
host, customer, or credentials likewise does not create a new Product identity.

A **Product Revision** is one immutable version of that selection and promise. Changing an exact
Composition or Suite pin, owner-qualified profile, projection, supported use case, default, or
customer/support policy within the same stable operator promise creates a new Product Revision.
A materially different profession, market, or operator promise requires a new Product identity.
Neither a new Deployment nor presentation-only public copy changes the Product Revision.

A Native Reference Composition may publish an exact reference deployment profile without becoming
a Product. Such a profile binds that Composition's implementation and acceptance target. Once
Configuration selects a delivered registered revision and Containers admits its complete manifest,
the resulting configured installation is a Deployment; it still creates no Product, supported-use-
case catalogue, customer promise, or service before those gates.

A Product or use-case study may expose an unresolved application-ownership need. Until that need
resolves to an exact external authority or an accepted Composition revision, the Product must not
claim the affected use case as supported and no Invocation depending on that missing truth may be
admitted as a supported Product path. Product packaging never acquires the missing records,
judgment, policy, consent, secrets, or effect authority in the meantime.

An already-settled exact record, artifact, receipt, capability snapshot, Product co-packaging, or
exact external precondition whose lifecycle the consumer cannot manage does not by itself create a
Suite. A foreign reference grants no installation, availability, lifecycle, upgrade, credential,
admission, or effect authority. Suite is required when one result must initiate or admit, await,
retry, cancel, recover, correlate, or settle multiple Composition-owned Invocations. It pins member
and Pattern revisions, typed ArtifactRef/Intent handoffs, correlation, ceilings, dependencies, and
partial-completion law while never merging ownership, secrets, Sigils, HitL, or domain judgment.
A Suite has its own technical identity, authority-qualified publisher, and revision as soon as
that reusable live-coordination contract is published. Each Suite revision pins one exact
Suite-owned coordination Pattern revision—an immutable Scroll whose only application truth is
member identity, typed handoff, correlation, ceilings, cancellation/recovery, and aggregate
settlement. Its Casting opens a parent Suite Invocation and Run; every initiated member remains a
separate Composition Invocation and Run with its own owner and judgment. A direct Intent may
therefore resolve the Suite revision and its pinned Scroll without a Product, while a Product may
pin the same eligible Suite revision. Neither route grants the publisher or parent Run any member
authority.

Suite execution requires authority-qualified Suite publication, the Suite-to-Pattern pin,
parent and child identity/revision/closure, fan-out/join, budgets, cancel, Stasis, retry, effects,
compensation, and partial-settlement law before admission of any Suite Casting.

A Schedule makes one durable, deduplicated **Occurrence** for each firing and enters ordinary
admission. Spellweaver owns calendar/event meaning, service class, temporal eligibility,
priority/overlap/coalescing/revision, and the decision to admit or settle a missed firing. Workers
deliver and retry exact admitted hops; Dispatcher resolves capability; Orchestrator owns readiness.
A timer never calls a Graph node, model, Animator, or container.

Three semantic service classes govern admission; they are not broker queues:

| Service class | Contract |
| --- | --- |
| `foreground` | Eligible now and latency-sensitive. It receives preference, not a promise of immediate start or unsafe preemption. |
| `deadline_windowed` | Initial Invocation admission is no earlier than `not_before` and strictly before `latest_start_at`, with optional `finish_by`. An unadmitted firing at or beyond the latest-start bound settles explicitly without an Invocation. |
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

### Temporal admission and settlement (Designed)

These rules govern the designed Schedule and Occurrence contract. They add no executable
scheduler, store, Run status, event, or callable interface.

A firing has one recoverable identity within an authority-qualified stable Schedule. A calendar
source identifies its nominal firing and selected fold member when applicable; an external
trigger requires a source-qualified durable event identity. Input equality, delivery identity,
jitter, worker attempt, and arrival time do not identify a firing. A trigger without a recoverable
source-firing identity cannot claim durable deduplication. This is an identity requirement, not a
public identifier encoding.

Each source firing is assigned to one exact Schedule revision once. Assignment and revision
activation share serialized decision authority. Rediscovery first recovers the assignment by
stable Schedule and source firing, across all retained revisions; it never looks only under the
currently active revision. The assigned revision, immutable source content, Pattern and policy
revisions, calendar interpretation, resolved absolute bounds, and selected jitter remain with the
Occurrence. A replay returns that Occurrence and any admitted Invocation even after the original
Run is terminal. Changed immutable source content fails closed; a newly active policy revision
alone does not make an unchanged source replay conflicting content.

For a previously unassigned external event, the revision active at its first committed assignment
owns the firing. Activation and assignment cannot race to assign it twice. For calendar firings,
activation instead pins a disjoint, recoverable partition of the source firings between retained
revisions. This partition covers unresolved old firings as well as the cutover and new firings;
late discovery uses that partition, not the revision active when a relay happens to run. Existing
assignments cannot be changed by activation. A change of time zone, cadence, or fold policy must
pin which nominal candidates under the two calendar interpretations denote the same source
firing, which are distinct, and which are explicitly skipped under their assigned revision.
Civil timestamps in different zones are not a shared ordering. Activation is refused if the
partition is missing, ambiguous, or would reassign an existing firing. Two relays encountering
the same cutover firing must therefore recover one assigned revision and one Occurrence. These
requirements refine Schedule revision law; they introduce no separate registry or service.

Calendar revisions retain the exact zone-rule interpretation needed to reproduce unresolved
firings. Installing different zone rules requires another revision rather than silently
reinterpreting an existing one. Materialization retains resolved bounds and selected jitter;
redelivery and restart cannot resample or revise them. The default calendar policy selects the
earlier instant in a fold and explicitly skips a nonexistent civil firing without shifting it.
Recovery considers at most the newest still-eligible missed calendar firing for admission; older
unadmitted backlog is explicitly skipped. Eligibility follows the firing's service class and no
expired window is enlarged. Different fold, gap, or bounded catch-up policies must be pinned in
the Schedule revision.

Temporal decisions compare absolute UTC. Take a fresh trusted clock sample at the serialized
conditional transition, after acquiring its decision authority; retain that sample as
`decision_time` only if the exact atomic transaction commits. Transaction opening time, caller or
delivery timestamps, and acknowledgement time cannot substitute. A lost acknowledgement requires
observation of the exact durable decision; rollback leaves no accepted decision. This measures
the accepted decision, not the later physical visibility or acknowledgement of the commit. A
process may derive a fresh monotonic waiting budget from the retained absolute bounds but cannot
persist that process-local reading as recovery authority. Restart and clock correction require
another absolute check before an undecided transition; they never reopen a committed admission,
skip, expiry, or terminal settlement.

The `not_before`, `latest_start_at`, and optional `finish_by` predicates below apply only to
`deadline_windowed`. Foreground and spare-capacity firings retain their own eligibility contracts;
they require no invented cutoff or sentinel bound. Identity, revision assignment, deduplication,
recovery, authority, and overlap rules apply to every service class.

| Deadline-windowed boundary | Required transition |
| --- | --- |
| Initial admission | Admit only when `not_before <= decision_time < latest_start_at`, and strictly before any `finish_by`. The same atomic decision binds the Occurrence to one Invocation and its initial Run delivery. Before commit there is no admitted Invocation; afterwards publication and recovery preserve that exact admission. |
| Unadmitted expiry | At or after `latest_start_at`, or an earlier `finish_by`, settle the firing explicitly as missed without creating an Invocation. Before `not_before`, retain it outside a sleeping worker while neither upper bound has expired. This strict rule retires the previously Designed admitted-late option for this class; no pinned miss policy can authorize it. |
| Consent or delegate resume | Initial admission satisfies `latest_start_at` once; a later worker claim or first effect need not precede it. Resume preserves the exact persisted wait owner and pinned Pattern, and requires current authority and ordinary Workers, Graph, and HitL checks. An approval creates no new firing and renews no bound. |
| Finish acceptance | The requested finish is timely only when its pinned semantic evidence is accepted by the authoritative terminal Run decision at `decision_time < finish_by`. The required proof must already be valid when that decision samples time; the transaction retains the exact proof and temporal disposition together. An intermediate artifact, generic `DONE`, event, or projection cannot substitute for that proof. |
| Admitted finish expiry | At or after `finish_by`, absent a timely accepted finish, close forward-effect admission and record the unmet deadline. Every new forward-effect admission must check that bound; safety cannot depend on an expiry callback running on time. A committed expiry prevents later acceptance of a timely finish. Expiry alone establishes neither terminal Run truth nor proof that an effect stopped. |

The requested finish remains domain- and Scroll-owned. If it requires delivered speech, committed
text alone cannot satisfy it: speech or an explicitly admitted text-only fallback must be proved.
A separately settled destination result does not finish a Companion presentation or a Suite round
trip. Display is observational only when presentation is not itself the admitted result.

After finish expiry, preserve every already-started effect's identity, actual result, and
settlement obligations under its original safety budgets. Use the existing owning cancellation,
containment, and reconciliation contracts. A late result can resolve those obligations but cannot
retroactively satisfy `finish_by`, reopen a terminal job, or authorize replacement submission.
Unknown effects remain unresolved; required unresolved containment keeps the Run nonterminal under
[Workers](14-workers.md#terminal-settlement). These are temporal dispositions, not new Run statuses.
Without `finish_by`, `latest_start_at` supplies no completion-time promise.

The default overlap policy skips a new firing while any earlier Invocation of the same stable
Schedule is nonterminal, across all Schedule revisions. Consent, delegated work, cancellation,
and required unresolved containment keep that overlap live. Neither a released worker nor a
finish accepted only in memory releases it. A different overlap policy must be pinned; coalescing
still requires the Pattern-owned typed merge and preserves every member Occurrence.

Schedule timing does not change [Orchestrator](23-orchestrator.md) activation-cutoff law. Timely
actuator/adapter invocation or honest readiness confirmation retires that local admission cutoff;
subsequent settlement keeps its original safety budgets. An expired coalesced follower ends only
its own wait. Local coalescing and that process-local cutoff establish neither Occurrence identity
nor workflow settlement.

Canonical **Occurrence** means the schedule or external-trigger firing before Invocation admission.
The delivered Graph runtime's `occurrence_id` field is a legacy name for a station-attempt
correlation; it is not this durable trigger identity. No Occurrence store, timer, eligibility
engine, service-class persistence, safe preemption, or periodic workflow scheduler exists.

## Returning findings

Drift returns `CompositionSuiteFindingSet@1`, `AttributionCandidate@1`, `InvalidationSet@1`, and
`CorrectionRequest@1` as evidence. A Correction Request enters Spellweaver only as a new forward
Invocation under validation, budget, authority, and consent. It cannot create reverse edges,
resume an arbitrary old station, mutate an artifact, inherit consumer authority, or turn
recurrence into training. Repair begins at the smallest supported cut. Reuse needs full
input/evaluation closure, while unresolved attribution or exhausted budget ends the attempt honestly.

## Loom projection and drafting

[Loom](../divination/altar/loom.md) reads the fixed immutable Pattern manifest: semantic stations,
edges, Gate/delegate, revision, implementation revision, checkpoint schema, and digest.
Mermaid/canvas are views. Charcoal remains inert until a canonical declarative Pattern has typed
ports/state/effects/authority/termination/continuity. Drawn grouping does not nest a Pattern or
execute a Suite. Publication alone makes a new immutable revision; Invocations stay pinned. Model
prose, browser gesture, and renderer state are not authority.

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
conflicting and inherited lineage; unchanged moves, splits, marker deletion, and manifest changes;
base and candidate races; live-only refusal of preauthorization; exact affected-region review; and
proof that approving Agent output never relabels it `human_attested`.

The execution-road profile additionally requires complete local/Portal/A2A/delegated matrices;
manifest-undeclared and model-selected road refusal; consumer-specific Cut and target binding;
nested coding-agent child egress; capability/peer/runtime unavailability; pre- and post-submit
failure at every edge; new-attempt fallback; indeterminate reconciliation; quarantine/adoption; and
proof that a decision commits before admission, contains no live handle, is referenced by the
road-owned record/event, and never settles that ledger.
