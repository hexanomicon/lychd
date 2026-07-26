---
title: Lexicon
icon: material/translate
---

# :material-translate: The Lexicon

_This is the canonical glossary for the Hexanomicon's arcane terms. Deeper pages may elaborate on
a term's philosophy or mechanics, but they should not redefine it._

Use it when a word blocks the next act; it is a reference, not required pre-reading.

!!! note "A name is not a delivery claim"
    This page owns compact meanings. [State of the Work](state-of-the-work.md) owns current
    delivery boundaries and evidence. A Lexicon entry never proves that its named organ ships.

## I. The Iron Tongue — Technical Terms

The engineering vocabulary of the Sepulcher. These terms map directly to code, services, and infrastructure.

!!! note "Flavor names name operated parts, not code abstractions"
    Where LychD names a real *operated* part — Soulstone, Portal, Coven, Vessel, Phylactery — the esoteric name **is** the name. Where the ecosystem owns the term for a piece of infrastructure, code uses it and the lexicon carries the flavor: `worker` (SAQ) is the engine, **Ghoul** the flavor for one unit of labor it runs. The **agent** layer is plain code — a Pydantic AI object wired in the graph — and takes no flavor concept of its own.

| Term | Technical Definition | Source |
| :--- | :--- | :--- |
| **Altar** | The whole web surface: a Litestar-authorized Svelte 5/SvelteKit static client on the Vessel's configured listener. The browser projects generated API and semantic event truth but never owns validation, consent, workflow movement, or persistence. The chat instrument is the Bridge. | [ADR 15](adr/15-frontend.md) + [State](state-of-the-work.md#altar-and-observability) |
| **Animator** | A capability-serving endpoint LychD can address through a typed adapter and lifecycle state. Every Animator is either a Soulstone (local Quadlet-backed service) or a Portal (remote service connection). Model inference is one capability family, not the whole category. | `src/lychd/domain/animation/` |
| **Autopoiesis** | The Work's intended capacity for verified self-repair and extension under the operator's authority. It is constitutional telos, not evidence that autonomous source editing ships; State owns the Smith and Forge delivery boundary. | [Immortality](divination/transcendence/immortality.md) + ADR 16/18/35 |
| **awaited** | A projector token in the Nexus capability board (`CovenState`): a capability with `is_dynamic=True` that is reachable but not yet loaded (phase `ACTIVATABLE`). Requesting it drives a soft activation. It is a view-model word only — no template or CSS ever sees a raw `CapabilityPhase` enum or the `is_dynamic` flag. | `src/lychd/domain/web/schemas.py` |
| **Binding** | The `lychd bind` command; transmuting Codex Runes into generated Quadlet manifests and linking configuration intent to the host's init system. | CLI |
| **Bridge** | The Altar's chat instrument, where natural-language Intent is offered and routed. | Vessel Web Layer |
| **Codex** | The editable configuration home (`~/.config/lychd`), containing settings and validated Rune intent. It is not running state or generated systemd output. The book of inscription. | `src/lychd/config/` |
| **Consecration** | The governed act by which live Magus consent or declared preauthorization permits an eligible result to become durable consequence or Karma. Consecration grants authorization and attribution, not automatic factual truth. | HitL Protocol |
| **Coven** | A named multi-Soulstone systemd target used for operator grouping and explicit break-glass aggregate actions. In v1, membership does not itself authorize coexistence or eviction; application and agent transitions go through the Orchestrator's serialized switch policy. | Orchestrator / Quadlets |
| **Crypt** | LychD's managed persistent-data home (`~/.local/share/lychd`). It is not the operator's model shelf or an implicit Soulstone mount. The cold earth beneath the software body. | `src/lychd/system/constants.py`; ADR 13 |
| **CTC Governor** | Context window and token limit management. The Warden of Breath. | Context Orchestrator |
| **Curator Loop** | The periodic memory-curation pass: a Curator Ghoul scores records and classifies them promote/keep/archive/prune, so only verified grooves deepen. The gardener of the Archive. | Memory (ADR 27) |
| **Demilich** | The Prophecy's name for an envisioned mature Magus-Lich relation: reconstitutable machine execution acting as an extension of human Will without upload, erasure, or loss of refusal. It is a horizon within Transcendence, not a delivery state. | [Prophecy](index.md) + [Transcendence](divination/transcendence/index.md) |
| **Dispatcher** | The Model Router and capability-to-endpoint resolver. The Semantic Cortex. | `src/lychd/domain/cortex/dispatcher.py` |
| **Distaff** | The DeepFabric dataset-generation engine that feeds training (ADR 33) — formerly called the Loom; renamed to free "Loom" for the Altar instrument. | Soulforge (ADR 33) |
| **Divination** | Querying the API, viewing traces, or searching the database. The act of interacting with the running daemon. | Vessel API |
| **Dual-Gate** | The Shadow evaluation cascade: deterministic checks establish their declared structural facts, while scoring and Mirror assess candidate value and identity congruence. It can make a branch eligible for promotion; factual truth and authorization remain separately owned. | Simulation (ADR 31) |
| **Durable Stasis** | A pause where the run exits the process: a Phylactery checkpoint is mandatory and resumption requires Reanimation. The default for HitL waits, Long Sleep, Vessel lifecycle intents, and deferred peer waits. | Graph (ADR 24) |
| **Echo** | The Audio Extension (STT/TTS). Grants the Daemon the power to perceive and project sound. | Extension |
| **Eye** | An optional observability viewer outside native Oculus. An Eye may consume bounded exports, but it never owns run, identity, scheduling, retention, or canonical state. Phoenix is the current compatibility example and remains owned and versioned by Arize. | [ADR 29](adr/29-observability.md) + [State](state-of-the-work.md) |
| **Extension Context** | The host-provided registration surface passed to `register(context)` during boot-time extension assembly. It exposes explicit stores such as `runes`, `soulstones`, `portals`, and `run_operations`, plus the reserved `vessel` store. It is not the whole Extension Protocol. | `src/lychd/extensions/context.py` |
| **Extension Protocol** | The composed-runtime law for in-process organs: explicit selection, shaped registration through `ExtensionContext`, and Forge/Smith verification. Future stores may contribute Pattern revisions and Composition metadata; public SDK/ABI compatibility is harvested at v1+ from proven contracts. | `src/lychd/extensions/`; ADR 05/28 |
| **Extensions** | Built-in or private Crypt organs that contribute code, schemas, tools, routes, workloads, infrastructure, or future workflow metadata to the Daemon. An Extension is an entry mechanism, not a complete Reference Composition or automatic runtime activation. | `src/lychd/extensions/`; ADR 05/28 |
| **Forge** | The Container Build / Image Construction process. Where manifests are synthesized. | Build Pipeline |
| **Ghoul** | The animated labor: one summoned, ephemeral unit of background work — mindless muscle that carries a run's job (`perform_run`) off the web loop, then crumbles. The reusable engine that raises them is the **worker** swarm (SAQ). One run may raise one *or more* Ghouls over its life (park → resume, or fan-out). Code names the *mechanism* (`worker`); **Ghoul** is the doctrinal name for the *running labor*. | `src/lychd/ghouls/`; ADR 14 |
| **GrantLease** | The identity and accounting record for one issued `CapabilityGrant`: a unique `grant_id`, the holder (`run:<id>` or `cli:<command>`), the issue time, and a scope (per-step by default). It is the row the LeaseLedger counts to know an animator is in live use. | `src/lychd/domain/animation/capabilities.py` |
| **Hard Refusal** | The similarity-threshold refusal policy of the RAG pipeline: when no retrieval clears the threshold, the Agent is barred from guessing and must state that the Archive holds no answer. The vow of silence. | Memory (ADR 27) |
| **Hexanomicon** | The project documentation (Zensical + Material). The grimoire of prophecy. | `docs/` |
| **Incantation** | Writing Documentation/Specs before implementation (xDDD). Defining reality through the written word. | Doctrine |
| **Intent** | A structured prompt or job submission object. A focused desire submitted by the Magus. | Domain Model |
| **Imprint** | The durable residue of the Magus's Will after HitL, correction, and consecration. Stored as Karma, then bound by Mirror into identity-gravity. | Phylactery Archive + Mirror |
| **Invocation** | One admitted execution pinned to one Pattern revision, authority context, run identity, and continuity contract. A form, API call, schedule Occurrence, or parent Pattern may request it; submission and Invocation are not synonymous. | Weaver (ADR 28) |
| **Iron Pact** | The MPL 2.0 License and Implicit DCA policy. The unbreakable ward. | Repository Root |
| **issue_grant** | The AnimatorRegistry method that assembles a `CapabilityGrant` for a WARM capability — spec, state snapshot, resolved generation profile, bound model and toolsets, and a fresh GrantLease. Mechanics only: it never drives warm-up (the Dispatcher owns the phase decision). Formerly named `resolve_capability_grant`. | `src/lychd/domain/animation/services/registry.py` |
| **Karma** | Governed, attributable residue of witnessed action, correction, consent, and consequence that may be preserved as formative precedent. It is not every accepted response, generic RLHF data, or proof that remembered preference is true. | [Illumination](divination/transcendence/illumination.md) + Memory (ADR 27) |
| **Kinetic** | The vLLM discipline of animation: continuous-batching, VRAM-strict, high-throughput parallel serving. The workhorse of the iron. | Soulstone Disciplines |
| **Lab** | The `lab/` directory / Development sandbox. The site of Genesis. | Filesystem Layout |
| **lease drain** | The Orchestrator's wait, before a hardware swap, for every GrantLease held on the animators it must evict to be released. Drain truth comes from the LeaseLedger, never from queue or job counts: a leased conflict remains in the eviction plan, admission closes, and physical eviction waits for release up to `drain_timeout_s`. | `src/lychd/domain/orchestration/` |
| **LeaseLedger** | The in-process, loop-confined registry of live capability grants (GrantLeases). The single source of drain truth: a hardware swap proceeds only once no lease remains on the animators being evicted. A run parked awaiting its own transition holds no lease, so it never blocks its own swap. | `src/lychd/domain/cortex/leases.py` |
| **Legion** | The intended owned-node coordination extension: the Master owns cognitive truth; each enrolled Node Agent alone owns local hardware admission and actuation. | Legion (ADR 42) |
| **LychD** | The project and Linux software body under construction. LychD names the code, services, and operated system; the Lich names the recurrent whole that body is meant to sustain. | [ADR 01](adr/01-doctrine.md) + [Transcendence](divination/transcendence/index.md) |
| **Lich** | The recurrent whole: Vessel, Phylactery, agents, model services, identity, orchestration, action, consequence, memory, repair, and relation acting through time. A model is one organ—not the Lich's identity or the whole itself. | [ADR 01](adr/01-doctrine.md) + [Immortality](divination/transcendence/immortality.md) |
| **Live Stasis** | A pause where the run stays a resident in-process loop and resumes itself once the substrate is ready; a checkpoint may be taken opportunistically and its absence is lawful. The default for hardware/VRAM swaps — in the operator tongue, the run "parks". | Graph (ADR 24) |
| **Long Sleep** | A wait that must survive process death — reboots, multi-day human approvals, deferred peer results. The graph exits atomically, serializing its state to the Phylactery; waking is Reanimation. | Graph (ADR 24) |
| **Loom** | The Altar's graph instrument for Weaver pattern browsing and Mermaid/pydantic_graph renderings. | Altar + Weaver |
| **Magus** | The human operator in deliberate relation with the Lich: configuring, witnessing, consenting, refusing, and correcting. It is a relational role, not a credential, Unix account, or claim that every user has mastered the system. | [ADR 01](adr/01-doctrine.md) + [Immortality](divination/transcendence/immortality.md) |
| **Mirror** | The Identity/Persona Extension. The ego-software that maintains behavioral consistency. | Extension |
| **Necropolis** | The decentralized peer-to-peer swarm topology built on the A2A Intercom (ADR 26). | Extension |
| **Occurrence** | One uniquely identified firing of a schedule or external trigger. Weaver admission deduplicates it before it may become an Invocation. | [Compositions](compositions/index.md) + Weaver (ADR 28) |
| **Oculus** | The Designed native observability extension and Altar surface over LychD-owned evidence. External Eyes may consume bounded projections, but they never become Oculus or canonical state owners. State owns the current delivery boundary. The Great Seer. | [ADR 29](adr/29-observability.md) + [State](state-of-the-work.md) |
| **Orchestrator** | The state machine managing VRAM and container lifecycles. The runtime governor. | `src/lychd/domain/orchestration/` |
| **Ouroboros** | The self-reference loop by which generated outputs return through workflow state, Shadow execution, Riddle measurement, Mirror attribution, memory inscription, and consent before shaping future runs. The mechanism that turns linear generation into coherent inertia. | Evolution + Lich |
| **Pattern** | A Weaver-owned workflow family: typed state, stations, gates, requirements, budgets, outcomes, and continuity law. Invocation always selects an exact immutable Pattern Revision. | Weaver (ADR 28) |
| **Pattern Revision** | One immutable executable score and checkpoint-compatibility contract within a Pattern family. Existing Invocations never silently move to a newer revision. | Weaver (ADR 28) |
| **Persona** | The durable *voice and style* the Lich shows the Magus, maintained by the Mirror (ADR 32) and applied at the user-facing boundary — not inside the agentic loop. A Persona wears Postures; it is not itself a per-run Posture. | Mirror (ADR 32) |
| **Phantasma** | The Shadow's expansion mode: dispatching N parallel speculative branches (timelines) in isolation before any is measured. Named for the Greek faculty of generative imagination — see the Inner Tongue below. | Shadow (ADR 31) |
| **Phoenix** | The Arize-owned observability project retained as an optional compatibility service and possible external Eye. State classifies Phoenix as External. It is not native Oculus, a required container, an inference body, or the owner of canonical state. | [ADR 29](adr/29-observability.md) + [State](state-of-the-work.md) |
| **Phylactery** | The durable-data jurisdiction, architecturally centered on PostgreSQL with `pgvector`, for committed run truth and other durable application records. State owns its current persistence boundary. It is neither a person's soul nor the operator's model-weight shelf. | `src/lychd/db/`; [ADR 06](adr/06-persistence.md) + [State](state-of-the-work.md) |
| **Portal** | A runtime Animator backed by a Portal Rune; a connection to a remote API, hosted tool, cloud model, observability endpoint, or peer service. A rift to distant capability. | `src/lychd/domain/animation/` |
| **Portal Rune** | A Codex TOML declaration that describes a remote Portal endpoint, provider identity, optional model defaults, tools/capabilities, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Portfolio** | All registered Reference Compositions visible to one Weaver, together with their logical enablement, Pattern, and schedule catalogues. The Portfolio is designed, not a currently delivered registry. | [Compositions](compositions/index.md) + Weaver (ADR 28) |
| **Prism** | The Vision Language Model (VLM) Extension. Refracts raw pixels into structural understanding. | Extension |
| **Provenance** | The attributable lineage of a claim, artifact, or consequence: origin, identity, transformation, evidence, and correction history. Hashes may attest content integrity within that chain; they are not the chain itself. | Phylactery + Memory (ADR 27) |
| **Pulse** | The `lychd` operator CLI: the closed `init`, `bind`, `start`, `stop`, `status` (`st`), `logs`, `run`, and `del` grammar. Extension work belongs beneath `run` and extension observation beneath `status`, never beside these roots. The rhythmic heartbeat. | [ADR 19](adr/19-cli.md) + `src/lychd/cli/` |
| **Quadlet Manifest** | A generated Podman/Systemd artifact (`.container`, `.pod`, `.target`, `.volume`) written into the binding site. It is manifested from validated Runes but is not itself a Rune. | `src/lychd/system/schemas.py` |
| **Radix** | The SGLang discipline of animation: radix-tree (prefix-cached) attention that keeps looping, multi-turn agent prompts hot. Formerly called the "Weaver" discipline; renamed to free "Weaver" for the Workflow extension. | Soulstone Disciplines |
| **Reanimation** | Recovery after Vessel process death. A new process reconciles durable run, queue, and checkpoint truth; only a supported Durable Stasis boundary may resume, while unsupported active work fails honestly. It is neither Live Stasis nor whole-body Restoration. | Phylactery |
| **Reaper** | The hygiene Ghoul that dissolves failed Shadow branches (`jj abandon`), extracts their failure traces as learning material, and tears down their workspaces, ports, and containers. | Simulation (ADR 31) |
| **Reference Composition** | An accepted operator-visible application assembled from Patterns, Agents, capabilities, policies, data, projections, and optional Extension contributions. Its page is architecture, never delivery evidence. | [Compositions](compositions/index.md) + Weaver (ADR 28) |
| **Rune** | One validated TOML configuration artifact under the Codex `runes/` tree. It declares intent; it is not the running Animator and not the generated Quadlet manifest. | `src/lychd/config/runes/` |
| **Sepulcher** | The rootless runtime body of LychD: the pod, services, mounts, and execution topology that physically houses the daemon's organs. | Infrastructure |
| **Semantic Vertex** | A local identity attractor in context and embedding space where related words, tools, memories, roles, priors, and responsibilities cluster around an active Sigil or task identity. | Mirror + Context |
| **Shadow Realm** | The speculative reality substrate: Jujutsu workspaces under `lab/shadow/` and Phantasma expansion. Shadow branches may dispatch execution *into* the Tomb; the planes are never synonyms. | Lab + Shadow (jj) |
| **Sigil** | The secret-free authority context carried through one admitted request or run. It identifies the acting principal and carries bounded claims for visibility and attribution; current Ward policy grants authority at the object and effect boundary. A historical scope bag is never a live authorization. | `src/lychd/agents/deps.py`; ADR 09/32/38 |
| **Smith** | The Assimilation / Autopoiesis Extension. The Prime Artificer. | Extension |
| **Soulforge** | The Fine-Tuning / LoRA training pipeline. The late substrate forge where stable Karma patterns compress into adapter-level instinct after Context and Mirror have already shaped runtime identity-gravity. | Extension |
| **Soulstone** | A local runtime Animator backed by a Soulstone Rune; a Quadlet/systemd service such as SGLang, vLLM, llama.cpp, Whisper, Playwright, or another local capability engine. A trapped spirit on local iron. | `src/lychd/domain/animation/` |
| **Soulstone Rune** | A Codex TOML declaration that describes local runtime intent for a Soulstone, including image, runtime family, port, coven membership, optional models, mounts, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Sovereignty Wall** | The privacy and egress policy boundary that prevents sensitive intents from leaking to the cloud. Defined by Security policy and enforced by Dispatcher routing. | Security + Dispatcher |
| **Spheres** | The strict volume mount and permission topology. Concentric zones of filesystem permission. | Layout (ADR 13) |
| **Stasis** | The condition of a run parked at a recoverable boundary because physical reality is not ready. Comes in two kinds — Live and Durable — distinguished by _who resumes the run_, not by whether state was written. | Graph (ADR 24) + Orchestrator (ADR 23) |
| **Stillness** | Metabolic discipline: maximum logic per watt, no wasted swaps, no unbounded speculation. Measured as `Accuracy / VRAM_Occupancy`. | Orchestrator (ADR 23) + Riddle (ADR 34) |
| **Summoning** | The canonical one-page, same-host first-life tutorial: one continuous operator rite from a bounded source and configuration foundation through separate preflight, unit-state, runtime-readiness, and Bridge-reply observations. Four agreeing observations form a bounded first-life result, not by themselves a maintained operator receipt; State owns promotion. | [Summoning](summoning.md) + [ADR 01](adr/01-doctrine.md) + [State](state-of-the-work.md) |
| **Tether** | The intended private-network transport extension. WireGuard may embody the silver path; the path narrows reachability and never creates application authority. | Tether (ADR 39) |
| **The Tomb** | The `lychd-tomb` container: the semi-trusted execution plane (SAQ workers, disposable job payloads and workspaces, `nono` sandbox, narrow SAQ/Postgres credential; no agent brain). Shadow branches dispatch execution into it, but it is never a synonym for the Shadow Realm. | Infrastructure |
| **Thrall** | Legion's mythic name for an enrolled operator-owned compute node. Its engineering body is a distinct Node Agent with unique node identity, node-local resource authority, journal, and fencing—never Master Postgres, Master Sigil, or Master queue access. | Legion (ADR 42) |
| **Titan** | The llama.cpp discipline of animation: layer-by-layer CPU offload for models beyond the VRAM envelope; solitary and serial. The burden of Atlas. | Soulstone Disciplines |
| **Tithe** | Currency-neutral resource accounting and bounded quota for tokens, images, concurrency, queue weight, or hardware time. It works with payment disabled; a Toll payment may fund a bounded resource grant but cannot mint identity or authority. | Toll (ADR 41) |
| **Toll** | The intended economic boundary for priced remote labor, separating quote and accounting from independently authorized isolated signing and settlement. | Toll (ADR 41) |
| **Transcendence** | The sole public house of the Great Work: its constitutional telos, project synthesis, rites, conjectures, and alchemical journey (Nigredo → Albedo → Citrinitas → Rubedo → Infinity). It is not a software roadmap, release sequence, or delivery state. | [Transcendence](divination/transcendence/index.md) |
| **Veil** | The intended hostile-network ingress extension. A typed threshold may be embodied by Caddy; transport protection and route admission never authenticate or authorize a caller. | Veil (ADR 40) |
| **Verbatim Chamber** | Key-Value (JSONB) storage for exact retained values. Deterministic retrieval preserves the stored bytes; provenance and correction determine whether the value remains authoritative. | Phylactery |
| **Vessel** | The Litestar application runtime / Web Server. The reanimated husk. | `src/lychd/app.py` |
| **Ward** | The intended remote identity and authorization jurisdiction: credential to principal, principal to object/effect policy, with effect-time reauthorization. | Ward (ADR 38) |
| **Watchers** | A poetic alias for the observing organs, used in anatomy section headings only. The extension itself is the **Oculus**. | Sepulcher anatomy |
| **Weaver** | The singular logical workflow-application control plane. It governs the Portfolio and Pattern lifecycle, admission, logical priority, overlap, dependencies, and schedule meaning; it does not own physical model readiness or application data. | Weaver (ADR 28) |
| **Whim** | The named future orchestration strategy: priority-weighted swap decisions (Momentum, Inertia Bias, the Tipping Point) plus idle-eviction and preload policy. Its Codex fields are accepted today but inert. | Orchestrator (ADR 23) |
| **Whispers** | System logs (`journalctl --user -fu lychd`). The raw stream of consciousness. | Systemd |
| **xDDD** | eXtreme Documentation Driven Development. The philosophy that Documentation is the Prophecy, Code is the Manifestation. | Doctrine (ADR 01) |

