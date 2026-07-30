---
title: Iron Tongue
icon: material/anvil
---

# :material-anvil: Iron Tongue — Canonical Project Terms

_The canonical project vocabulary: one alphabet, one compact meaning per term._

Iron Tongue fixes names used by code, accepted architecture, operations, and authored project
doctrine. [Inner Tongue](./inner-tongue.md) separately owns etymology, philosophical
correspondence, and native cosmology; a word appears in both only to map the two registers.

## Terms

Flavor names such as Vessel, Phylactery, Soulstone, Portal, Coven, and Ghoul are canonical only
where the project assigns them a stable part, contract, or operated concept.

| Term | Technical Definition | Source |
| :--- | :--- | :--- |
| **Agent** | A Pydantic AI execution specification hydrated with a model or provider, tools, dependencies, limits, and an output contract. | [Agents (ADR 20)](../adr/20-agents.md) |
| **AgentJob** | The durable, idempotent occurrence record for one bounded attempt by a delegated-agent Graph node. | [Graph (ADR 24)](../adr/24-graph.md#3-delegated-agent-macro-nodes) |
| **Altar** | The Litestar-served Svelte web surface whose Bridge, Loom, Nexus, and Orb instruments project server-owned truth. | [ADR 15](../adr/15-frontend.md) + [State](../state-of-the-work.md#altar-and-observability) |
| **Animator** | A typed, lifecycle-managed capability endpoint manifested as a local Soulstone or remote Portal. | `src/lychd/domain/animation/` |
| **Answer** | The attribution office of the inner instrument: it binds an active Sigil, identity, Context, capability, memory, selected act, and consequence to one bounded local “I.” | [Answer](../sepulcher/lich/answer.md) |
| **Archive** | The governed memory substrate in the Phylactery for eligible traces, Karma, anchored records, provenance, and decay state. | [Memory (ADR 27)](../adr/27-memory.md#memory-layering-sediment-not-dump) + [State](../state-of-the-work.md#karma-semantic-memory) |
| **ArtifactRef** | Immutable metadata naming external durable content by identity, SHA-256 digest, media type, byte size, and classification. | [Dispatcher (ADR 22)](../adr/22-dispatcher.md#durable-content-and-artifactref) |
| **Autopoiesis** | The Work's intended capacity for verified self-repair and extension under the operator's authority. | [Immortality](../divination/transcendence/immortality.md) + ADR 16/18/35 |
| **awaited** | The Nexus `CovenState` token for a reachable dynamic capability in `ACTIVATABLE` phase that is not yet loaded. | `src/lychd/domain/web/schemas.py` |
| **Binding** | The `lychd bind` operation that compiles validated Rune intent into generated Quadlet manifests at the host binding site. | CLI |
| **Blade** | The discrimination office that separates supported shape, evidence, authority, and continuation from persuasive or unsafe alternatives. | [Blade](../sepulcher/lich/blade.md) |
| **Bridge** | The Altar instrument that accepts and routes natural-language Intent. | [Altar Bridge](../divination/altar/bridge.md) |
| **Call** | The reception and routing office that makes present signals, recalled forms, and possible acts addressable without selecting one. | [Call](../sepulcher/lich/call.md) |
| **Candidate study** | An explicitly unaccepted Portfolio proposal retained for examination without architectural promotion. | [Composition Portfolio](../compositions/index.md) |
| **Capability** | A typed service requestable from an Animator, defined by family, implementation identity, modalities, tools, and live phase. | [Dispatcher (ADR 22)](../adr/22-dispatcher.md#capability-binding-cartography) |
| **CapabilityGrant** | The Dispatcher's temporary binding of one warm capability to its state, runtime handles, resolved generation profile, toolsets, and GrantLease. | [Dispatcher (ADR 22)](../adr/22-dispatcher.md#the-grant-lease-doctrine) |
| **Censor** | A typed local transformation station that produces a sanitized candidate and findings without declassification or egress authority. | [Weaver anonymization](../sepulcher/extensions/weaver/anonymization.md#transformations-are-evidence) |
| **Circle** | The bounded world in which one Invocation joins identity, Context, capability, authority, and consequence. | [The First Invocation](../sepulcher/lich/index.md#the-first-invocation) |
| **Codex** | LychD's editable configuration home at `~/.config/lychd`, containing settings and validated Rune intent. | `src/lychd/config/` |
| **Coffin** | The lower-trust, per-job containment profile for an opaque delegated-agent runtime with disposable files and a revocable Provider Gate. | [Security (ADR 09)](../adr/09-security.md#the-coffin-delegated-agent-profile) |
| **Composition** | An operator-visible workflow application that owns one purpose, Pattern catalogue, domain state, policy, and effects. | [Composition Portfolio](../compositions/index.md) + Weaver (ADR 28) |
| **Composition Revision** | One immutable version of a Composition contract, pinning application identity, Pattern catalogue, requirements, policy, and projection metadata. | [Composition Portfolio](../compositions/index.md) + Weaver (ADR 28) |
| **Consecration** | The governed authorization by which live consent or declared preauthorization permits an eligible result to become consequence or Karma. | [HitL (ADR 25)](../adr/25-hitl.md) |
| **Context** | The bounded active field assembled by `ContextOrchestrator` from identity, world material, environment, governed memory, state, and query. | [Context (ADR 21)](../adr/21-context.md) |
| **Contribution** | A typed addition admitted through an existing Domain boundary while that Domain retains ownership. | [Extensions](../sepulcher/extensions/index.md) + ADR 05 |
| **Coven** | A named multi-Soulstone systemd target for operator grouping and explicit aggregate actions. | Orchestrator / Quadlets |
| **Covenant** | An accepted Architecture Decision Record that governs construction without proving delivery. | [The Covenants](../adr/index.md) + [State](../state-of-the-work.md) |
| **Crypt** | LychD's managed persistent-data home at `~/.local/share/lychd`. | `src/lychd/system/constants.py`; ADR 13 |
| **Curator Loop** | The designed memory-curation pass that classifies eligible records for promotion, retention, archival, or pruning. | [Memory (ADR 27)](../adr/27-memory.md#memory-layering-sediment-not-dump) |
| **DelegatedAgentNode** | A typed opaque Graph macro-node that assigns one bounded task to a Coffin-hosted foreign agent runtime. | [Graph (ADR 24)](../adr/24-graph.md#3-delegated-agent-macro-nodes) |
| **Demilich** | The Transcendence horizon of reconstitutable machine execution extending human Will without upload, erasure, or loss of refusal. | [Prophecy](../index.md) + [Transcendence](../divination/transcendence/index.md) |
| **Dispatcher** | The policy-aware resolver that binds a typed Capability request to an eligible Animator. | `src/lychd/domain/cortex/dispatcher.py` |
| **Divination** | Relation with the Lich through operating its Altar and interpreting its Transcendence. | [Divination](../divination/index.md#the-two-doors) |
| **Dual-Gate** | Shadow's accepted evaluation cascade combining deterministic checks with attributed qualitative judgment before promotion eligibility. | [Simulation (ADR 31)](../adr/31-simulation.md) |
| **Durable Stasis** | A pause that exits the process after a mandatory Graph checkpoint and resumes only through Reanimation. | [Graph (ADR 24)](../adr/24-graph.md) |
| **EgressDecision** | The Portal Egress Gate's allow-or-deny record for one exact payload, principal, purpose, destination, provider, model, policy revision, and receipt. | [Security (ADR 09)](../adr/09-security.md#portal-privatization-and-egress) |
| **Echo** | The speech-lifecycle Extension Domain for temporal capture, transcription, synthesis, codecs, and voice activity. | [Echo](../sepulcher/extensions/echo.md) + ADR 37 |
| **Extension Context** | The shaped host registration surface passed to an extension package's `register(context)` function. | `src/lychd/extensions/context.py` |
| **Extension Domain** | One of the Fifteen stable user-facing jurisdictions through which the Lich may grow. | [Fifteen Extensions](../sepulcher/extensions/index.md) + ADR 05 |
| **Extension package** | Selected built-in or private Crypt code admitted for registration through the Extension Protocol. | `src/lychd/extensions/`; ADR 05 |
| **Extension Protocol** | The in-process law of explicit package selection and shaped registration through `ExtensionContext`. | `src/lychd/extensions/`; ADR 05/28 |
| **Extensions** | The qualified collective for either the Fifteen Extension Domains or concrete extension packages. | [Fifteen Extensions](../sepulcher/extensions/index.md) + ADR 05 |
| **Eye** | An external observability viewer that may consume bounded exports without owning canonical LychD state. | [ADR 29](../adr/29-observability.md) + [State](../state-of-the-work.md) |
| **Flux** | Spirit in present movement as salience, candidates, tools, constraints, and consequences reshape what may follow. | [Flux](../sepulcher/lich/spirit/flux.md) |
| **Forge** | The governed container-image construction process. | Build Pipeline |
| **Ghoul** | One ephemeral unit of background labor raised by the SAQ worker mechanism to carry a Run job. | `src/lychd/ghouls/`; ADR 14 |
| **GrantLease** | The holder, issue time, scope, and identity record counted for one issued `CapabilityGrant`. | `src/lychd/domain/animation/capabilities.py` |
| **Graph** | The typed stateful topology that moves a workflow among declared nodes and recoverable boundaries. | [Graph (ADR 24)](../adr/24-graph.md) |
| **Graph checkpoint** | A Run-owned durable snapshot of typed Graph state at a supported recovery boundary. | [Graph (ADR 24)](../adr/24-graph.md#checkpoint-ownership-and-terminal-commit) + [Snapshots (ADR 07)](../adr/07-snapshots.md) |
| **Hard Refusal** | The retrieval policy that forbids an Agent from guessing when no Archive result clears the declared similarity threshold. | [Memory (ADR 27)](../adr/27-memory.md) |
| **Hexanomicon** | The project and its published grimoire: prophecy, doctrine, operation, law, and lore rendered from `docs/`. | `docs/` |
| **HitL** | The consent protocol through which live approval or narrower declared preauthorization may authorize an eligible consequence. | [Human-in-the-Loop (ADR 25)](../adr/25-hitl.md) |
| **Imprint** | The durable residue of the Magus's witnessed Will that may enter Karma and later Persona hydration under explicit policy. | Phylactery Archive + Mirror |
| **Incantation** | The xDDD act of establishing documentation and specification before implementation. | Doctrine |
| **Intent** | The single typed cross-surface request shape submitted to the native Run engine. | `src/lychd/agents/router.py` |
| **Invocation** | One admitted execution pinned to a Pattern revision, authority context, Run identity, and continuity contract. | Weaver (ADR 28) |
| **Iron Pact** | The MPL-2.0 license and inbound-equals-outbound contribution policy with no CLA or private relicensing grant. | Repository root |
| **issue_grant** | The `AnimatorRegistry` method that assembles a `CapabilityGrant` for one warm capability without changing lifecycle state. | `src/lychd/domain/animation/services/registry.py` |
| **Karma** | Governed, attributable residue of witnessed action, correction, consent, and consequence retained as formative precedent. | [Illumination](../divination/transcendence/illumination.md) + Memory (ADR 27) |
| **Kinetic** | The vLLM Soulstone discipline for continuous-batched, VRAM-strict parallel serving. | [Soulstone](../sepulcher/animator/soulstone/disciplines.md#i-the-kinetic-vllm) |
| **Lab** | The repository's `lab/` development sandbox. | Filesystem Layout |
| **lease drain** | The Orchestrator's wait for all GrantLeases on Animators selected for eviction to be released. | `src/lychd/domain/orchestration/` |
| **LeaseLedger** | The in-process registry whose live GrantLeases are the Orchestrator's drain truth. | `src/lychd/domain/cortex/leases.py` |
| **Legion** | The distributed-embodiment Extension Domain for fenced delegation across operator-owned nodes. | [Legion](../sepulcher/extensions/legion.md) + ADR 42 |
| **Legionnaire** | Legion's name for an enrolled operator-owned compute node with its own identity, resource authority, journal, and fencing. | [Legion](../sepulcher/extensions/legion.md) + ADR 42 |
| **Lens** | A bounded Posture template used to seed an isolated Shadow branch. | [Agents (ADR 20)](../adr/20-agents.md#mechanical-cognitive-postures) + Simulation (ADR 31) |
| **Lich** | The recurrent whole formed by the Vessel, Phylactery, agents, Animators, identity, action, consequence, memory, repair, and relation through time. | [ADR 01](../adr/01-doctrine.md) + [Immortality](../divination/transcendence/immortality.md) |
| **Live Stasis** | A resident in-process pause that resumes itself when the required substrate becomes ready. | [Graph (ADR 24)](../adr/24-graph.md) |
| **Long Sleep** | Durable Stasis for a wait that must survive process death, such as reboot, deferred approval, or peer delay. | [Graph (ADR 24)](../adr/24-graph.md) |
| **Loom** | The Altar instrument for inspecting immutable Pattern revisions and Weaver-authored possibility. | [Altar Loom](../divination/altar/loom.md) + Weaver |
| **LychD** | The self-hosted Linux daemon for local model services and agent runs; its recurrent whole is the Lich. | [ADR 01](../adr/01-doctrine.md) + [Transcendence](../divination/transcendence/index.md) |
| **Magus** | The human operator in deliberate relation with the Lich through configuration, witness, consent, refusal, and correction. | [ADR 01](../adr/01-doctrine.md) + [Immortality](../divination/transcendence/immortality.md) |
| **Manifestation** | The concrete form an Extension Domain takes in one assembled body or profile. | ADR 05 + [State](../state-of-the-work.md) |
| **Mirror** | The identity Extension Domain for versioned Persona lineage, hydration provenance, attribution, and declared continuity. | [Mirror](../sepulcher/extensions/mirror.md) + ADR 32 |
| **Necropolis** | The designed peer-to-peer topology in which sovereign LychD nodes negotiate bounded work over A2A. | [A2A (ADR 26)](../adr/26-a2a.md) |
| **Nexus** | The Altar instrument projecting Animator readiness, grants, leases, resource evidence, and Orchestrator transitions. | [Altar Nexus](../divination/altar/nexus.md) + Orchestrator |
| **Occurrence** | One uniquely identified firing of a schedule or external trigger, deduplicated before Invocation admission. | [Compositions](../compositions/index.md) + Weaver (ADR 28) |
| **Oculus** | The designed evidence Extension Domain for bounded observations, correlation, explicit gaps, and rebuildable read models. | [ADR 29](../adr/29-observability.md) + [State](../state-of-the-work.md) |
| **Orb** | The Altar instrument for inspecting one Run's retained evidence, capture boundaries, gaps, and correlations. | [Altar Orb](../divination/altar/orb.md) + Oculus (ADR 29) |
| **Orchestrator** | The state machine that plans and governs Animator and container lifecycle transitions. | `src/lychd/domain/orchestration/` |
| **Ouroboros** | The return by which consequence, evaluation, attribution, memory policy, and consent may shape a later Invocation. | Evolution + Lich |
| **Pattern** | A Weaver-owned workflow family defining typed state, stations, gates, requirements, budgets, outcomes, and continuity law. | Weaver (ADR 28) |
| **Pattern Revision** | One immutable executable score and checkpoint-compatibility contract within a Pattern family. | Weaver (ADR 28) |
| **Persona** | A durable, revisioned identity and voice definition that Mirror may hydrate into a bounded Agent instruction envelope. | [Mirror](../sepulcher/extensions/mirror.md) + ADR 32 |
| **Phantasma** | Shadow's mode for expanding isolated speculative branches before measurement. | [Shadow](../sepulcher/extensions/shadow/index.md) + ADR 31 |
| **Phoenix** | The Arize-owned external observability project retained as an optional Eye. | [ADR 29](../adr/29-observability.md) + [State](../state-of-the-work.md) |
| **Phylactery** | The PostgreSQL-centered durable-data jurisdiction for committed Run truth and other durable application records. | `src/lychd/db/`; [ADR 06](../adr/06-persistence.md) + [State](../state-of-the-work.md) |
| **Portal** | A remote-service Animator backed by a Portal Rune. | `src/lychd/domain/animation/` |
| **Portal Rune** | A validated Codex TOML declaration of remote endpoint, provider, model defaults, capabilities, tools, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Portfolio** | The designed Weaver registry of Reference Compositions and their enablement, Pattern, and schedule catalogues. | [Compositions](../compositions/index.md) + Weaver (ADR 28) |
| **Posture** | A per-run Agent specialization expressed through output schema, tool grant, model settings, and prompt frame. | [Agents (ADR 20)](../adr/20-agents.md#mechanical-cognitive-postures) |
| **Prism** | The vision Extension Domain for source-grounded regions, frames, transforms, and visual observations. | [Prism](../sepulcher/extensions/prism.md) + ADR 36 |
| **Privacy Cut** | A new sanitized Context branch built locally without reusing raw history, continuation, attachment projections, or provider cache identity. | [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut) |
| **Privatization Label** | Privacy class, weight, categories, subjects, lineage, and handling constraints that conservatively follow material influence. | [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut) |
| **Provenance** | The attributable origin, identity, transformations, evidence, and correction history of a claim, artifact, or consequence. | Phylactery + Memory (ADR 27) |
| **Provider** | A concrete engine or service implementing a typed contract owned by a Domain. | Animator + ADR 05 |
| **Provider Gate** | The fail-closed credential and egress mediator exposing one admitted provider surface to a Coffin without disclosing the real secret. | [Security (ADR 09)](../adr/09-security.md#provider-gate) |
| **Pulse** | The `lychd` operator CLI and its closed `init`, `bind`, `start`, `stop`, `status`, `logs`, `run`, and `del` grammar. | [ADR 19](../adr/19-cli.md) + `src/lychd/cli/` |
| **Quadlet Manifest** | A generated Podman/systemd `.container`, `.pod`, `.target`, or `.volume` artifact written to the binding site. | `src/lychd/system/schemas.py` |
| **Radix** | The SGLang Soulstone discipline for radix-tree prefix caching of iterative and multi-turn prompts. | [Soulstone](../sepulcher/animator/soulstone/disciplines.md#ii-the-radix-sglang) |
| **Reanimation** | Process-death recovery that reconciles durable Run, queue, and checkpoint truth from a supported Durable Stasis boundary. | Phylactery |
| **Reaper** | Shadow's designed hygiene Ghoul for releasing branch-owned workspaces and resources while preserving required failure evidence. | [Simulation (ADR 31)](../adr/31-simulation.md#the-branch-reaper) |
| **Recall** | A retained Seed becoming active in present Flux after retrieval and Context make it available. | [Recall](../sepulcher/lich/spirit/recall.md) |
| **Reference Composition** | An accepted operator-visible application architecture assembled from Patterns, Agents, capabilities, policies, data, and projections. | [Compositions](../compositions/index.md) + Weaver (ADR 28) |
| **Reliquary** | A designed artifact-custody lifecycle for immutable lineage, authorized retrieval, comparison, and retention. | [Artifact-reference boundary](../state-of-the-work.md#artifact-reference-contract) + [Phylactery](../sepulcher/phylactery/index.md) |
| **Riddle** | The evaluation Extension Domain for versioned trials, controls, repeated Outcomes, calibrated findings, attribution candidates, and uncertainty. | [Riddle](../sepulcher/extensions/riddle/index.md) + ADR 34 |
| **Run** | The executable and ledger record through which the current implementation represents one Invocation. | `src/lychd/db/models/run.py`; Weaver (ADR 28) |
| **Rune** | One validated TOML declaration of configuration intent under the Codex `runes/` tree. | `src/lychd/config/runes/` |
| **Scout** | The web-acquisition Extension Domain for separately authorized search, fetch, extraction, crawl, render, interaction, and capture. | [Scout](../sepulcher/extensions/scout.md) + ADR 30 |
| **Scrying** | The disciplined inspection of execution evidence through the Orb. | [Altar Orb](../divination/altar/orb.md) + Oculus (ADR 29) |
| **Seed** | A trace or inherited disposition that retains governed potency to shape a later Flux. | [Seed](../sepulcher/lich/spirit/seed.md) |
| **Sepulcher** | LychD's rootless runtime body of pods, services, mounts, and execution topology. | Infrastructure |
| **Shadow** | The possibility-lineage Extension Domain for isolated candidate worlds with exact parentage, evidence, and terminal disposition. | [Shadow](../sepulcher/extensions/shadow/index.md) + ADR 31 |
| **Shadow Realm** | Shadow's speculative state and Jujutsu workspace topology, distinct from the Tomb execution plane. | [Shadow](../sepulcher/extensions/shadow/index.md) |
| **Sigil** | The secret-free identity and bounded authority context carried through an admitted request or Run. | `src/lychd/domain/codex/sigil.py`; ADR 09/32/38 |
| **Smith** | The Assimilation Extension Domain's artificer Agent for producing attributable candidate organs from foreign material. | [Smith](../sepulcher/extensions/smith.md) + ADR 35 |
| **Soulforge** | The training Extension Domain binding admitted corpus, base-model digest, objective, recipe, trainer Run, and candidate-weight lineage. | [Soulforge](../sepulcher/extensions/soulforge/index.md) + ADR 33 |
| **Soulstone** | A local-service Animator backed by a Soulstone Rune and managed through Quadlet/systemd. | `src/lychd/domain/animation/` |
| **Soulstone Rune** | A validated Codex TOML declaration of a local Animator's image, runtime, port, Coven, models, mounts, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Sovereignty Wall** | The Security-owned privacy and egress boundary enforced by Dispatcher routing. | Security + Dispatcher |
| **Spheres** | The strict volume-mount and filesystem-permission topology of the Crypt. | [Crypt](../sepulcher/crypt.md#the-spheres) + ADR 13 |
| **Spirit** | The conditioning and remembering office that bears retained form through Flux, Seed, and Recall. | [Spirit](../sepulcher/lich/spirit/index.md) |
| **Stasis** | A Run paused at a recoverable boundary as either resident Live Stasis or checkpointed Durable Stasis. | Graph (ADR 24) + Orchestrator (ADR 23) |
| **Stillness** | The discipline of bounded work that avoids needless residency, disruptive swaps, and unbounded speculation while preserving measured quality. | Orchestrator (ADR 23) + Riddle (ADR 34) |
| **Suite** | A designed, versioned graph of separately owned Compositions and typed handoffs. | [Compositions](../compositions/index.md) + Weaver (ADR 28) |
| **Summoning** | The canonical same-host first-life tutorial from preflight through unit, runtime, and Bridge observations. | [Summoning](../summoning.md) + [State](../state-of-the-work.md) |
| **Tether** | The private-reachability Extension Domain, planned to manifest through managed WireGuard or external attachments. | [Tether](../sepulcher/extensions/tether.md) + ADR 39 |
| **The Tomb** | The `lychd-tomb` execution plane for disposable payloads and workspaces under narrow credentials and sandboxing. | [Security (ADR 09)](../adr/09-security.md#6-tomb-execution-contract) |
| **Titan** | The llama.cpp Soulstone discipline for serial CPU offload beyond the VRAM envelope. | [Soulstone](../sepulcher/animator/soulstone/disciplines.md#iii-the-titan-llamacpp) |
| **Tithe** | Currency-neutral accounting and bounded quota for compute resources independently of payment. | [Toll](../sepulcher/extensions/toll.md) + ADR 41 |
| **Toll** | The optional economics Extension Domain separating quote, commitment, signing, settlement, delivery, refund, and reconciliation. | [Toll](../sepulcher/extensions/toll.md) + ADR 41 |
| **Transcendence** | The public house of the Great Work's constitutional telos, synthesis, rites, conjectures, and alchemical journey. | [Transcendence](../divination/transcendence/index.md) |
| **TransformationReceipt** | A secret-free binding of source and candidate digests, transformer and policy revisions, operations, residual label, uncertainty, and expiry. | [Context (ADR 21)](../adr/21-context.md#privatization-and-the-privacy-cut) |
| **typed handoff** | A schema-versioned attributable ArtifactRef or new Intent crossing between separately admitted Compositions. | [Composition Portfolio](../compositions/index.md#suites-do-not-dissolve-their-members) + Weaver (ADR 28) |
| **Veil** | The hostile-ingress Extension Domain, planned to manifest through managed Caddy or an external edge. | [Veil](../sepulcher/extensions/veil.md) + ADR 40 |
| **Vessel** | The Litestar application runtime and web server. | `src/lychd/app.py` |
| **Ward** | The authority Extension Domain mapping credentials to principals and current object or effect policy. | [Ward](../sepulcher/extensions/ward.md) + ADR 38 |
| **Weaver** | The workflow-application control plane for Portfolio and Pattern lifecycle, admission, logical priority, dependencies, and schedule meaning. | [Weaver](../sepulcher/extensions/weaver/index.md) + ADR 28 |
| **Whim** | The designed priority-weighted Orchestrator strategy whose current Codex fields are validated but inert. | [Orchestrator (ADR 23)](../adr/23-orchestrator.md#1-the-tipping-point-whim-algorithm) |
| **Whispers** | LychD's systemd journal stream, read through `lychd logs` or `journalctl --user`. | Systemd |
| **xDDD** | eXtreme Documentation Driven Development: establish the governing Logos before deriving implementation. | Doctrine (ADR 01) |
