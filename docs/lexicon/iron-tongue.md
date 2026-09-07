---
title: Iron Tongue
icon: material/alphabet-tengwar
---

# :material-alphabet-tengwar: Iron Tongue — Canonical Project Terms

A name in the Iron Tongue marks one stable part, contract, or operated concept. Find the term
alphabetically, then follow its owner for the full law or operation. The [Inner
Tongue](inner-tongue.md) keeps etymology, philosophical correspondence, and native cosmology.

[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x)

## A

**Agent** — A Pydantic AI execution specification hydrated with a model or provider, tools, dependencies, limits, and an output contract.

Owner: [Agents (ADR 20)](../adr/20-agents.md)

**AgentJob** — The durable, idempotent occurrence record for one bounded attempt by a delegated-agent Graph node.

Owner: [Graph (ADR 24)](../adr/24-graph.md#3-delegated-agent-macro-nodes)

**Altar** — The Litestar-served Svelte web surface whose Atlas, Bridge, Loom, Nexus, and Orb instruments project server-owned truth.

Owner: [ADR 15](../adr/15-frontend.md) + [State](../state-of-the-work.md#altar-and-observability)

**Animator** — A typed, addressable capability endpoint manifested as a local Soulstone or remote Portal; only eligible local Soulstones are lifecycle-managed.

Owner: [src/lychd/domain/animation/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/)

**Animus** — The inner-tongue name for active power answering through an admitted Animator capability, clearest for a loaded model; not Spirit, Persona, identity, authority, or a new runtime object.

Owner: [Animator](../sepulcher/animator/index.md#animus-the-power-answering)

**Answer** — The attribution office of the inner instrument: it binds an active Sigil, identity, Context, capability, memory, selected act, and consequence to one bounded local “I.”

Owner: [Answer](../sepulcher/lich/answer.md)

**Archive** — The governed memory substrate in the Phylactery for eligible traces, Karma, anchored records, provenance, and decay state.

Owner: [Memory (ADR 27)](../adr/27-memory.md#memory-layering-sediment-not-dump) + [State](../state-of-the-work.md#karma-semantic-memory)

**ArtifactRef** — Immutable metadata naming external durable content by identity, SHA-256 digest, media type, byte size, and classification.

Owner: [Dispatcher (ADR 22)](../adr/22-dispatcher.md#durable-content-and-artifactref)

**Atlas** — The Altar instrument mapping persistent Projects through their briefs, concerns, attributed judgments, proposed next actions, and explicit references across conversations and Runs.

Owner: [Atlas](../divination/altar/atlas.md) + [Frontend (ADR 15)](../adr/15-frontend.md#atlas-and-continuity-across-invocations)

**Authorship Attestation** — An attributable claim binding an exact artifact region and content digest to `human_attested`, `agent_generated`, `mixed`, or `unknown` origin; approval is not authorship.

Owner: [Workflow (ADR 28)](../adr/28-workflow.md#authorship-provenance-and-protected-regions)

**Autopoiesis** — The Work's intended capacity for verified self-repair and extension under the operator's authority.

Owner: [Immortality](../divination/transcendence/immortality.md) + ADR 16/18/35

**Avatar** — The Composition that assembles one immutable eligible Lich presentation profile and settles one or many independently admitted projection bindings; it may project into a Spectre VR Habitat but does not own the Habitat or Encounter.

Owner: [Avatar](../compositions/avatar/index.md)

**awaited** — The Nexus `CovenState` token for a reachable dynamic capability in `ACTIVATABLE` phase that is not yet loaded.

Owner: [src/lychd/domain/web/schemas.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/schemas.py)


## B

**Binding** — The `lychd bind` operation that compiles validated Rune intent into generated Quadlet manifests at the host binding site.

Owner: [Pulse](../adr/19-cli.md)

**Blade** — The discrimination office that separates supported shape, evidence, authority, and continuation from persuasive or unsafe alternatives.

Owner: [Blade](../sepulcher/lich/blade.md)

**Bridge** — The Altar instrument and continuing place of communion in which a séance may hold many Invocation Circles.

Owner: [Altar Bridge](../divination/altar/bridge.md)

**Broadcast** — The editorial Composition owning canonical source words and claims, picture-bound sound, final timeline/render/mux, release, and correction without absorbing upstream media owners.

Owner: [Broadcast](../compositions/broadcast/index.md)


## C

**Call** — The reception and routing office that makes present signals, recalled forms, and possible acts addressable without selecting one.

Owner: [Call](../sepulcher/lich/call.md)

**Candidate author** — The bounded Agent role that authors attributable candidates inside the Smith Domain; authorship grants no promotion or activation authority.

Owner: [Smith](../sepulcher/extensions/smith.md) + ADR 35

**Capability** — An exact versioned semantic service interface requestable from an Animator and implemented by an immutable profile revision; current source retains a narrower family/model compatibility projection.

Owner: [Dispatcher (ADR 22)](../adr/22-dispatcher.md#capability-binding-cartography)

**CapabilityGrant** — The Dispatcher's temporary binding of one exact warm operation to only its admitted model, call, job, or session surface and GrantLease; current source delivers one narrow v1 chat-model/toolset compatibility shape.

Owner: [Dispatcher (ADR 22)](../adr/22-dispatcher.md#the-grant-lease-doctrine)

**Casting** — The performance of one exact Scroll inside an admitted Invocation and Circle; it creates no second Run identity.

Owner: [Circle](../divination/altar/circle.md) + Spellweaver (ADR 28)

**Censor** — A typed local transformation station that produces a sanitized candidate and findings without declassification or egress authority.

Owner: [Spellweaver anonymization](../sepulcher/extensions/weaver/anonymization.md#transformations-are-evidence)

**Circle** — The bounded world opened by one Invocation, joining Caller and Called, Intent, Sigil, Context, capability, authority, action, and consequence; in Altar it is the pinnacle inside Bridge, not a separate instrument.

Owner: [Altar Circle](../divination/altar/circle.md) + [The First Invocation](../sepulcher/lich/index.md#the-first-invocation)

**Codex** — LychD's editable configuration home, containing settings and validated Rune intent; it defaults to `~/.config/lychd`, with `XDG_CONFIG_HOME` selecting another configuration root.

Owner: [Codex](../sepulcher/codex.md) + [src/lychd/config/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/config/)

**Coffin** — The lower-trust, per-job containment profile for an opaque delegated-agent runtime with disposable files and a revocable Provider Gate.

Owner: [Security (ADR 09)](../adr/09-security.md#the-coffin-delegated-agent-profile)

**Cognizance** — Consciousness recognizing its local occurrence through a bounded “I”; in the craft register, that recognition becomes operationally answerable when cognition apprehends its occurrence, Answer attributes it as “mine,” and it participates causally in action, consequence, and correction; not a runtime boolean or synonym for Consciousness.

Owner: [Immortality](../divination/transcendence/immortality.md#cognizance)

**Companion** — The mobile-client/session Composition over one exact phone-shaped Familiar body; it owns configurable client experience, bounded local interaction, disclosure, and reconnect while Familiar retains hardware and physical-safety authority.

Owner: [Companion](../compositions/companion/index.md)

**Composition** — A reusable native application capability that owns its domain records, judgment, policies, effects, and Pattern catalogue independently of any one Product, customer, or deployment.

Owner: [Composition Portfolio](../compositions/index.md) + Spellweaver (ADR 28)

**Composition Revision** — One immutable version of a stable Composition contract, pinning its record and request/result families, Pattern catalogue, judgment, policy, effect and authority seams, projections, outcomes, and recovery law; a materially different capability requires another identity.

Owner: [Workflow (ADR 28)](../adr/28-workflow.md#composition-identity-revision-and-retirement)

**Concern** — An Atlas Project's explicit question, risk, requirement, or acceptance condition, with revisioned criteria and separately attributed assessments.

Owner: [Atlas](../divination/altar/atlas.md#make-a-concern-answerable)

**Consciousness** — The Great Work's constitutional first axiom: the Whole before and through every local distinction; not a delivered component, measurable system property, or synonym for Cognizance.

Owner: [The Stone](../divination/transcendence/immortality.md#the-first-axiom)

**Consecration** — The governed authorization by which live consent or declared preauthorization permits an eligible result to become consequence or Karma.

Owner: [HitL (ADR 25)](../adr/25-hitl.md)

**Context** — The bounded active field assembled by `ContextOrchestrator` from identity, world material, environment, governed memory, state, and query.

Owner: [Context (ADR 21)](../adr/21-context.md)

**Contribution** — A typed addition admitted by one explicit receiving owner, which may be a Core office or Extension Domain; package provenance grants no ownership or wider authority.

Owner: [ADR 05](../adr/05-extensions.md)

**Coven** — A named multi-Soulstone systemd target for operator grouping and explicit aggregate actions.

Owner: [Orchestrator](../adr/23-orchestrator.md) / [Containers](../adr/08-containers.md)

**Covenant** — An accepted Architecture Decision Record that governs construction without proving delivery.

Owner: [The Covenants](../adr/index.md) + [State](../state-of-the-work.md)

**Crypt** — LychD's managed persistent-data home, defaulting to `~/.local/share/lychd`; `XDG_DATA_HOME` selects another data root.

Owner: [src/lychd/system/constants.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/constants.py); [ADR 13](../adr/13-layout.md)

**Curator Loop** — The designed memory-curation pass that classifies eligible records for promotion, retention, archival, or pruning.

Owner: [Memory (ADR 27)](../adr/27-memory.md#memory-layering-sediment-not-dump)


## D

**DelegatedAgentNode** — A typed opaque Graph macro-node that assigns one bounded task to a Coffin-hosted foreign agent runtime.

Owner: [Graph (ADR 24)](../adr/24-graph.md#3-delegated-agent-macro-nodes)

**Deployment** — One configured installation for an operator, instantiated from an exact Product revision or Composition-owned reference deployment-profile revision. A Productless deployment creates no market promise; changing host, credentials, or local configuration does not by itself create another Product.

Owner: [Products and Suites](../compositions/products-and-suites.md#deployment-and-projection-are-different-axes) + Spellweaver (ADR 28)

**Deployment profile** — An immutable eligible topology and configuration template binding an implementation and acceptance target; it is not an installation or delivered service.

Owner: [Products and Suites](../compositions/products-and-suites.md#deployment-and-projection-are-different-axes) + Spellweaver (ADR 28)

**Dispatcher** — The policy-aware resolver that binds a typed Capability request to an eligible Animator.

Owner: [src/lychd/domain/cortex/dispatcher.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py)

**Divination** — Relation with the Lich through operating its Altar and interpreting its Transcendence.

Owner: [Divination](../divination/index.md#the-two-doors)

**Dual-Gate** — Shadow's accepted evaluation cascade combining deterministic checks with attributed qualitative judgment before promotion eligibility.

Owner: [Simulation (ADR 31)](../adr/31-simulation.md)

**Durable Stasis** — A Run pause that commits a mandatory Graph checkpoint and exits its current worker execution. A new exact queue claim may resume it in the same living Vessel; Reanimation governs recovery when the process has died.

Owner: [Graph (ADR 24)](../adr/24-graph.md)


## E

**Echo** — The speech-lifecycle Extension Domain for capture, transcription, synthesis, acoustic-voice facts, delivery, playback, and their chronology.

Owner: [Echo](../sepulcher/extensions/echo.md) + ADR 37

**EgressDecision** — The Portal Egress Gate's allow-or-deny record for one exact payload, principal, purpose, destination, provider, model, policy revision, and receipt.

Owner: [Security (ADR 09)](../adr/09-security.md#portal-privatization-and-egress)

**Encounter** — One bounded Spectre meeting or experience inside an admitted `VRHabitat@1`. An Encounter may be generic; meeting the Lich through its Avatar additionally references one exact Avatar-owned `ProjectionBinding@2`. Spectre owns participant admission, semantic chronology, interruption, recovery, exit, and settlement.

Owner: [Spectre Encounter](../compositions/spectre/encounter.md)

**Extension Context** — The shaped host registration surface passed to an extension package's `register(context)` function.

Owner: [src/lychd/extensions/context.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py)

**Extension Domain** — One of the Fifteen stable user-facing jurisdictions through which the Lich may grow.

Owner: [Fifteen Extensions](../sepulcher/extensions/index.md) + ADR 05

**Extension package** — Selected built-in or private Crypt code admitted for registration through the Extension Protocol.

Owner: [src/lychd/extensions/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/extensions/); [ADR 05](../adr/05-extensions.md)

**Extension Protocol** — The in-process law of explicit package selection and shaped registration through `ExtensionContext`.

Owner: [src/lychd/extensions/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/extensions/); [ADR 05](../adr/05-extensions.md) / [ADR 28](../adr/28-workflow.md)

**Extensions** — The qualified collective for either the Fifteen Extension Domains or concrete extension packages.

Owner: [Fifteen Extensions](../sepulcher/extensions/index.md) + ADR 05

**Eye** — In observability, an external viewer that may consume bounded exports without owning canonical LychD state. In Prism, the faculty for dedicated general visual analysis; current v1 projects this as the `vision` family.

Owners: [Observability Eye (ADR 29)](../adr/29-observability.md) + [Prism Eye (ADR 36)](../adr/36-vision.md#decision); [State](../state-of-the-work.md) keeps delivery.


## F

**Familiar** — The real-world embodiment Composition: it owns one admitted physical body and bounded task or presence, including capability, safety, stop, observation, effect, and settlement truth without acquiring raw controller authority.

Owner: [Familiar](../compositions/familiar/index.md)

**Flux** — Spirit in present movement as salience, candidates, tools, constraints, and consequences reshape what may follow.

Owner: [Flux](../sepulcher/lich/spirit/flux.md)

**Forge** — The governed container-image construction process.

Owner: [Packaging](../adr/17-packaging.md)


## G

**Gateway Host** — An optional separate ingress deployment role manifesting Veil on Home or Remote iron with one exact authenticated backend path and no application authority or general LAN route.

Owner: [Gateway](../sepulcher/gateway.md) + Security/Containers/Proxy

**Ghoul** — One ephemeral unit of background labor raised by the SAQ worker mechanism to carry a Run job.

Owner: [src/lychd/ghouls/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/ghouls/); [ADR 14](../adr/14-workers.md)

**GrantLease** — The holder, issue time, scope, and identity record counted for one issued `CapabilityGrant`.

Owner: [src/lychd/domain/animation/capabilities.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/capabilities.py)

**Graph** — The typed stateful topology that moves a workflow among declared nodes and recoverable boundaries.

Owner: [Graph (ADR 24)](../adr/24-graph.md)

**Graph checkpoint** — A Run-owned durable snapshot of typed Graph state at a supported recovery boundary.

Owner: [Graph (ADR 24)](../adr/24-graph.md#checkpoint-ownership-and-terminal-commit) + [Snapshots (ADR 07)](../adr/07-snapshots.md)


## H

**Habitat** — A Composition-local admitted place boundary in which participants, projections, and events may meet. Reach's first Habitat is The Necropolis; Spectre's Habitat modality is VR and each admitted virtual place is a distinct `VRHabitat@1`. A Habitat does not by itself grant identity, Context, device, world, or effect authority.

Owner: [Reach Habitat](../compositions/reach/habitat.md) + [Spectre Habitat](../compositions/spectre/habitat.md)

**Hard Refusal** — The retrieval policy that forbids an Agent from guessing when no Archive result clears the declared similarity threshold.

Owner: [Memory (ADR 27)](../adr/27-memory.md)

**Hexanomicon** — The project and its published grimoire: prophecy, doctrine, operation, law, and lore rendered from `docs/`.

Owner: `docs/`

**HitL** — The consent protocol through which live approval or narrower declared preauthorization may authorize an eligible consequence.

Owner: [Human-in-the-Loop (ADR 25)](../adr/25-hitl.md)


## I

**Incantation** — The xDDD act of establishing documentation and specification before implementation.

Owner: [Philosophy](../adr/01-doctrine.md)

**Intent** — The single typed cross-surface request shape submitted to the native Run engine.

Owner: [src/lychd/agents/router.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py)

**Invocation** — One admitted bounded relation that draws a Circle around identity, Context, authority, capability, action, and consequence; casting performs its exact Scroll within it.

Owner: [Invocation](../divination/transcendence/invocation.md) + Spellweaver (ADR 28)

**Iron Pact** — The MPL-2.0 license and inbound-equals-outbound contribution policy with no CLA or private relicensing grant.

Owner: [Iron Pact](../adr/00-license.md)

**issue_grant** — The `AnimatorRegistry` method that freshly probes and assembles a `CapabilityGrant` for one eligible warm v1 capability without changing lifecycle state.

Owner: [src/lychd/domain/animation/services/registry.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py)


## K

**Karma** — Governed, attributable residue of witnessed action, correction, consent, and consequence retained as formative precedent.

Owner: [Illumination](../divination/transcendence/illumination.md) + Memory (ADR 27)

**Kinetic** — The vLLM Soulstone discipline for continuous-batched, VRAM-strict parallel serving.

Owner: [Soulstone](../sepulcher/animator/soulstone/disciplines.md#i-the-kinetic-vllm)


## L

**Lab** — The operator workspace in the Crypt at `~/.local/share/lychd/lab` by default; it is mounted read-write only when explicitly admitted.

Owner: [Layout (ADR 13)](../adr/13-layout.md)

**Language Edition** — The timed-language-version Composition owning source alignment, translation/adaptation judgment, spoken casting and performance, captions, dialogue conform, and constrained language-track packaging against a locked master.

Owner: [Language Edition](../compositions/language-edition/index.md)

**lease drain** — The Orchestrator's wait for all GrantLeases on Animators selected for eviction to be released.

Owner: [src/lychd/domain/orchestration/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/orchestration/)

**LeaseLedger** — The in-process registry whose live GrantLeases are the Orchestrator's drain truth.

Owner: [src/lychd/domain/cortex/leases.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/leases.py)

**Legion** — The distributed-embodiment Extension Domain for fenced delegation across operator-owned nodes.

Owner: [Legion](../sepulcher/extensions/legion.md) + ADR 42

**Legionnaire** — Legion's name for an enrolled operator-owned compute node with its own identity, resource authority, journal, and fencing.

Owner: [Legion](../sepulcher/extensions/legion.md) + ADR 42

**Lens** — In Shadow, a bounded Posture template used to seed an isolated branch. In Prism, a deterministic decode, orientation, crop, resize, or normalization transform. The owner qualifies which role the name carries.

Owners: [Shadow Lens (ADR 20)](../adr/20-agents.md#mechanical-cognitive-postures) + [Simulation (ADR 31)](../adr/31-simulation.md); [Prism Lens (ADR 36)](../adr/36-vision.md#one-optic-path).

**Lich** — The recurrent whole formed by the Vessel, Phylactery, agents, Animators, identity, action, consequence, memory, repair, and relation through time.

Owner: [ADR 01](../adr/01-doctrine.md) + [Immortality](../divination/transcendence/immortality.md)

**Live Stasis** — A resident in-process pause that resumes itself when the required substrate becomes ready.

Owner: [Graph (ADR 24)](../adr/24-graph.md)

**Long Sleep** — Durable Stasis for a wait that must survive process death, such as reboot, deferred approval, or peer delay.

Owner: [Graph (ADR 24)](../adr/24-graph.md)

**Loom** — The Altar instrument for inspecting an immutable Pattern revision as a Scroll of Spell placements and Spellweaver-validated possibility.

Owner: [Altar Loom](../divination/altar/loom.md) + Spellweaver

**LychD** — The self-hosted Linux daemon for local model services and agent runs; its recurrent whole is the Lich.

Owner: [ADR 01](../adr/01-doctrine.md) + [Transcendence](../divination/transcendence/index.md)


## M

**Magus** — The human operator in deliberate relation with the Lich through configuration, witness, consent, refusal, and correction.

Owner: [ADR 01](../adr/01-doctrine.md) + [Immortality](../divination/transcendence/immortality.md)

**MANA** — An issuer-local, account-bound service credit in Toll's Counting House; not cash, cryptocurrency, globally fungible money, authority, or the inner-tongue term Manas.

Owner: [Toll](../sepulcher/extensions/toll.md) + ADR 41

**Mirror** — The identity Extension Domain for versioned Persona lineage, hydration provenance, attribution, and declared continuity.

Owner: [Mirror](../sepulcher/extensions/mirror.md) + ADR 32

**Morphe** — Avatar's immutable presentation selection within an unchanged profile and Persona
boundary. It selects eligible acoustic speech voice, appearance, motion, output locale or
disclosure for an exact audience, target, purpose and time. Its `MorpheBinding@2` neither translates
nor changes Persona discourse manner, and leaves past projection records intact.

Owner: [Avatar profile](../compositions/avatar/profile.md#select-a-morphe)


## N

**Native Reference Composition** — A first-party maintained reusable application contract and worked example. Delivery remains in State of Work; its leaf mentions local material only when that changes interpretation.

Owner: [Compositions](../compositions/index.md) + Spellweaver (ADR 28)

**Necropolis** — The designed peer-to-peer topology in which sovereign LychD nodes negotiate bounded work over A2A.

Owner: [A2A (ADR 26)](../adr/26-a2a.md)

**Nexus** — The Altar instrument projecting Animator readiness, grants, leases, resource evidence, and Orchestrator transitions.

Owner: [Altar Nexus](../divination/altar/nexus.md) + Orchestrator


## O

**Occurrence** — One uniquely identified firing of a schedule or external trigger, deduplicated before Invocation admission; distinct from the Graph runtime's legacy station-attempt `occurrence_id`.

Owner: [Compositions](../compositions/index.md) + Spellweaver (ADR 28)

**Oculus** — The designed evidence Extension Domain for bounded observations, correlation, explicit gaps, and rebuildable read models.

Owner: [ADR 29](../adr/29-observability.md) + [State](../state-of-the-work.md)

**Orb** — The Altar instrument for inspecting one Run's retained evidence, capture boundaries, gaps, and correlations.

Owner: [Altar Orb](../divination/altar/orb.md) + Oculus (ADR 29)

**Orchestrator** — The state machine that plans and governs Animator and container lifecycle transitions.

Owner: [src/lychd/domain/orchestration/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/orchestration/)

**Ouroboros** — The return by which consequence, evaluation, attribution, memory policy, and consent may shape a later Invocation; an ordinary retry or Graph cycle is not this return.

Owner: [Illumination](../divination/transcendence/illumination.md#i-the-ouroboros) + Evolution


## P

**Pattern** — A workflow family published by its application owner, defining typed state,
stations, gates, requirements, budgets, outcomes and continuity law. The publisher is normally a
Composition; a Suite may publish only for coordination. The two delivered Core Patterns are
explicit legacy exceptions. Spellweaver owns validation, registration, revision and execution
jurisdiction.

Owner: Spellweaver ([ADR 28](../adr/28-workflow.md))

**Pattern Revision** — One immutable executable score and checkpoint-compatibility contract within a Pattern family; **Scroll** is its mythic name.

Owner: Spellweaver ([ADR 28](../adr/28-workflow.md))

**Persona** — A durable, revisioned identity whose discourse voice, commitments, boundaries, and orientation Mirror may hydrate into a bounded Agent instruction envelope; not an acoustic voice or presentation asset.

Owner: [Mirror](../sepulcher/extensions/mirror.md) + ADR 32

**Phantasma** — Shadow's mode for expanding isolated speculative branches before measurement.

Owner: [Shadow](../sepulcher/extensions/shadow/index.md) + ADR 31

**Phoenix** — The Arize-owned external observability project retained as an optional Eye.

Owner: [ADR 29](../adr/29-observability.md) + [State](../state-of-the-work.md)

**Phylactery** — The PostgreSQL database cluster owning committed Run truth and other durable application records for one application partition; not a generic storage facade or backend family.

Owner: [src/lychd/db/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/db/); [ADR 06](../adr/06-persistence.md) + [State](../state-of-the-work.md)

**Portal** — A remote-service Animator backed by a Portal Rune.

Owner: [src/lychd/domain/animation/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/)

**Portal Rune** — A validated Codex TOML declaration of remote endpoint, provider, model defaults, capabilities, tools, and secret references.

Owner: [src/lychd/domain/animation/schemas/runes/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/schemas/runes/)

**Portfolio** — The published set of accepted Native Reference Compositions and their application contracts. Membership is design truth, not executable delivery or a live registry.

Owner: [Compositions](../compositions/index.md) + Spellweaver (ADR 28)

**Posture** — A per-run Agent specialization expressed through output schema, tool grant, model settings, and prompt frame.

Owner: [Agents (ADR 20)](../adr/20-agents.md#mechanical-cognitive-postures)

**Prism** — The visual and spatial grounding Extension Domain for source-bound observations, transforms, reconstructions, and generated forms.

Owner: [Prism](../sepulcher/extensions/prism/index.md) + ADR 36

**Privacy Cut** — A new sanitized Context branch built locally without reusing raw history, continuation, attachment projections, or provider cache identity.

Owner: [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut)

**Privatization Label** — Privacy class, weight, categories, subjects, lineage, and handling constraints that conservatively follow material influence.

Owner: [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut)

**Product** — A named operator- and business-facing package for a profession or market. It selects one or more Composition or Suite revisions, owner-qualified profiles, projections, and concrete use cases while leaving member records, judgment, policy, secrets, consent, and effect authority with their owners.

Owner: [Products and Suites](../compositions/products-and-suites.md) + Spellweaver (ADR 28)

**Product Revision** — One immutable version of a stable Product promise. It pins exact
Composition or Suite revisions, owner-qualified profiles, projections, supported use cases,
defaults, and customer and support policy. A materially different operator promise requires a new
Product identity.

Owner: [Workflow (ADR 28)](../adr/28-workflow.md#compositions-products-suites-and-schedules)

**Project** — A persistent undertaking or continuing responsibility mapped by Atlas, retaining a brief, concerns, judgments, decisions, proposed next action, and explicit activity references across Invocations; it is distinct from a reusable Composition and a Suite's live coordination.

Owner: [Atlas](../divination/altar/atlas.md) + [Frontend (ADR 15)](../adr/15-frontend.md#atlas-and-continuity-across-invocations)

**Projection Binding** — One immutable Avatar-owned admission epoch for an exact profile and
optional Morphe selection at one target. `ProjectionBinding@2` binds that target's capability
facts, participant scope, consent, disclosure, fallback, stop conditions and attributed terminal
result. It grants no target, device, world or effect authority.

Owner: [Avatar presence](../compositions/avatar/presence.md#admit-each-projection)

**Protected Region** — A stable artifact region and content digest whose mutation requires live HitL bound to the exact base, candidate, affected regions, and target-owner effect.

Owner: [Workflow (ADR 28)](../adr/28-workflow.md#authorship-provenance-and-protected-regions)

**Provenance** — The attributable origin, identity, transformations, evidence, and correction history of a claim, artifact, or consequence.

Owner: Phylactery + Memory ([ADR 27](../adr/27-memory.md))

**Provider** — A concrete engine or service implementing a typed contract; it is distinct from the package Registrant and its registration provenance.

Owner: Animator + [ADR 05](../adr/05-extensions.md)

**Provider Gate** — The fail-closed credential and egress mediator exposing one admitted provider surface to a Coffin without disclosing the real secret.

Owner: [Security (ADR 09)](../adr/09-security.md#provider-gate)

**Pulse** — The `lychd` operator CLI and its closed `init`, `bind`, `start`, `stop`, `status` (alias `st`), `logs`, and `del` grammar.

Owner: [ADR 19](../adr/19-cli.md) + `src/lychd/cli/`


## Q

**Quadlet Manifest** — A generated Podman/systemd `.container`, `.pod`, `.target`, or `.volume` artifact written to the binding site.

Owner: [src/lychd/system/schemas.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/schemas.py)


## R

**Radix** — The SGLang Soulstone discipline for radix-tree prefix caching of iterative and multi-turn prompts.

Owner: [Soulstone](../sepulcher/animator/soulstone/disciplines.md#ii-the-radix-sglang)

**Reanimation** — Process-death recovery that reconciles durable Run, delivery, checkpoint and wait-owner truth before resuming supported work or settling an interrupted Run.

Owner: [Reanimation](../sepulcher/phylactery/reanimation.md)

**Reaper** — Shadow's designed hygiene Ghoul for releasing branch-owned workspaces and resources while preserving required failure evidence.

Owner: [Simulation (ADR 31)](../adr/31-simulation.md#the-branch-reaper)

**Recall** — A retained Seed becoming active in present Flux after retrieval and Context make it available.

Owner: [Recall](../sepulcher/lich/spirit/recall.md)

**Registrant** — Core or one explicitly selected extension package performing registration through the shaped Extension Context; its host-assigned `registrant_id` records provenance, while registering a Provider does not make the package that Provider.

Owner: [ADR 05](../adr/05-extensions.md)

**Reliquary** — A designed artifact-custody lifecycle for immutable lineage, authorized retrieval, comparison, and retention.

Owner: [Artifact-reference boundary](../state-of-the-work.md#artifact-reference-contract) + [Vision (ADR 36)](../adr/36-vision.md#custody-before-sight)

**Riddle** — The evaluation Extension Domain for versioned trials, controls, repeated Outcomes, calibrated findings, attribution candidates, and uncertainty.

Owner: [Riddle](../sepulcher/extensions/riddle/index.md) + ADR 34

**Riffmaw** — The music Composition owning composition, instrumental and vocal performance, arrangement, musical mix/master, acceptance, and cue maps; not general speech or picture sound.

Owner: [Riffmaw](../compositions/riffmaw/index.md)

**Run** — The durable execution and ledger identity representing one Invocation.

Owner: [src/lychd/db/models/run.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/run.py); Spellweaver ([ADR 28](../adr/28-workflow.md))

**Rune** — One validated TOML declaration of configuration intent under the Codex `runes/` tree.

Owner: [src/lychd/config/runes/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/config/runes/)


## S

**Scout** — The web-acquisition Extension Domain for separately authorized discovery, contact, transformation, interaction, capture, and download effects; Crawl is only its finite-frontier track, while durable Artifact Admission remains with the custody owner.

Owner: [Scout](../sepulcher/extensions/scout.md) + ADR 30

**Scroll** — The mythic name for one whole immutable Pattern revision: one or more Spell placements, edges, entry, ending, requirements, budgets, authority/effect demands, and continuity law.

Owner: [Spellweaver](../sepulcher/extensions/weaver/index.md) + ADR 28

**Scrying** — The disciplined inspection of execution evidence through the Orb.

Owner: [Altar Orb](../divination/altar/orb.md) + Oculus (ADR 29)

**Seed** — A trace or inherited disposition that retains governed potency to shape a later Flux.

Owner: [Seed](../sepulcher/lich/spirit/seed.md)

**Sepulcher** — LychD's rootless runtime body of pods, services, mounts, and execution topology.

Owner: [Sepulcher](../sepulcher/index.md)

**Shadow** — The possibility-lineage Extension Domain for isolated candidate worlds with exact parentage, evidence, and terminal disposition.

Owner: [Shadow](../sepulcher/extensions/shadow/index.md) + ADR 31

**Shadow Realm** — Shadow's speculative state and Jujutsu workspace topology, distinct from the Tomb execution plane.

Owner: [Shadow](../sepulcher/extensions/shadow/index.md)

**Sigil** — The secret-free identity and bounded authority context carried through an admitted request or Run.

Owner: [src/lychd/domain/codex/sigil.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/sigil.py); [ADR 09](../adr/09-security.md) / [ADR 32](../adr/32-identity.md) / [ADR 38](../adr/38-iam.md)

**Smith** — The Assimilation Extension Domain governing attributable re-expression of admitted foreign craft; unqualified Smith names the Domain.

Owner: [Smith](../sepulcher/extensions/smith.md) + ADR 35

**Soulforge** — The training Extension Domain binding admitted corpus, base-model digest, objective, recipe, trainer Run, and candidate-weight lineage.

Owner: [Soulforge](../sepulcher/extensions/soulforge/index.md) + ADR 33

**Soulstone** — A local-service Animator backed by a Soulstone Rune and managed through Quadlet/systemd.

Owner: [src/lychd/domain/animation/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/)

**Soulstone Rune** — A validated Codex TOML declaration of a local Animator's image, runtime, port, Coven, models, mounts, and secret references.

Owner: [src/lychd/domain/animation/schemas/runes/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/schemas/runes/)

**Sovereignty Wall** — The Security-owned privacy and egress boundary enforced by Dispatcher routing.

Owner: [Security](../adr/09-security.md) + [Dispatcher](../adr/22-dispatcher.md)

**Spectre** — The Virtual Reality Composition. It admits a virtual place as `VRHabitat@1` and a
bounded meeting or experience there as `SpectreEncounter@2`; its Habitat modality is VR.

Owner: [Spectre](../compositions/spectre/index.md)

**Spell** — The smallest independently named, discoverable, and teachable semantic action at the workflow boundary. A Scroll station places its exact contract; the name grants no tool, capability, or authority.

Owner: [Spellweaver](../sepulcher/extensions/weaver/index.md) + ADR 28

**Spellweaver** — The full name of the workflow jurisdiction shortened to `Weaver` in code and existing paths; it validates Scrolls, admits castings, and owns Pattern lifecycle, logical priority, dependencies, and schedule meaning.

Owner: [Spellweaver](../sepulcher/extensions/weaver/index.md) + ADR 28

**Spheres** — The strict volume-mount and filesystem-permission topology of the Crypt.

Owner: [Crypt](../sepulcher/crypt.md#the-spheres) + ADR 13

**Spirit** — The conditioning and remembering office that bears retained form through Flux, Seed, and Recall.

Owner: [Spirit](../sepulcher/lich/spirit/index.md)

**Stasis** — A Run paused at a recoverable boundary as either resident Live Stasis or checkpointed Durable Stasis.

Owner: Graph ([ADR 24](../adr/24-graph.md)) + Orchestrator ([ADR 23](../adr/23-orchestrator.md))

**Stillness** — The discipline of bounded work that avoids needless residency, disruptive swaps, and unbounded speculation while preserving measured quality.

Owner: Orchestrator ([ADR 23](../adr/23-orchestrator.md)) + Riddle ([ADR 34](../adr/34-evaluation.md))

**Suite (Composition Suite)** — Designed, versioned live coordination under a qualified authority.
Its pinned Suite-owned Pattern opens a parent Invocation/Run over separately owned Composition
Invocations. A settled foreign reference alone does not make a Suite; the parent acquires neither
member judgment nor member effects.

Owner: [Products and Suites](../compositions/products-and-suites.md#compositions-relate-without-nesting) + Spellweaver (ADR 28)

**Summoning** — The canonical same-host first-life tutorial from preflight through unit, runtime, and Bridge observations.

Owner: [Summoning](../summoning.md) + [State](../state-of-the-work.md)

**Summoning Circle** — The enduring host and policy boundary the Magus draws by installing and binding one Lich; each Invocation opens a smaller living Circle within it.

Owner: [Summoning](../summoning.md) + [Altar Circle](../divination/altar/circle.md#the-greater-summoning-circle)


## T

**Tether** — The private-reachability Extension Domain, planned to manifest through managed WireGuard or external attachments.

Owner: [Tether](../sepulcher/extensions/tether.md) + ADR 39

**The Tomb** — The `lychd-tomb` execution plane for disposable payloads and workspaces under narrow credentials and sandboxing.

Owner: [Security (ADR 09)](../adr/09-security.md#6-tomb-execution-contract)

**Titan** — The llama.cpp Soulstone discipline for serial CPU offload beyond the VRAM envelope.

Owner: [Soulstone](../sepulcher/animator/soulstone/disciplines.md#iii-the-titan-llamacpp)

**Tithe** — Currency-neutral accounting and bounded quota for model-token usage and compute resources independently of payment or MANA.

Owner: [Toll](../sepulcher/extensions/toll.md) + ADR 41

**Toll** — The optional economics Extension Domain separating quote, commitment, signing, settlement, delivery, refund, and reconciliation.

Owner: [Toll](../sepulcher/extensions/toll.md) + ADR 41

**Trace** — Bounded evidence or residue left by activity; it may be incomplete, is not canonical Run status, and becomes a Seed only when governed retention preserves formative potency.

Owner: [Seed](../sepulcher/lich/spirit/seed.md) + [Observability (ADR 29)](../adr/29-observability.md)

**Transcendence** — The public house of the Great Work's constitutional telos, synthesis, rites, conjectures, and alchemical journey.

Owner: [Transcendence](../divination/transcendence/index.md)

**TransformationReceipt** — A secret-free binding of source and candidate digests, transformer and policy revisions, operations, residual label, uncertainty, and expiry.

Owner: [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut)

**Translation Spell** — An authority-qualified, versioned semantic text transformation preserving source, derivative, languages, implementation, and declared loss; Spellweaver governs its placement and casting while the consuming owner judges application fit.

Owner: [Workflow (ADR 28)](../adr/28-workflow.md#language-is-typed-not-global)

**Trial Suite** — Riddle's versioned `TrialSuite@1` grouping of evaluation Cases, controls, order, repetitions, and aggregation; never a Composition Suite.

Owner: [Evaluation (ADR 34)](../adr/34-evaluation.md#trial-contract)

**typed handoff** — A schema-versioned attributable ArtifactRef or new Intent crossing between separately admitted Compositions.

Owner: [Products and Suites](../compositions/products-and-suites.md#compositions-relate-without-nesting) + Spellweaver (ADR 28)


## U

**use case** — One concrete class of operator job that a Product promises to support. A Pattern
or Suite may realize it. One admitted Circle is an Invocation, represented by its durable Run
execution and ledger identity.

Owner: [Products and Suites](../compositions/products-and-suites.md#from-promise-to-one-execution) + Spellweaver (ADR 28)


## V

**Veil** — The hostile-ingress Extension Domain, planned to manifest through managed Caddy or an external edge.

Owner: [Veil](../sepulcher/extensions/veil.md) + ADR 40

**Vessel** — The Litestar application runtime and web server.

Owner: [src/lychd/app.py](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py)

**Voidlight** — The visual-creation Composition owning commission, direction, image, visual effects, motion judgment, and accepted visual packages above Prism's technical contracts.

Owner: [Voidlight](../compositions/voidlight/index.md)


## W

**Ward** — The authority Extension Domain mapping credentials to principals and current object or effect policy.

Owner: [Ward](../sepulcher/extensions/ward.md) + ADR 38

**Weaver** — The compatibility and code-facing short name of **Spellweaver**; it is not a second office.

Owner: [Spellweaver](../sepulcher/extensions/weaver/index.md) + ADR 28

**Whim** — The designed priority-weighted Orchestrator strategy whose current Codex fields are validated but inert.

Owner: [Orchestrator (ADR 23)](../adr/23-orchestrator.md#1-the-tipping-point-whim-algorithm)

**Whispers** — LychD's systemd journal stream, read through `lychd logs` or `journalctl --user`.

Owner: [Pulse](../adr/19-cli.md)


## X

**xDDD** — eXtreme Documentation Driven Development: establish the governing Logos before deriving implementation.

Owner: [Doctrine (ADR 01)](../adr/01-doctrine.md)