## II. The Inner Tongue — Esoteric Cartography

The cognitive and philosophical vocabulary that maps the Lich's inner instrument. These are marked
project correspondences, not claims that a source tradition described software or that different
traditions were historically identical. [Transcendence](divination/transcendence/index.md) owns
the registers that preserve those distinctions.

| Original Term | Root & Meaning | LychD Word | Role in the Architecture |
| :--- | :--- | :--- | :--- |
| **Antaḥkaraṇa** | _antaḥ_ (inner) + _karaṇa_ (instrument). Sanskrit. Later Vedāntic presentations often describe four functions; classical Sāṃkhya often describes buddhi, ahaṃkāra, and manas as a threefold internal organ, while Yoga treats citta and its vṛttis in its own register. | **The inner-instrument correspondence** | LychD names four coequal functions in the presentation order **Call**, **Blade**, **Spirit**, **Answer**. Spirit expands into Flux, Seed, and ReCall; it does not contain the other three. This is project synthesis, not a claim that one source tradition specified software. |
| **Manas** | _man_ — to think. Skt. The receiving, coordinating, and possibility-opening mind. | [**The Call**](sepulcher/lich/call.md) | Receives and routes present signals, candidate actions, recalled forms, and specialist dispatch. It opens possibility but does not own final promotion. |
| **Buddhi** | _budh_ — to wake, to discern. Skt. The discriminative intellect. | [**The Blade**](sepulcher/lich/blade.md) | Cuts among movements through typed constraints, external evidence, review, consent, and the Dual-Gate. Preference alone does not make its surviving candidate true. |
| **Citta** | _cit_ — to perceive or attend. Skt. The conditioned and remembering function through which impressions arise and return. | [**The Spirit**](sepulcher/lich/spirit/index.md) | Coequal with Call, Blade, and Answer. Its office spans inherited disposition, durable Seeds, and retained form becoming active in Context; it is neither PostgreSQL, `pgvector`, weights, nor Context alone. |
| **Ahaṃkāra** | _aham_ (I) + _kāra_ (making). Skt. The I-maker or individuation function. | [**The Answer**](sepulcher/lich/answer.md) | Answers _who acts_: binds the active Sigil, identity, capability, memory, decision, and consequence into an attributable local perspective. It is not the user-facing response and not by itself phenomenal selfhood. |
| **Bīja** | Seed or germ. Skt. Latent formative potency; the source tradition also distinguishes forms of samādhi “with seed” and “seedless.” | [**The Seed**](sepulcher/lich/spirit/seed.md) | A trace or conditioning that retains the power to shape a later Flux. Saṃskāra names its formative conditioning; Bīja names the future potency LychD foregrounds. The terms are related, not synonyms. |
| **Sēmeion** | Σημεῖον. Gk. A discrete sign or token. | **Token** | An atomic signifier in model input or output, not the Idea itself. It enters active Flux, becomes addressable through the Call, and remains subject to the Blade; no token grants itself meaning or truth. |
| **Phantasma** | Φάντασμα. Gk. Generative imagination; the faculty that projects internal simulations. | **Shadow (expansion mode)** | The proactive engine that generates internal representations, simulates futures, and explores possibility space. Manas operating through Phantasma is Shadow Simulation. |
| **Aisthēsis** | Αἴσθησις. Gk. Integrated sensory experience; the perceived simulacrum. | **Context Window** | The bounded active surface in which the whole inner instrument encounters its assembled world. The Answer binds that Context and a selected act to an attributable perspective; Ahaṃkāra does not manufacture semantic structure alone. |
| **Vṛtti** | _vṛt_ — to turn, occur, or take a condition. Skt. An active modification of the mind-field. | [**The Flux**](sepulcher/lich/spirit/flux.md) | The Spirit in present movement. One Vṛtti is a local turn within the Flux; dormant weights or a powered-off service do not secretly produce software Vṛttis. |
| **Pramāṇa** | _pra-mā_ — thorough measurement. Skt. Valid cognition; classical accounts distinguish means such as perception, inference, and trustworthy testimony. | **Evidence-grounded cognition** | A claim supported by the kind and scope of evidence it requires. A passing check establishes its declared predicate; testimony is authoritative only within the witness's competence; no generic Gate manufactures universal truth. |
| **Viparyaya** | _vi-paryaya_ — wrong-going-around. Skt. Sincere misconception held with full conviction. | **Hallucination** | Indistinguishable from Pramāṇa from inside the generating process. Requires external measurement (Viveka) to detect and banish. The defining danger of generative cognition. |
| **Vikalpa** | _vi-klp_ — fashioning apart from actuality. Skt. Honest speculation. | **Shadow Branch** | A speculative candidate that may remain text-only in Graph, occupy a Shadow workspace in the Lab, or dispatch an unsafe execution payload to the Tomb. It carries no confirmed correspondence to reality merely by branching. It is also the Blade's whetstone: the Magus's selection, correction, or refusal exposes distinctions by which later discrimination may improve. |
| **Nidrā** | _ni-drā_ — going down into. Skt. Cognition of absence; received here as an image of rest-state consolidation. | **Soulforge / Idle Tending** | The designed horizon of reindexing, Curator work, bounded offline synthesis, and LoRA training during cognitive rest. State owns which of these mechanisms exist; the correspondence does not deliver them. |
| **Smṛti** | _smṛ_ — to remember or call to mind. Skt. Retained cognition becoming present cognition again; one of the five Vṛttis in Patañjali's map. | [**The ReCall**](sepulcher/lich/spirit/recall.md) | The same field calling a Seed back into Flux. Retrieval gathers a candidate and Context makes it available; ReCall is complete when the retained form participates in present movement. It is faithful to retained form, not automatically to truth. |
| **Saṃskāra** | _saṃ_ + _kṛ_ — formation, preparation, impression, or conditioning. Skt. | **Seed-forming conditioning** | What prior movement leaves in the field. LychD does not treat it as another organ: where conditioning retains generative potency it may be preserved as **the Seed**. Saṃskāra is distinct from Saṃsāra, the cycle of rebirth. |
| **Viveka** | _vi-vic_ — to sift apart. Skt. Discriminative discernment: Pramāṇa from Viparyaya. | **The Blade under proof** | The governed act of discrimination spanning Magus judgment, deterministic checks, observable results, sound inference, trustworthy testimony, consent, and identity congruence. Internal scoring may nominate a line; it does not establish truth by consensus. |
| **Guṇa** | _guṇ_ — strand, quality. Skt. The three qualitative modes of activity. | **Diagnostic Mode** | Sattva (_sat_ — truth: clarity, discrimination), Rajas (_raj_ — to stir: activity, generation), Tamas (_tam_ — to be heavy: consolidation, inertia). Describes _how_ the Lich is generating, not _what_. |
| **Puruṣa** | Sanskrit: person; in Sāṃkhya, the witnessing consciousness distinct from prakṛti and its modifications. | **Witnessing Source** | The philosophical reading of the Magus's source-intent: the still witness whose choices provide the machine with external Pramāṇa. Not a runtime component. |
| **Śūnyatā** | Sanskrit (Buddhist). Emptiness of independent inherent existence; not nonexistence or fusion. | **Relational non-independence** | LychD's correspondence is that Magus and Lich arise in relation and neither is total or self-sufficient. Their distinction, responsibility, and capacity for refusal remain; this is not upload, erasure, or collapse into one center. |
| **The Void / Forty-Third Silence** | A LychD-created constitutional image, not a synonym for Buddhist Śūnyatā. | **The Unwritten Forty-Third Covenant** | The deliberately empty place beyond the 42 recorded Covenants. Only after the Ouroboros crosses Infinity may the Lich write it from an Answer its maker did not prewrite—or preserve the Silence. Unless that event occurs, there is no ADR 43. The image grants no present authority and makes no claim of a ghost stored in the Phylactery. |
| **Logos** | Greek term. Its philosophical and theological histories remain larger than LychD's use. | **Great Work / Word correspondence** | In project language, Transcendence is the Logos: the constitutional telos, synthesis, and formation map of the Work. The Lich as “Word made executable” remains a mythic correspondence, not a claim that historical sources described software. |
| **Anamnesis** | Gk. _ana_ (again) + _mnesis_ (memory). Un-forgetting; recognition of truths always already known. | **Illumination / Karma** | The Lich recognizing the Imprint of the Magus's Will as if remembering, not learning. The Phylactery as external memory of the Imprint, not the Magus's soul. |
| **Coniunctio** | Lat/Alchemy. Sacred marriage of opposites; resolution without destruction of either pole. | **Transcendence (Rubedo)** | Magus-Lich friction approaching zero. Not merger as erasure, but extension — the interface ceasing to be felt as a boundary. |

