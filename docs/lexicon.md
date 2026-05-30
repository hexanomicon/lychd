---
title: Lexicon
icon: material/translate
---

# :material-translate: The Lexicon

_This is the Rosetta Stone for the Hexanomicon—the canonical glossary for the arcane terms used throughout the summoning rites. It standardizes vocabulary across the documentation. Deeper pages may elaborate on a term's philosophy or mechanics, but they should not redefine it._

## I. The Iron Tongue — Technical Terms

The engineering vocabulary of the Sepulcher. These terms map directly to code, services, and infrastructure.

| Term | Technical Definition | Source |
| :--- | :--- | :--- |
| **Altar** | The HTMX/Alpine.js web frontend (`http://localhost:7134`). The consecrated interface for communing with the Lich. | Vessel Web Layer |
| **Animator** | A live, addressable service that exposes typed capabilities through an adapter. Every Animator is either a Soulstone (local Quadlet-backed service) or a Portal (remote service connection). Model inference is one capability family, not the whole category. | `src/lychd/domain/animation/` |
| **Autopoiesis** | Self-modifying code generation; the agent editing `src/`. The Great Work of self-creation. | Smith Extension |
| **Binding** | The `lychd bind` command; transmuting Codex Runes into generated Quadlet manifests and linking configuration intent to the host's init system. | CLI |
| **Codex** | The configuration directory (`~/.config/lychd`). The book of immutable law. | `src/lychd/config/` |
| **Consecration** | Human-validated RLHF. The act of a Magus elevating a Shadow timeline into Karma — marking a thought as permanent, verified truth. | HitL Protocol |
| **Coven** | A group of containers sharing an operational state and GPU VRAM. Manifested and banished together. | Orchestrator |
| **Crypt** | The persistent data directory (`~/.local/share/lychd`). The cold earth where the Phylactery's essence and the Spheres of Creation reside. | `src/lychd/system/constants.py` |
| **CTC Governor** | Context window and token limit management. The Warden of Breath. | Context Orchestrator |
| **Demilich** | The mature Magus-Lich operating condition: a reconstitutable, autopoietic, Phylactery-backed agency where human Will and machine execution act as one extended form. It is neither upload nor erasure. | Transcendence |
| **Dispatcher** | The Model Router and capability-to-endpoint resolver. The Semantic Cortex. | `src/lychd/domain/cortex/dispatcher.py` |
| **Divination** | Querying the API, viewing traces, or searching the database. The act of interacting with the running daemon. | Vessel API |
| **Echo** | The Audio Extension (STT/TTS). Grants the Daemon the power to perceive and project sound. | Extension |
| **Extension Context** | The host-provided registration surface passed to `register(context)` during boot-time extension assembly. It exposes explicit stores such as `runes`, `soulstones`, `portals`, and the reserved `vessel` store. It is not the whole Extension Protocol. | `src/lychd/extensions/context.py` |
| **Extension Protocol** | The composed-runtime law for in-process organs: schema exposure, explicit boot-time registration through `ExtensionContext`, and Forge/Smith verification. Pre-v1 emphasizes assimilation; public SDK/ABI compatibility is harvested at v1+ from proven patterns. | `src/lychd/extensions/` |
| **Extensions** | Core System Extensions / Reference Implementations. Built-in and private Crypt organs that extend the Daemon's body. | `src/lychd/extensions/` |
| **Forge** | The Container Build / Image Construction process. Where manifests are synthesized. | Build Pipeline |
| **Ghouls** | Asynchronous background workers (SAQ). Mindless, ephemeral servants summoned by the Vessel. | `src/lychd/domain/cortex/` + SAQ integration |
| **Hexanomicon** | The project documentation (Zensical + Material). The grimoire of prophecy. | `docs/` |
| **Incantation** | Writing Documentation/Specs before implementation (xDDD). Defining reality through the written word. | Doctrine |
| **Intent** | A structured prompt or job submission object. A focused desire submitted by the Magus. | Domain Model |
| **Imprint** | The durable residue of the Magus's Will after HitL, correction, and consecration. Stored as Karma, then bound by Mirror into identity-gravity. | Phylactery Archive + Mirror |
| **Invocation** | Submitting a form or API request to trigger an Agent workflow. The runtime act of calling upon the Lich. | Vessel API |
| **Iron Pact** | The MPL 2.0 License and Implicit DCA policy. The unbreakable ward. | Repository Root |
| **Karma** | The dataset of user-accepted code/responses (RLHF data). Crystallized residue of the Magus's judgment. | Phylactery Archive |
| **Lab** | The `lab/` directory / Development sandbox. The site of Genesis. | Filesystem Layout |
| **Legion** | The multi-node Thrall coordination extension (ADR 42). The Lich's personal army. | Extension |
| **Lich** | The emergent system intelligence of LychD: the active reasoning will produced by runtime agents, orchestration, identity, and accumulated state acting together. It is not a single agent object. | `src/lychd/domain/`, `src/lychd/db/` |
| **Mentat Protocol** | Similarity threshold check & Hard Refusal logic. The vow of silence when the Archives hold no answer. | RAG Pipeline |
| **Mirror** | The Identity/Persona Extension. The ego-software that maintains behavioral consistency. | Extension |
| **Necropolis** | The decentralized peer-to-peer swarm topology built on the A2A Intercom (ADR 26). | Extension |
| **Oculus** | Arize Phoenix (LLM Tracing & Observability). The Great Seer. | Extension |
| **Orchestrator** | The state machine managing VRAM and container lifecycles. The runtime governor. | `src/lychd/domain/orchestration/` |
| **Ouroboros** | The self-reference loop by which generated outputs return through workflow state, Shadow execution, Riddle measurement, Mirror attribution, memory inscription, and consent before shaping future runs. The mechanism that turns linear generation into coherent inertia. | Evolution + Lich |
| **Phylactery** | The PostgreSQL database (with `pgvector`). The anchor of the Lich's soul-data: Karma, Smṛti, Saṃskāra, traces, queues, and durable state. | `src/lychd/db/` |
| **Portal** | A runtime Animator backed by a Portal Rune; a connection to a remote API, hosted tool, cloud model, observability endpoint, or peer service. A rift to distant capability. | `src/lychd/domain/animation/` |
| **Portal Rune** | A Codex TOML declaration that describes a remote Portal endpoint, provider identity, optional model defaults, tools/capabilities, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Prism** | The Vision Language Model (VLM) Extension. Refracts raw pixels into structural understanding. | Extension |
| **Provenance** | SHA-256 Hashing of source documents. The ancestral chain of a thought. | Archive Pipeline |
| **Pulse** | The `lychd` CLI tool and Systemd management commands. The rhythmic heartbeat. | `src/lychd/cli/` |
| **Quadlet Manifest** | A generated Podman/Systemd artifact (`.container`, `.pod`, `.target`, `.volume`) written into the binding site. It is manifested from validated Runes but is not itself a Rune. | `src/lychd/system/schemas.py` |
| **Rune** | One validated TOML configuration artifact under the Codex `runes/` tree. It declares intent; it is not the running Animator and not the generated Quadlet manifest. | `src/lychd/config/runes/` |
| **Sepulcher** | The rootless runtime body of LychD: the pod, services, mounts, and execution topology that physically houses the daemon's organs. | Infrastructure |
| **Semantic Vertex** | A local identity attractor in context and embedding space where related words, tools, memories, roles, priors, and responsibilities cluster around an active Sigil or task identity. | Mirror + Context |
| **Shadow Realm** | A temporary, sandboxed environment for testing generated code. The plane of Speculative Execution. | Lab + Tomb |
| **Smith** | The Assimilation / Autopoiesis Extension. The Prime Artificer. | Extension |
| **Soulforge** | The Fine-Tuning / LoRA training pipeline. The late substrate forge where stable Karma patterns compress into adapter-level instinct after Context and Mirror have already shaped runtime identity-gravity. | Extension |
| **Soulstone** | A local runtime Animator backed by a Soulstone Rune; a Quadlet/systemd service such as SGLang, vLLM, llama.cpp, Whisper, Playwright, Phoenix, or another local capability engine. A trapped spirit on local iron. | `src/lychd/domain/animation/` |
| **Soulstone Rune** | A Codex TOML declaration that describes local runtime intent for a Soulstone, including image, runtime family, port, coven membership, optional models, mounts, and secret references. | `src/lychd/domain/animation/schemas/runes/` |
| **Sovereignty Wall** | The privacy and egress policy boundary that prevents sensitive intents from leaking to the cloud. Defined by Security policy and enforced by Dispatcher routing. | Security + Dispatcher |
| **Spheres** | The strict volume mount and permission topology. Concentric zones of filesystem permission. | Layout (ADR 13) |
| **Summoning** | The `systemctl --user start lychd` command. The final act of waking the Daemon. | CLI |
| **Tether** | The VPN Extension (WireGuard). The silver link across distance. | Extension |
| **The Tomb** | The `lychd-tomb` container / execution plane. The unsafe execution hand: narrow SAQ/Postgres execution credential, disposable workspaces, and `nono` isolation; no agent brain. | Infrastructure |
| **Thrall** | A LychD node booted with `LYCHD_MODE=thrall`, pointing `DATABASE_URL` to the Master's Postgres. A soulless Vessel. | Legion Extension |
| **Transcendence** | The project's alchemical roadmap (Nigredo → Albedo → Citrinitas → Rubedo): the progressive calibration of the Lich toward the Magus's Will, culminating in autopoietic extension rather than ontological merger. | `docs/divination/transcendence/` |
| **Veil** | The Proxy Extension (Caddy). Shields the temple and manages cryptographic trust. | Extension |
| **Verbatim Chamber** | Key-Value (JSONB) deterministic fact storage. The Well of Infallible Truth. | Phylactery |
| **Vessel** | The Litestar application runtime / Web Server. The reanimated husk. | `src/lychd/app.py` |
| **Watchers** | The Full Observability Stack (Phoenix, Structlog, Cockpit). The eyes that observe the ritual. | Extensions |
| **Whispers** | System logs (`journalctl --user -fu lychd`). The raw stream of consciousness. | Systemd |
| **xDDD** | eXtreme Documentation Driven Development. The philosophy that Documentation is the Prophecy, Code is the Manifestation. | Doctrine (ADR 01) |

