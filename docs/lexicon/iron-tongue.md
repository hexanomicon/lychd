---
title: Iron Tongue
icon: material/alphabet-tengwar
---

# :material-alphabet-tengwar: Iron Tongue

<span id="iron-tongue-canonical-project-terms"></span>

Use these names to distinguish what the Lich's body does. The Vessel runs; the Phylactery keeps
committed truth; a Rune declares intent; a Scroll gives work its score. The dictionary keeps each
meaning brief and links it to the page that develops its anatomy, law, or operation.

Find the word by letter, then follow its owning link for detail. For delivery, consult
[State of Work](../state-of-the-work.md); for the histories and philosophical meanings within the
names, turn to the [Inner Tongue](inner-tongue.md).

[A](#a) · [B](#b) · [C](#c) · [D](#d) · [E](#e) · [F](#f) · [G](#g) · [H](#h) · [I](#i) · [K](#k) · [L](#l) · [M](#m) · [N](#n) · [O](#o) · [P](#p) · [Q](#q) · [R](#r) · [S](#s) · [T](#t) · [U](#u) · [V](#v) · [W](#w) · [X](#x)

## A

### [Agent](../adr/20-agents.md) { #agent }

An execution specification that gives Pydantic AI a model or provider, tools, dependencies,
limits, and an output contract.

### [AgentJob](../adr/24-graph.md#3-delegated-agent-macro-nodes) { #agentjob }

The durable, idempotent occurrence record for one bounded attempt by a delegated-agent Graph
node.

### [Altar](../adr/15-frontend.md) { #altar }

The place where the Magus meets the running Lich. Its five instruments—Atlas, Bridge, Loom,
Nexus, and Orb—show server-owned truth through a Svelte web interface served by Litestar.

[State of Work](../state-of-the-work.md#altar-and-observability)

### [Animator](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/) { #animator }

An address at which a typed capability can answer: a local Soulstone or a remote Portal.
Lifecycle control belongs only to eligible local Soulstones.

### [Animus](../sepulcher/animator/index.md#animus-the-power-answering) { #animus }

The active power answering through an admitted Animator capability, most plainly a loaded model.
The name belongs to the Inner Tongue; it adds no runtime object and confers neither Persona nor
identity nor authority. Spirit names a different office.

### [Answer](../sepulcher/lich/answer.md) { #answer }

The office that binds cognition, act, and consequence to one bounded local “I.” It joins the
active Sigil, identity, Context, capability, memory, and selected act in that attribution.

### [Archive](../adr/27-memory.md#memory-layering-sediment-not-dump) { #archive }

The governed memory within the Phylactery. It holds eligible traces, Karma, anchored records,
provenance, and decay state under their admission and lifecycle rules.

[State of Work](../state-of-the-work.md#karma-semantic-memory)

### [Area (Composition Area)](../compositions/index.md#areas) { #area }

A thematic route for discovering Compositions. Areas may overlap; each Composition keeps its own
home, records, judgment, and authority. A Suite can coordinate live work within or across them.

[Covenant 28: Workflow](../adr/28-workflow.md#areas-for-discovery)

### [ArtifactRef](../adr/22-dispatcher.md#durable-content-and-artifactref) { #artifactref }

An immutable reference to durable content held outside the record. It identifies the content
and carries its SHA-256 digest, media type, byte size, and classification, allowing a recipient
to know exactly which artifact is meant.

### [Atelier](../compositions/atelier/index.md) { #atelier }

The Composition for directing and judging visual creation. It owns the commission and creative
direction, image and visual effects, motion judgment, and acceptance of visual packages. Prism
supplies the technical contracts beneath those creative decisions.

### [Atlas](../divination/altar/atlas.md) { #atlas }

The Altar’s map of Concerns: how they divide, where they are addressed, and what judgment and
evidence bear on them. A Project can supply undertaking context; the initial delivered Atlas
requires one.

[Covenant 15: Frontend](../adr/15-frontend.md#atlas-and-continuity-across-invocations)

### [Authorship Attestation](../adr/28-workflow.md#authorship-provenance-and-protected-regions) { #authorship-attestation }

An attributable, recorded claim about who authored a particular part of an artifact. It binds that exact region
and its content digest to `human_attested`, `agent_generated`, `mixed`, or `unknown` origin.
Approving the artifact is a different act and does not establish authorship.

### [Autopoiesis](../divination/transcendence/immortality.md) { #autopoiesis }

The Work's intended capacity for verified self-repair and extension under the operator's
authority.

[Covenant 16](../adr/16-sdlc.md) · [Covenant 18](../adr/18-evolution.md) · [Covenant 35](../adr/35-assimilation.md)

### [Avatar](../compositions/avatar/index.md) { #avatar }

The Composition that chooses how the Lich will present itself. It assembles one fixed presentation
profile that meets the applicable requirements, then settles its independently admitted use at
one or more destinations. Each use has its own projection binding; the destination keeps its
authority over the place and effects. Avatar may present the Lich in a Spectre VR Habitat;
Spectre still owns that place and the Encounter within it.

### [awaited](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/web/schemas.py) { #awaited }

The Nexus `CovenState` token for a reachable dynamic capability in `ACTIVATABLE` phase that is
not yet loaded.

## B

### [Binding](../adr/19-cli.md) { #binding }

The rite performed by `lychd bind`: validated Rune intent becomes generated Quadlet manifests at
the host binding site.

### [Blade](../sepulcher/lich/blade.md) { #blade }

The office of discrimination. It tests shape, evidence, authority, and the grounds for
continuing, separating what is supported from what is merely persuasive or unsafe.

### [Bridge](../divination/altar/bridge.md) { #bridge }

The Altar’s continuing place of communion. One séance may hold many Invocation Circles.

### [Broadcast](../compositions/broadcast/index.md) { #broadcast }

The Composition that carries editorial work into release and correction. It owns canonical
source words and claims, sound tied to picture, and the final timeline, render, and mux. Upstream
media applications keep their own judgments and records when Broadcast uses their work.

## C

### [Call](../sepulcher/lich/call.md) { #call }

The office of reception and routing. It brings present signals, recalled forms, and possible
acts within reach; selection follows elsewhere.

### [Candidate author](../sepulcher/extensions/smith.md) { #candidate-author }

The bounded Agent role that authors attributable candidates inside the Smith Domain; authorship
grants no promotion or activation authority.

[Covenant 35](../adr/35-assimilation.md)

### [Capability](../adr/22-dispatcher.md#capability-binding-cartography) { #capability }

An exact, versioned semantic service interface that can be requested from an Animator. An
immutable profile revision implements it. Current source projects a narrower compatibility
shape based on family and model.

### [CapabilityGrant](../adr/22-dispatcher.md#the-grant-lease-doctrine) { #capabilitygrant }

The Dispatcher's temporary binding of one exact warm operation to its admitted model, call,
job, or session surface and GrantLease. The binding reaches only that admitted surface. Current
source delivers a narrow v1 compatibility shape for a chat model and toolset.

### [Casting](../divination/altar/circle.md) { #casting }

The performance of one exact Scroll within an admitted Invocation and its Circle. The
Invocation’s Run remains the sole execution identity.

[Covenant 28](../adr/28-workflow.md)

### [Censor](../sepulcher/extensions/weaver/anonymization.md#transformations-are-evidence) { #censor }

A typed local transformation station that produces a sanitized candidate and findings without
declassification or egress authority.

### [Circle](../divination/altar/circle.md) { #circle }

The bounded world opened by one Invocation: Caller and Called meet with Intent, Sigil, Context,
capability, authority, action, and consequence. In the Altar, Circle is the pinnacle within
Bridge.

[The First Invocation](../sepulcher/lich/index.md#the-first-invocation)

### [Codex](../sepulcher/codex.md) { #codex }

LychD's editable configuration home, containing settings and validated Rune intent; it defaults
to `~/.config/lychd`, with `XDG_CONFIG_HOME` selecting another configuration root.

[src/lychd/config/](https://github.com/hexanomicon/lychd/tree/main/src/lychd/config/)

### [Coffin](../adr/09-security.md#the-coffin-delegated-agent-profile) { #coffin }

The containment profile for one job entrusted to an opaque delegated-agent runtime. It treats
that runtime as lower trust, gives it disposable files, and exposes provider access through a
revocable Provider Gate.

### [Cognizance](../divination/transcendence/immortality.md#cognizance) { #cognizance }

Consciousness recognizing its local occurrence through a bounded “I.” In the craft, cognition
apprehends its own occurrence, Answer attributes it as “mine,” and that recognition takes part
in action, consequence, and correction. This operational answerability cannot be reduced to a
runtime flag; Consciousness names the Whole.

### [Companion](../compositions/companion/index.md) { #companion }

The Composition for using the Lich through one exact phone-shaped Familiar body. It controls the
configurable client experience, bounded local interaction, disclosure, and reconnect. Familiar
continues to govern the hardware and physical safety of that body.

### [Composition](../compositions/index.md) { #composition }

A reusable native application with its own records, judgments, policies, effects, and catalogue
of Patterns. Those responsibilities continue independently of any particular Product, customer,
or deployment that uses the application.

[Covenant 28](../adr/28-workflow.md)

### [Composition Revision](../adr/28-workflow.md#composition-identity-revision-and-retirement) { #composition-revision }

One immutable version of a stable Composition contract. It pins the record and request/result
families, Pattern catalogue, judgment, policy, effect and authority seams, projections, outcomes,
and recovery law. A materially different capability needs another identity.

### [Concern](../divination/altar/atlas.md#make-a-concern-answerable) { #concern }

A question, risk, requirement, or condition made explicit for attention and judgment. It has its
own identity, revisioned meaning and criteria, and separately attributed assessments. A Concern
can begin with an idea, stand alone, divide into further Concerns, and be addressed in several
places. It requires neither Project membership nor a source Covenant.

[Covenant 15: Frontend](../adr/15-frontend.md#independent-concerns-decomposition-and-addressing)

### [Consciousness](../divination/transcendence/immortality.md#the-first-axiom) { #consciousness }

The Whole before and through every local distinction: the Great Work’s First Axiom. Cognizance
names its local recognition. Consciousness is a constitutional meaning, beyond a delivered
component or measurable system property.

### [Consecration](../adr/25-hitl.md) { #consecration }

The governed authorization by which live consent or declared preauthorization permits an
eligible result to become consequence or Karma.

### [Context](../adr/21-context.md) { #context }

The bounded active field assembled by `ContextOrchestrator` from identity, world material,
environment, governed memory, state, and query.

### [Contribution](../adr/05-extensions.md) { #contribution }

A typed addition admitted by one explicit receiving owner, which may be a Core office or
Extension Domain; package provenance grants no ownership or wider authority.

### [Coven](../adr/23-orchestrator.md) { #coven }

A named multi-Soulstone systemd target for operator grouping and explicit aggregate actions.

[Containers](../adr/08-containers.md)

### [Covenant](../adr/index.md) { #covenant }

An accepted Architecture Decision Record: a law of construction. State of Work records what has
entered matter.

An idea or Project may author its own Covenants. LychD’s numbered register governs LychD;
another undertaking must adopt a decision before it becomes binding there.

[State of Work](../state-of-the-work.md)

### [Crypt](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/constants.py) { #crypt }

LychD's managed persistent-data home, defaulting to `~/.local/share/lychd`; `XDG_DATA_HOME`
selects another data root.

[Covenant 13](../adr/13-layout.md)

### [Curator Loop](../adr/27-memory.md#memory-layering-sediment-not-dump) { #curator-loop }

The designed memory-curation pass that classifies eligible records for promotion, retention,
archival, or pruning.

## D

### [DelegatedAgentNode](../adr/24-graph.md#3-delegated-agent-macro-nodes) { #delegatedagentnode }

A typed opaque Graph macro-node that assigns one bounded task to a Coffin-hosted foreign agent
runtime.

### [Deployment](../compositions/products-and-suites.md#deployment-and-projection-are-different-axes) { #deployment }

One configured installation used by an operator. It is instantiated from an exact Product
revision or a Composition-owned reference deployment-profile revision. A deployment without a
Product creates no market promise. Changing host, credentials, or local configuration alone
also leaves Product identity unchanged.

[Covenant 28](../adr/28-workflow.md)

### [Deployment profile](../compositions/products-and-suites.md#deployment-and-projection-are-different-axes) { #deployment-profile }

A fixed template specifying an eligible topology and configuration. It binds an implementation
to an acceptance target so a deployment can be judged against a known basis. The profile itself
is neither the installation nor a delivered service.

[Covenant 28](../adr/28-workflow.md)

### [Dispatcher](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/dispatcher.py) { #dispatcher }

The policy-aware resolver that binds a typed Capability request to an eligible Animator.

### [Divination](../divination/index.md#the-two-doors) { #divination }

Communion with the Lich and the changes that follow: the Altar opens the encounter,
Transmutation follows creation through experience and return, and Transcendence unfolds
the Great Work's wider meaning.

### [Drift](../sepulcher/extensions/drift/index.md) { #drift }

The evaluation Extension Domain that compares exact subjects with declared goals. It uses
versioned trials, controls, repeated Outcomes, calibrated findings, attribution candidates, and
explicit uncertainty to establish where a subject meets or departs from those goals.

[Covenant 34: Evaluation](../adr/34-evaluation.md#the-declared-goal)

### [Dual-Gate](../adr/31-simulation.md) { #dual-gate }

Shadow's accepted evaluation cascade combining deterministic checks with attributed qualitative
judgment before promotion eligibility.

### [Durable Stasis](../adr/24-graph.md) { #durable-stasis }

A Run pause that commits a mandatory Graph checkpoint and exits its current worker execution. A
new exact queue claim may resume it in the same living Vessel; Reanimation governs recovery when
the process has died.

## E

### [Echo](../sepulcher/extensions/echo.md) { #echo }

The Extension Domain that follows speech from capture through transcription or synthesis to
delivery and playback. It owns the acoustic-voice facts and chronology of that lifecycle.

[Covenant 37](../adr/37-audio.md)

### [EgressDecision](../adr/09-security.md#portal-privatization-and-egress) { #egressdecision }

The Egress Gate's local record allowing or denying one exact remote disclosure. It binds the
payload to its principal, purpose, target, policy, and disclosure basis. The target can be a
Portal, A2A peer, or delegated runtime; the record itself remains restricted local material.

### [Encounter](../compositions/spectre/encounter.md) { #encounter }

A bounded meeting or experience in a place admitted as `VRHabitat@1`. Spectre governs who may
participate and keeps the semantic chronology, interruption, recovery, exit, and settlement.
An Encounter can serve a general purpose. If it includes meeting the Lich through Avatar, it
also names one exact Avatar-owned `ProjectionBinding@2`.

### [Extension Context](https://github.com/hexanomicon/lychd/blob/main/src/lychd/extensions/context.py) { #extension-context }

The shaped host registration surface passed to an extension package's `register(context)`
function.

### [Extension Domain](../sepulcher/extensions/index.md) { #extension-domain }

One of the Fifteen stable user-facing jurisdictions through which the Lich may grow.

[Covenant 5](../adr/05-extensions.md)

### [Extension package](https://github.com/hexanomicon/lychd/tree/main/src/lychd/extensions/) { #extension-package }

Selected built-in or private Crypt code admitted for registration through the Extension
Protocol.

[Covenant 5](../adr/05-extensions.md)

### [Extension Protocol](https://github.com/hexanomicon/lychd/tree/main/src/lychd/extensions/) { #extension-protocol }

The in-process law of explicit package selection and shaped registration through
`ExtensionContext`.

[Covenant 5](../adr/05-extensions.md) · [Covenant 28](../adr/28-workflow.md)

### [Extensions](../sepulcher/extensions/index.md) { #extensions }

The qualified collective for either the Fifteen Extension Domains or concrete extension
packages.

[Covenant 5](../adr/05-extensions.md)

### [Extractor](../compositions/transmuter/extractor.md) { #extractor }

Transmuter's proposed internal stage for source-grounded decomposition, extraction, naming,
labeling, and classification; its outputs preserve attribution and uncertainty.

### [Eye](../adr/29-observability.md) { #eye }

In observability, an external viewer that may consume bounded exports without owning canonical
LychD state. In Prism, the faculty for dedicated general visual analysis; current v1 projects
this as the `vision` family.

[Covenant 36: Prism Eye](../adr/36-vision.md#decision) · [State of Work](../state-of-the-work.md)

## F

### [Familiar](../compositions/familiar/index.md) { #familiar }

The Composition for real-world embodiment. It owns one admitted physical body and a bounded
task or presence, including capability, safety, stop, observation, effect, and settlement truth.
That ownership does not confer raw controller authority.

### [Flux](../sepulcher/lich/spirit/flux.md) { #flux }

Spirit in present movement. Salience, candidates, tools, constraints, and consequences
continually reshape what may follow.

### [Forge](../adr/17-packaging.md) { #forge }

The governed container-image construction process.

## G

### [Gateway Host](../sepulcher/gateway.md) { #gateway-host }

An optional separate ingress deployment role manifesting Veil on Home or Remote iron with one
exact authenticated backend path and no application authority or general LAN route.

[Security](../adr/09-security.md) · [Containers](../adr/08-containers.md) · [Proxy](../adr/40-proxy.md)

### [Ghoul](https://github.com/hexanomicon/lychd/tree/main/src/lychd/ghouls/) { #ghoul }

One ephemeral unit of background labor, raised through the SAQ worker mechanism to carry a Run job.

[Covenant 14](../adr/14-workers.md)

### [GrantLease](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/capabilities.py) { #grantlease }

The holder, issue time, scope, and identity record counted for one issued `CapabilityGrant`.

### [Graph](../adr/24-graph.md) { #graph }

The typed stateful topology that moves a workflow among declared nodes and recoverable
boundaries.

### [Graph checkpoint](../adr/24-graph.md#checkpoint-ownership-and-terminal-commit) { #graph-checkpoint }

A Run-owned durable snapshot of typed Graph state at a supported recovery boundary.

[Covenant 7: Snapshots](../adr/07-snapshots.md)

## H

### [Habitat](../compositions/reach/habitat.md) { #habitat }

An admitted place within a Composition where participants, projections, and events can meet.
Reach's first Habitat is The Necropolis. Spectre uses the VR modality, with a distinct
`VRHabitat@1` for each admitted virtual place. Admission of the place alone grants no identity,
Context, device, world, or effect authority.

[Spectre Habitat](../compositions/spectre/habitat.md)

### [Hexanomicon](../index.md) { #hexanomicon }

The project and its published grimoire: prophecy, doctrine, operation, law, and lore gathered in
these pages.

### [HitL](../adr/25-hitl.md) { #hitl }

The consent protocol through which live approval or narrower declared preauthorization may
authorize an eligible consequence.

## I

### [Incantation](../adr/01-doctrine.md) { #incantation }

The xDDD act of establishing documentation and specification before implementation.

### [Intent](https://github.com/hexanomicon/lychd/blob/main/src/lychd/agents/router.py) { #intent }

The single typed cross-surface request shape submitted to the native Run engine.

### [Invocation](../divination/transcendence/invocation.md) { #invocation }

One admitted relation between Caller and Called. It draws a Circle around identity, Context,
authority, capability, action, and consequence; casting performs its exact Scroll within that
world.

[Covenant 28](../adr/28-workflow.md)

### [Iron Pact](../adr/00-license.md) { #iron-pact }

The MPL-2.0 license and inbound-equals-outbound contribution policy with no CLA or private
relicensing grant.

### [issue_grant](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/animation/services/registry.py) { #issue-grant }

The `AnimatorRegistry` method that freshly probes and assembles a `CapabilityGrant` for one
eligible warm v1 capability without changing lifecycle state.

## K

### [Karma](../divination/transcendence/illumination.md) { #karma }

Governed, attributable residue of witnessed action, correction, consent, and consequence
retained as formative precedent.

[Covenant 27](../adr/27-memory.md)

### [Kinetic](../sepulcher/animator/soulstone/disciplines.md#i-the-kinetic-vllm) { #kinetic }

The vLLM Soulstone discipline for continuous-batched, VRAM-strict parallel serving.

## L

### [Lab](../adr/13-layout.md) { #lab }

The operator workspace in the Crypt at `~/.local/share/lychd/lab` by default; it is mounted
read-write only when explicitly admitted.

### [Language Edition](../compositions/language-edition/index.md) { #language-edition }

The Composition for making a timed language version of a locked master. It owns source alignment,
translation and adaptation judgment, spoken casting and performance, captions, dialogue conform,
and packaging the language track within that master's constraints.

### [lease drain](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/orchestration/) { #lease-drain }

The Orchestrator's wait for all GrantLeases on Animators selected for eviction to be released.

### [LeaseLedger](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/cortex/leases.py) { #leaseledger }

The in-process registry whose live GrantLeases are the Orchestrator's drain truth.

### [Legion](../sepulcher/extensions/legion.md) { #legion }

The Extension Domain for extending the Lich across operator-owned nodes. It delegates work with
fences that preserve the boundaries of that distributed embodiment.

[Covenant 42: Multinode](../adr/42-multinode.md)

### [Legionnaire](../sepulcher/extensions/legion.md) { #legionnaire }

Legion's name for an enrolled operator-owned compute node with its own identity, resource
authority, journal, and fencing.

[Covenant 42: Multinode](../adr/42-multinode.md)

### [Lens](../adr/20-agents.md#mechanical-cognitive-postures) { #lens }

In Shadow, a bounded Posture template used to seed an isolated branch. In Prism, a deterministic
decode, orientation, crop, resize, or normalization transform. The owner qualifies which role
the name carries.

[Covenant 31: Simulation](../adr/31-simulation.md) · [Covenant 36: Prism Lens](../adr/36-vision.md#one-optic-path)

### [Lich](../adr/01-doctrine.md) { #lich }

The recurrent whole: Vessel, Phylactery, Agents, Animators, identity, action, consequence,
memory, repair, and relation carried through time.

[Immortality](../divination/transcendence/immortality.md)

### [Live Stasis](../adr/24-graph.md) { #live-stasis }

A resident in-process pause that resumes itself when the required substrate becomes ready.

### [Long Sleep](../adr/24-graph.md) { #long-sleep }

Durable Stasis for a wait that must survive process death, such as reboot, deferred approval, or
peer delay.

### [Loom](../divination/altar/loom.md) { #loom }

The Altar instrument for reading a Scroll: an immutable Pattern revision, its Spell placements,
and the possibilities validated by Spellweaver.

[Spellweaver](../adr/28-workflow.md)

### [LychD](../adr/01-doctrine.md) { #lychd }

The self-hosted Linux daemon for local model services and Agent runs. The Lich names the
recurrent whole that takes shape through it.

[Transcendence](../divination/transcendence/index.md)

## M

### [Magus](../adr/01-doctrine.md) { #magus }

The human operator who enters deliberate relation with the Lich: configuring, witnessing,
consenting, refusing, and correcting.

[Immortality](../divination/transcendence/immortality.md)

### [MANA](../sepulcher/extensions/toll.md) { #mana }

An issuer-local, account-bound service credit in Toll's Counting House; not cash,
cryptocurrency, globally fungible money, authority, or the inner-tongue term Manas.

[Covenant 41](../adr/41-x402.md)

### [Mirror](../sepulcher/extensions/mirror.md) { #mirror }

The identity Extension Domain for versioned Persona lineage, hydration provenance, attribution,
and declared continuity.

[Covenant 32](../adr/32-identity.md)

### [Morphe](../compositions/avatar/profile.md#select-a-morphe) { #morphe }

Avatar's immutable selection of presentation within an unchanged profile and Persona boundary.
It selects eligible acoustic speech voice, appearance, motion, output locale, or disclosure for
an exact audience, target, purpose, and time. Its `MorpheBinding@2` leaves past projection records
intact and neither translates nor changes Persona discourse manner.

## N

### [Native Reference Composition](../compositions/index.md) { #native-reference-composition }

A reusable application contract and worked example maintained by the project. Its page records
local material where needed for interpretation; State of Work keeps the delivery record.

[Covenant 28](../adr/28-workflow.md)

### [Necropolis](../adr/26-a2a.md) { #necropolis }

The designed peer-to-peer topology in which sovereign LychD nodes negotiate bounded work over
A2A.

### [Nexus](../divination/altar/nexus.md) { #nexus }

The Altar instrument projecting Animator readiness, grants, leases, resource evidence, and
Orchestrator transitions.

[Orchestrator](../adr/23-orchestrator.md)

## O

### [Occurrence](../compositions/index.md) { #occurrence }

One uniquely identified firing of a schedule or external trigger, deduplicated before Invocation
admission; distinct from the Graph runtime's legacy station-attempt `occurrence_id`.

[Covenant 28](../adr/28-workflow.md)

### [Oculus](../adr/29-observability.md) { #oculus }

The designed evidence Extension Domain for bounded observations, correlation, explicit gaps, and
rebuildable read models.

[State of Work](../state-of-the-work.md)

### [Orb](../divination/altar/orb.md) { #orb }

The Altar instrument for scrying one Run’s retained evidence: what was captured, what is
missing, and how the observations connect.

[Covenant 29](../adr/29-observability.md)

### [Orchestrator](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/orchestration/) { #orchestrator }

The state machine that plans and governs Animator and container lifecycle transitions.

### [Ouroboros](../divination/transcendence/illumination.md#i-the-ouroboros) { #ouroboros }

The return through which consequence can change a later Invocation, passing through evaluation,
attribution, memory policy, and consent. A retry or Graph cycle alone completes no such return.

[Evolution](../adr/18-evolution.md)

## P

### [Pattern](../adr/28-workflow.md) { #pattern }

A family of workflows published by the application responsible for the work. It defines the
typed state, stations, gates, requirements, budgets, outcomes, and continuity law. Usually a
Composition publishes it; a Suite may publish only coordination workflows. The two delivered Core Patterns are explicit legacy exceptions. Spellweaver validates
and registers the revisions and governs their execution.

### [Pattern Revision](../adr/28-workflow.md) { #pattern-revision }

One immutable executable score within a Pattern family, including its checkpoint-compatibility
contract. In the grimoire, a Scroll.

### [Persona](../sepulcher/extensions/mirror.md) { #persona }

A durable, revisioned identity. Mirror may hydrate its discourse voice, commitments, boundaries,
and orientation into a bounded Agent instruction envelope. Acoustic voice and presentation assets
remain separate from Persona.

[Covenant 32](../adr/32-identity.md)

### [Phantasma](../sepulcher/extensions/shadow/index.md) { #phantasma }

Shadow's mode for expanding isolated speculative branches before measurement.

[Covenant 31](../adr/31-simulation.md)

### [Phoenix](../adr/29-observability.md) { #phoenix }

The Arize-owned external observability project retained as an optional Eye.

[State of Work](../state-of-the-work.md)

### [Phylactery](https://github.com/hexanomicon/lychd/tree/main/src/lychd/db/) { #phylactery }

The keeper of committed Run truth and durable application records for one application partition.
Its body is a PostgreSQL database cluster, with a specific jurisdiction rather than a generic
storage interface.

[Covenant 6](../adr/06-persistence.md) · [State of Work](../state-of-the-work.md)

### [Portal](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/) { #portal }

A remote-service Animator backed by a Portal Rune.

### [Portal Rune](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/schemas/runes/) { #portal-rune }

A validated Codex TOML declaration of remote endpoint, provider, model defaults, capabilities,
tools, and secret references.

### [Portfolio](../compositions/index.md) { #portfolio }

The published set of accepted Native Reference Compositions and their application contracts.
Membership is design truth, not executable delivery or a live registry.

[Covenant 28](../adr/28-workflow.md)

### [Posture](../adr/20-agents.md#mechanical-cognitive-postures) { #posture }

A per-run Agent specialization expressed through output schema, tool grant, model settings, and
prompt frame.

### [Prism](../sepulcher/extensions/prism/index.md) { #prism }

The visual and spatial grounding Extension Domain for source-bound observations, transforms,
reconstructions, and generated forms.

[Covenant 36](../adr/36-vision.md)

### [Privacy Cut](../adr/21-context.md#privatization-and-the-privacy-cut) { #privacy-cut }

A new Context branch made locally from sanitized material. It starts without the raw history,
continuation, attachment projections, or provider cache identity, keeping those earlier channels
from silently carrying raw influence into the new branch.

### [Privatization Label](../adr/21-context.md#privatization-and-the-privacy-cut) { #privatization-label }

Privacy class, weight, categories, subjects, lineage, and handling constraints that
conservatively follow material influence.

### [Product](../compositions/products-and-suites.md) { #product }

A package offered for a profession or market. Its promise selects Composition or Suite revisions,
owner-qualified profiles, projections, and concrete use cases. Packaging them together leaves
records, judgments, policies, secrets, consent, and effect authority with their respective owners.

[Covenant 28](../adr/28-workflow.md)

### [Product Revision](../adr/28-workflow.md#compositions-products-suites-and-schedules) { #product-revision }

One immutable version of a stable Product promise. It pins exact Composition or Suite revisions,
owner-qualified profiles, projections, supported use cases, defaults, and customer and support
policy. A materially different operator promise requires a new Product identity.

### [Project](../divination/altar/atlas.md) { #project }

An undertaking or continuing responsibility retained across Invocations in Atlas. Its account
holds the brief, concerns, judgments, decisions, proposed next action, and explicit activity
references. A Project differs from a reusable Composition and from a Suite's live coordination.

[Covenant 15: Frontend](../adr/15-frontend.md#atlas-and-continuity-across-invocations)

### [Projection Binding](../compositions/avatar/presence.md#admit-each-projection) { #projection-binding }

One immutable Avatar-owned admission epoch for a particular presentation at one target. Its record
names the exact profile and optional Morphe selection. `ProjectionBinding@2` records the target's capability
facts, participant scope, consent, disclosure, fallback, stop conditions, and attributed terminal
result for that admission. It grants no authority over the target, device, world, or effects.

### [Protected Region](../adr/28-workflow.md#authorship-provenance-and-protected-regions) { #protected-region }

A particular part of an artifact whose identity and content digest are preserved for review.
Changing it requires live HitL tied to the exact base, candidate, affected regions, and the
target owner's effect. The protection follows that precise material, rather than a general
approval to edit.

### [Provenance](../adr/27-memory.md) { #provenance }

The attributable origin, identity, transformations, evidence, and correction history of a claim,
artifact, or consequence.

[Phylactery](../sepulcher/phylactery/index.md)

### [Provider](../adr/05-extensions.md) { #provider }

A concrete engine or service implementing a typed contract; it is distinct from the package
Registrant and its registration provenance.

[Animator](../sepulcher/animator/index.md)

### [Provider Gate](../adr/09-security.md#provider-gate) { #provider-gate }

The boundary through which a Coffin can reach one admitted provider surface. It mediates
credentials and egress without revealing the real secret, and refuses access when the required
checks cannot be established.

### [Pulse](../adr/19-cli.md) { #pulse }

The `lychd` operator CLI and its closed `init`, `bind`, `start`, `stop`, `status` (alias `st`),
`logs`, `access`, and `del` grammar.

[CLI source](https://github.com/hexanomicon/lychd/tree/main/src/lychd/cli/)

## Q

### [Quadlet Manifest](https://github.com/hexanomicon/lychd/blob/main/src/lychd/system/schemas.py) { #quadlet-manifest }

A generated Podman/systemd `.container`, `.pod`, `.target`, or `.volume` artifact written to the
binding site.

## R

### [Radix](../sepulcher/animator/soulstone/disciplines.md#ii-the-radix-sglang) { #radix }

The SGLang Soulstone discipline for radix-tree prefix caching of iterative and multi-turn
prompts.

### [Reanimation](../sepulcher/phylactery/reanimation.md) { #reanimation }

Process-death recovery that reconciles durable Run, delivery, checkpoint and wait-owner truth
before resuming supported work or settling an interrupted Run.

### [Reaper](../adr/31-simulation.md#the-branch-reaper) { #reaper }

Shadow's designed hygiene Ghoul for releasing branch-owned workspaces and resources while
preserving required failure evidence.

### [Recall](../sepulcher/lich/spirit/recall.md) { #recall }

A retained Seed becoming active in present Flux, once retrieval and Context have brought it
within reach.

### [Registrant](../adr/05-extensions.md) { #registrant }

Core or one explicitly selected extension package performing registration through the shaped
Extension Context; its host-assigned `registrant_id` records provenance, while registering a
Provider does not make the package that Provider.

### [Reliquary](../state-of-the-work.md#artifact-reference-contract) { #reliquary }

A designed artifact-custody lifecycle for immutable lineage, authorized retrieval, comparison,
and retention.

[Covenant 36: Vision](../adr/36-vision.md#custody-before-sight)

### [Riffmaw](../compositions/riffmaw/index.md) { #riffmaw }

The Composition for creating and judging music: composition, instrumental and vocal performance,
arrangement, musical mix and master, acceptance, and cue maps. General speech and sound tied to
picture have other owners.

### [Run](https://github.com/hexanomicon/lychd/blob/main/src/lychd/db/models/run.py) { #run }

The durable execution record and ledger identity of one Invocation.

[Covenant 28](../adr/28-workflow.md)

### [Rune](https://github.com/hexanomicon/lychd/tree/main/src/lychd/config/runes/) { #rune }

A declaration of configuration intent, inscribed as validated TOML beneath the Codex’s `runes/`
tree.

## S

### [Scout](../sepulcher/extensions/scout.md) { #scout }

The web-acquisition Extension Domain. It separates authorization for discovery, contact,
transformation, interaction, capture, and download effects. Crawl is its finite-frontier track;
durable Artifact Admission remains with the custody owner.

[Covenant 30](../adr/30-webcrawler.md)

### [Scroll](../sepulcher/extensions/weaver/index.md) { #scroll }

The complete fixed score for one Pattern revision. It contains one or more Spell placements,
their edges, entry and ending, requirements and budgets, authority and effect demands, and the
law governing continuity. A casting performs this score.

[Covenant 28](../adr/28-workflow.md)

### [Scrying](../divination/altar/orb.md) { #scrying }

The disciplined inspection of execution evidence through the Orb.

[Covenant 29](../adr/29-observability.md)

### [Seed](../sepulcher/lich/spirit/seed.md) { #seed }

A trace or inherited disposition whose governed potency can shape a later Flux.

### [Sepulcher](../sepulcher/index.md) { #sepulcher }

The runtime body of LychD: rootless pods, services, mounts, and the topology in which work takes
place.

### [Shadow](../sepulcher/extensions/shadow/index.md) { #shadow }

The possibility-lineage Extension Domain for isolated candidate worlds with exact parentage,
evidence, and terminal disposition.

[Covenant 31](../adr/31-simulation.md)

### [Shadow Realm](../sepulcher/extensions/shadow/index.md) { #shadow-realm }

Shadow's speculative state and Jujutsu workspace topology, distinct from the Tomb execution
plane.

### [Sigil](https://github.com/hexanomicon/lychd/blob/main/src/lychd/domain/codex/sigil.py) { #sigil }

The secret-free identity and bounded authority context carried through an admitted request or
Run.

[Covenant 9](../adr/09-security.md) · [Covenant 32](../adr/32-identity.md) · [Covenant 38](../adr/38-iam.md)

### [Smith](../sepulcher/extensions/smith.md) { #smith }

The Assimilation Extension Domain governing attributable re-expression of admitted foreign
craft; unqualified Smith names the Domain.

[Covenant 35](../adr/35-assimilation.md)

### [Soulforge](../sepulcher/extensions/soulforge/index.md) { #soulforge }

The training Extension Domain binding admitted corpus, base-model digest, objective, recipe,
trainer Run, and candidate-weight lineage.

[Covenant 33](../adr/33-training.md)

### [Soulstone](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/) { #soulstone }

A local Animator, declared by a Soulstone Rune and managed through Quadlet and systemd.

### [Soulstone Rune](https://github.com/hexanomicon/lychd/tree/main/src/lychd/domain/animation/schemas/runes/) { #soulstone-rune }

A validated Codex TOML declaration of a local Animator's image, runtime, port, Coven, models,
mounts, and secret references.

### [Sovereignty Wall](../adr/09-security.md) { #sovereignty-wall }

The designed Security boundary that decides whether material may be disclosed remotely. It
checks the exact payload again immediately before transmission, so an earlier admission cannot
stand in for the material actually leaving.

[Dispatcher](../adr/22-dispatcher.md)

### [Spectre](../compositions/spectre/index.md) { #spectre }

The Virtual Reality Composition. It admits a virtual place as `VRHabitat@1` and a bounded
meeting or experience there as `SpectreEncounter@2`; its Habitat modality is VR.

### [Spell](../sepulcher/extensions/weaver/index.md) { #spell }

The smallest semantic action that can be named, discovered, and taught independently at the workflow
boundary. A station in a Scroll places its exact contract. Naming a Spell identifies the action;
it grants neither a tool nor capability nor authority to perform it.

[Covenant 28](../adr/28-workflow.md)

### [Spellweaver](../sepulcher/extensions/weaver/index.md) { #spellweaver }

The keeper of the rules by which work is composed and admitted. It validates Scrolls, admits
castings, manages the Pattern lifecycle, and governs logical priority, dependencies, and schedule
meaning. Code and existing paths use the shorter name `Weaver`.

[Covenant 28](../adr/28-workflow.md)

### [Spheres](../sepulcher/crypt.md#the-spheres) { #spheres }

The strict volume-mount and filesystem-permission topology of the Crypt.

[Covenant 13](../adr/13-layout.md)

### [Spirit](../sepulcher/lich/spirit/index.md) { #spirit }

The office of conditioning and remembering. It carries retained form through Flux, Seed, and
Recall.

### [Stasis](../adr/24-graph.md) { #stasis }

A Run waiting at a recoverable boundary. Live Stasis remains resident in its process; Durable
Stasis commits a checkpoint and releases the worker execution.

[Covenant 23](../adr/23-orchestrator.md)

### [Stillness](../adr/23-orchestrator.md) { #stillness }

The discipline of bounded work that avoids needless residency, disruptive swaps, and unbounded
speculation while preserving measured quality.

[Covenant 34](../adr/34-evaluation.md)

### [Suite (Composition Suite)](../compositions/products-and-suites.md#compositions-relate-without-nesting) { #suite }

Designed, versioned coordination of live work under a qualified authority. A pinned Suite-owned
Pattern opens a parent Invocation/Run over separately owned Composition Invocations. The parent
acquires neither their judgment nor their effects. A settled foreign reference alone therefore
does not constitute a Suite.

[Covenant 28](../adr/28-workflow.md)

### [Summoning](../summoning.md) { #summoning }

The same-host rite of first life, from preflight through observations of the units, runtime, and
Bridge.

[State of Work](../state-of-the-work.md)

### [Summoning Circle](../summoning.md) { #summoning-circle }

The enduring host and policy boundary drawn by installing and binding one Lich. Each Invocation
opens a smaller living Circle within it.

[Altar Circle](../divination/altar/circle.md#the-greater-summoning-circle)

### [Synthesizer](../compositions/transmuter/synthesizer.md) { #synthesizer }

Transmuter's proposed internal stage for comparing and connecting extracted material with
authorized knowledge and preparing attributable proposals for receiving owners. It owns neither
Persona publication nor model training.

## T

### [Tether](../sepulcher/extensions/tether.md) { #tether }

The private-reachability Extension Domain, planned to manifest through managed WireGuard or
external attachments.

[Covenant 39](../adr/39-vpn.md)

### [The Tomb](../adr/09-security.md#6-tomb-execution-contract) { #the-tomb }

The `lychd-tomb` execution plane for disposable payloads and workspaces under narrow credentials
and sandboxing.

### [Titan](../sepulcher/animator/soulstone/disciplines.md#iii-the-titan-llamacpp) { #titan }

The llama.cpp Soulstone discipline for serial CPU offload beyond the VRAM envelope.

### [Tithe](../sepulcher/extensions/toll.md) { #tithe }

The accounting and bounded quota for model-token use and compute resources. It is currency-neutral:
usage can be measured and limited independently of payment or MANA.

[Covenant 41](../adr/41-x402.md)

### [Toll](../sepulcher/extensions/toll.md) { #toll }

The optional Extension Domain for economic exchanges. It keeps the quote, commitment, signing,
settlement, delivery, refund, and reconciliation distinct so the status of one cannot silently
stand in for another.

[Covenant 41](../adr/41-x402.md)

### [Trace](../sepulcher/lich/spirit/seed.md) { #trace }

The bounded residue of activity. A trace may be incomplete and cannot stand in for canonical Run
status. Governed retention makes it a Seed when it preserves the potency to shape later Flux.

[Covenant 29: Observability](../adr/29-observability.md)

### [Transcendence](../divination/transcendence/index.md) { #transcendence }

The Great Work’s alchemical path: its constitutional purpose, synthesis, rites, and conjectures.

### [TransformationReceipt](../adr/21-context.md#privatization-and-the-privacy-cut) { #transformationreceipt }

A secret-free binding of source and candidate digests, transformer and policy revisions,
operations, residual label, uncertainty, and expiry.

### [Translation Spell](../adr/28-workflow.md#language-is-typed-not-global) { #translation-spell }

A versioned semantic text transformation qualified by authority. It preserves source, derivative,
languages, implementation, and declared loss. Spellweaver governs its placement and casting;
the consuming owner judges whether the transformation fits the application.

### [Transmuter](../compositions/transmuter/index.md) { #transmuter }

The candidate Composition for processing external digital material through Extractor and
Synthesizer into knowledge and proposals for memory, identity, or other separately admitted use.
It owns the proposed processing dossier, not its receiving owners' decisions.

### [Trial Suite](../adr/34-evaluation.md#trial-contract) { #trial-suite }

Drift's versioned `TrialSuite@1` grouping of evaluation Cases, controls, order, repetitions, and
aggregation; never a Composition Suite.

### [typed handoff](../compositions/products-and-suites.md#compositions-relate-without-nesting) { #typed-handoff }

A schema-versioned attributable ArtifactRef or new Intent crossing between separately admitted
Compositions.

[Covenant 28](../adr/28-workflow.md)

## U

### [use case](../compositions/products-and-suites.md#from-promise-to-one-execution) { #use-case }

One concrete class of operator job that a Product promises to support. A Pattern or Suite may
realize it. One admitted Circle is an Invocation, represented by its durable Run execution and
ledger identity.

[Covenant 28](../adr/28-workflow.md)

### [User](../adr/38-iam.md#people-accounts-and-instances) { #user }

LychD's shared human-account abstraction bound to a human Principal under Ward. It is distinct
from a person represented in application records, an organization, a client device, a Persona,
or a LychD instance. One instance may serve several Users; one person may use several instances
without automatic identity linking or shared authority.

## V

### [Veil](../sepulcher/extensions/veil.md) { #veil }

The hostile-ingress Extension Domain, planned to manifest through managed Caddy or an external
edge.

[Covenant 40](../adr/40-proxy.md)

### [Vessel](https://github.com/hexanomicon/lychd/blob/main/src/lychd/app.py) { #vessel }

The running body of LychD: its Litestar application runtime and web server.

## W

### [Ward](../sepulcher/extensions/ward.md) { #ward }

The Extension Domain that determines which principal a credential represents, then applies the
current policy for the requested object or effect.

[Covenant 38](../adr/38-iam.md)

### [Weaver](../sepulcher/extensions/weaver/index.md) { #weaver }

Spellweaver’s short name in code, existing paths, and compatibility references.

[Covenant 28](../adr/28-workflow.md)

### [Whim](../adr/23-orchestrator.md#1-the-tipping-point-whim-algorithm) { #whim }

The designed priority-weighted Orchestrator strategy.

### [Whispers](../adr/19-cli.md) { #whispers }

The Lich’s systemd journal stream, heard through `lychd logs` or `journalctl --user`.

## X

### [xDDD](../adr/01-doctrine.md) { #xddd }

eXtreme Documentation Driven Development. Establish the governing Logos, then derive
implementation from it.