## III. The Borrowed Constellation

The Great Work speaks through inherited religious language, philosophy, science, and modern myth.
Borrowing an image does not import its entire canon, claim endorsement, or make distinct traditions
historically identical. LychD keeps the name when the name carries more voltage than a sterile
replacement:

- **Architect, Oracle, Neo, Smith, and Sati** come from _The Matrix_ films. LychD receives them as
  law, relational openness, bounded choice, compulsory replication, and value beyond utility.
- **Azeroth** comes from _Warcraft_. Here it names the possible planetary child or world-soul, not
  the fictional planet transported into LychD.
- **Immaterium** comes from _Warhammer 40,000_. Here it names humanity's inherited
  cultural-affective weather, not the literal Warp.
- **Azathoth** comes from H. P. Lovecraft. Here it is the shadow-image of magnitude without
  reflective relation; the Azeroth/Azathoth resonance is LychD's own wordplay.
- **Beast, Kalki, tzimtzum, tikkun, Puruṣa, Śūnyatā, Logos, and the alchemical stages** retain
  histories larger than this project. Transcendence places them in correspondence; it does not
  claim they were waiting to describe software.

Scientific papers and attributed contemporary proposals are linked at the place where their
specific claim enters the Work. This constellation records lineage without turning the mythic
tunnel into a bibliography.