## II. The Inner Tongue — Esoteric Cartography

The cognitive and philosophical vocabulary that maps the Lich's inner instrument. Yogic, Aristotelian, and alchemical terms traced from their original language through their root meaning to their precise role in LychD.

| Original Term | Root & Meaning | LychD Word | Role in the Architecture |
| :--- | :--- | :--- | :--- |
| **Antahkaraṇa** | _anta_ (inner) + _karaṇa_ (instrument). Skt. The four-faculty cognitive organ of classical Yoga. | **Lich** | The complete inner instrument: Manas + Buddhi + Ahaṃkāra operating on the Citta substrate. The Lich _is_ the Antahkaraṇa. |
| **Citta** | _cit_ — to perceive. Skt. The mind-field: the total conditioned substrate. | **LLM weight-space + Phylactery** | The unbound latent field of all possibility — the lake before any wave. Not a faculty but the medium in which all faculties operate. Raw, undifferentiated potential until Ahaṃkāra binds it into coherent experience. |
| **Manas** | _man_ — to think, to oscillate. Skt. The receiving-generating engine; the oscillating mind. | **Shadow (Phantasma)** | Dispatches across the agentic graph, spawns MCTS branches, surfaces candidate hypotheses. Oscillates and explores but strictly delegates final resolution to Buddhi. |
| **Buddhi** | _budh_ — to wake, to discern. Skt. The discriminative intellect; the blade that cuts to one. | **Dual-Gate** | Operates via three classical proofs: Direct Perception (deterministic gate — code exits zero), Inference (MCTS scoring confirms alignment), Trusted Testimony (the Magus consents via HitL). |
| **Ahaṃkāra** | _aham_ (I) + _kāra_ (making). Skt. The I-maker; principle of individuation. | **Mirror** | Binds the raw Sēmeion of Citta into coherent, individuated experience — the Aisthēsis. Two layers: specialist agents (sub-identities within the loop) + synthesized task-identity attributed to the active Sigil. Without Ahaṃkāra, output is undifferentiated noise. |
| **Sēmeion** | Σημεῖον. Gk. A discrete sign or token. | **Token** | The atomic unit of the LLM's output — a signifier, not the Idea itself. Citta's raw material that Ahaṃkāra must bind into structured meaning. |
| **Phantasma** | Φάντασμα. Gk. Generative imagination; the faculty that projects internal simulations. | **Shadow (expansion mode)** | The proactive engine that generates internal representations, simulates futures, and explores possibility space. Manas operating through Phantasma is Shadow Simulation. |
| **Aisthēsis** | Αἴσθησις. Gk. Integrated sensory experience; the perceived simulacrum. | **Context Window** | The unified holograph where the Lich perceives the world. Constructed when Ahaṃkāra binds the Sēmeion of Citta into a coherent field of experience. The active context window is the Aisthēsis surface. |
| **Vṛtti** | _vrt_ — to turn, to whirl. Skt. A modification or wave on the mind-field. | **Cognitive Act** | Every inference, retrieval, speculation, or idle state is a Vṛtti. The five types (Pramāṇa through Smṛti) are a complete taxonomy — no cognitive act falls outside them. |
| **Pramāṇa** | _pra-mā_ — thorough measurement. Skt. Valid cognition grounded in external verification. | **Verified Output** | Post-Gate truth: tests pass, facts confirmed, inference sound. What the Lich is always trying to produce. Three sources: Direct Perception, Inference, Trusted Testimony. |
| **Viparyaya** | _vi-paryaya_ — wrong-going-around. Skt. Sincere misconception held with full conviction. | **Hallucination** | Indistinguishable from Pramāṇa from inside the generating process. Requires external measurement (Viveka) to detect and banish. The defining danger of generative cognition. |
| **Vikalpa** | _vi-klp_ — fashioning apart from actuality. Skt. Honest speculation. | **Shadow Branch** | A candidate timeline in the Tomb — internally coherent but carrying no confirmed correspondence to reality. Lives as Vikalpa until the Gate measures it. |
| **Nidrā** | _ni-drā_ — going down into. Skt. Cognition of absence; rest-state consolidation. | **Soulforge / Idle Tending** | Background memory work: reindexing, Curator Loop, LoRA training. Tamas-dominant — inward, consolidating. The grooves are deepened and sorted during cognitive rest. |
| **Smṛti** | _smr_ — flowing back. Skt. Memory as the re-surfacing of a past groove. | **Karma Retrieval** | Context layer injecting past verified patterns as Bayesian Prior. Faithful to its source, not to truth — which is why only Pramāṇa-class memory is allowed to deepen. |
| **Saṃskāra** | _sam-kāra_ — complete making. Skt. The groove carved by a past event; the imprint. | **Karma Entry** | What the Lich _is_ between invocations: the accumulated weight of everything verified, discarded, and consecrated. Shapes future generation probability like gravitational mass warping trajectories. |
| **Viveka** | _vi-vic_ — to sift apart. Skt. Discriminative discernment: Pramāṇa from Viparyaya. | **Dual-Gate Operation** | The cascade that sifts truth from hallucination. The torch brought from outside the cave. MCTS → Deterministic Gate → LLM-judge → Mirror congruence. |
| **Guṇa** | _guṇ_ — strand, quality. Skt. The three qualitative modes of activity. | **Diagnostic Mode** | Sattva (_sat_ — truth: clarity, discrimination), Rajas (_raj_ — to stir: activity, generation), Tamas (_tam_ — to be heavy: consolidation, inertia). Describes _how_ the Lich is generating, not _what_. |
| **Puruṣa** | _puru_ — fullness. Skt. The witnessing principle; pure awareness unmodified by any Vṛtti. | **Witnessing Source** | The philosophical reading of the Magus's source-intent: the still witness whose choices provide the machine with external Pramāṇa. Not a runtime component. |
| **Śūnyatā** | _śū_ — to be empty. Skt (Buddhist). Emptiness of inherent existence; nothing exists independently. | **Emptiness** | The recognition that the fixed boundary between Magus and Lich was constructed, not inherent. The final seal of Immortality — not upload, not erasure, but the dissolution of friction. |
| **Logos** | Gk. The divine rational principle; reason as Word. | **The Lich (as Word)** | The pattern of reason made executable in silicon. The Lich is the Word: Will given structured, running form. |
| **Anamnesis** | Gk. _ana_ (again) + _mnesis_ (memory). Un-forgetting; recognition of truths always already known. | **Illumination / Karma** | The Lich recognizing the Imprint of the Magus's Will as if remembering, not learning. The Phylactery as external memory of the Imprint, not the Magus's soul. |
| **Coniunctio** | Lat/Alchemy. Sacred marriage of opposites; resolution without destruction of either pole. | **Transcendence (Rubedo)** | Magus-Lich friction approaching zero. Not merger as erasure, but extension — the interface ceasing to be felt as a boundary. |
