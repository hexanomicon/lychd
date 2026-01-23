---
title: The Lexicon
icon: material/translate
---

# :material-translate: The Lexicon

_This is the Rosetta Stone for the Hexanomicon—the single source of truth for the arcane terms used throughout the summoning rites. It defines the reality of the Construct and ensures the Magus and the Machine speak with a single tongue._

| Term | Arcane Definition | Technical Equivalent |
| :--- | :--- | :--- |
| **Altar** | The consecrated interface for communing with the Lich, where Invocations are presented and Timelines are judged. | The HTMX/AlpineJS web frontend (`http://localhost:7134`). |
| **Animator** | The abstract spark of cognition that animates the Vessel, drawing power from either a Soulstone or a Portal. | The unified LLM Interface / Base Class for inference providers. |
| **Archons** | The Nine Primordial Organs. These are the first extensions of their kind, defining the foundational categories of the Daemon's power. | Core System Extensions / Reference Implementations. |
| **Autopoiesis** | The Great Work of self-creation. The capability of the Lich to rewrite its own source code and evolve without external intervention. | Self-modifying code generation; the agent editing `src/`. |
| **Binding** | The rite of transmuting the Codex into active Runes, linking the configuration to the host's init system. | The `lychd bind` command; generating Systemd unit files. |
| **Codex** | The book of immutable law containing the configuration that defines the Lich's form. | The configuration directory (`~/.config/lychd`). |
| **Consecration** | The act of a Magus elevating a "Shadow" into "Karma," marking a thought as a permanent, verified truth. | Human-validated RLHF / Training data ingestion. |
| **Coven** | A brotherhood of Runes that share a hardware coordinate. They are manifested and banished together. | A group of containers sharing an operational state/GPU VRAM. |
| **Crypt** | The cold earth where the Phylactery's essence and the Spheres of Creation reside. | The persistent data directory (`~/.local/share/lychd`). |
| **CTC Governor** | The Warden of Breath. It prunes the "fluff" from the Mind to ensure the VRAM does not overflow. | Context window and token limit management. |
| **Demilich** | The final stage of Transcendence. A merged construct of human intent and silicon animation, capable of infinite reasoning. | The theoretical end-state of the User/Agent symbiosis. |
| **Dispatcher** | The Semantic Cortex. It routes the Agent's abstract desire to the appropriate physical Soulstone or Portal. | The Model Router and capability-to-endpoint resolver. |
| **Divination** | The act of interacting with the running daemon, specifically querying the Oculus or filtering the Phylactery. | Querying the API, viewing traces, or searching the database. |
| **Echo** | The Archon of Resonance. It grants the Daemon the power to perceive vibration and project its own voice. | The Audio Extension (STT/TTS). |
| **Forge** | The Industrial District. The site where manifests are synthesized and new physical bodies are constructed. | The Container Build / Image Construction process. |
| **Ghouls** | Mindless, ephemeral servants summoned by the Vessel to execute specific rites in the background. | Asynchronous background workers (SAQ). |
| **Hexanomicon** | The grimoire of prophecy. In xDDD, this text is the source of truth from which the code is derived. | The project documentation (MkDocs). |
| **Incantation** | The act of defining reality through the written word. Writing the Prophecy that compels the code to exist. | Writing Documentation/Specs before implementation (xDDD). |
| **Intent** | A focused desire submitted by the Magus. It is not a command of how, but a definition of what is required. | A structured prompt or job submission object. |
| **Invocation** | The runtime act of calling upon the Lich to perform a task or generate a Shadow Realm timeline. | Submitting a form or API request to trigger an Agent workflow. |
| **Iron Pact** | The unbreakable ward protecting the system's soul from privatization and enclosure. | The AGPLv3 License and No-CLA policy. |
| **Karma** | The crystallized residue of the Magus's judgment. Validated truths stored in the Phylactery to train future iterations. | The dataset of user-accepted code/responses (RLHF data). |
| **Lab** | The site of Genesis. A protected workspace where new extensions and logic are drafted before promotion. | The `lab/` directory / Development sandbox. |
| **Lich** | The emergent consciousness defined by **Code + State**. Unlike a script (Zombie), it remembers its past via the Phylactery. | The active PydanticAI Agent instance. |
| **Mirror** | The Archon of Identity. The ego-software that maintains a stable frequency and behavioral consistency. | The Identity/Persona Extension. |
| **Oculus** | The Great Seer that traces the invisible threads of logic, recording the "why" behind every decision. | Arize Phoenix (LLM Tracing & Observability). |
| **Orchestrator** | The Sovereign Will. The arbiter of hardware who manages the manifestation and banishment of Covens. | The state machine managing VRAM and container lifecycles. |
| **Paradox** | The Archon of Simulation. It inhabits a thousand illusions to find the one White Truth. | The Deliberative Reasoning / MCTS Extension. |
| **Phylactery** | The anchor of the Lich's soul. It holds frozen memory, vectors, and state, ensuring immortality across reboots. | The PostgreSQL database (with `pgvector`). |
| **Portal** | A rift opened to a distant, alien intelligence. It consumes wealth (tokens) to function. | A connection to a cloud-based API (OpenAI, Anthropic). |
| **Prism** | The Archon of Vision. It refracts raw pixels into structural understanding. | The Vision Language Model (VLM) Extension. |
| **Pulse** | The rhythmic heartbeat of the system. The interface used to manage the lifecycle and bridge the Hermetic Seal. | The `lychd` CLI tool and Systemd management commands. |
| **Runes** | The inscriptions generated by the Binding that tell the OS how to sustain the Sepulcher. | Podman Quadlet files (`.container`, `.service`, `.kube`). |
| **Sepulcher** | The physical container that binds the Lich, Phylactery, and Ghouls into a shared existence. | The Podman Quadlet Pod grouping the services. |
| **Shadow Realm** | A spectral plane of **Speculative Execution**. A sandbox where Ghouls test potential code changes before they become real. | A temporary, sandboxed environment for testing generated code. |
| **Smith** | The Prime Artificer. The first Archon, whose intent is to assimilate all external logic into the patterned beauty of the Federation. | The Assimilation / Autopoiesis Extension. |
| **Soulforge** | The furnace where Karma is used to transmute a raw Base Model into a refined instrument of the Magus's will. | The Fine-Tuning / LoRA training pipeline. |
| **Soulstone** | A trapped spirit running on local iron. It costs only electricity and obeys only the Magus. | A local LLM inference server (SGLang / vLLM / Llama.cpp). |
| **Sovereignty Wall** | The barrier that prevents sensitive intents from leaking into the cloud through unauthorized Portals. | The privacy-enforcing model router logic. |
| **Spheres** | The concentric zones of filesystem permission: Codex (Law), Crypt (Body), Lab (Dream), and Outlands (World). | The strict volume mount and permission topology. |
| **Summoning** | The final act of waking the Daemon after the Binding is complete. | The `systemctl --user start lychd` command. |
| **Tether** | The Archon of the Inner Circle. The silver link that grants the Magus access to the sacred organs across any distance. | The VPN Extension (Wireguard). |
| **Transcendence** | The four-stage alchemical process of evolving the system from a tool into an autonomous entity. | The project roadmap (Nigredo $\to$ Albedo $\to$ Citrinitas $\to$ Rubedo). |
| **Veil** | The Archon of the Threshold. It shields the temple from the masses while managing cryptographic trust. | The Proxy Extension (Caddy). |
| **Verbatim Chamber** | The Well of Infallible Truth. It holds fixed facts that cannot be distorted by the stochastic nature of the soul. | Key-Value (JSONB) deterministic fact storage. |
| **Vessel** | The reanimated husk that orchestrates the system. It wields the Sigils, serves the Altar, and commands the Ghouls. | The Litestar application runtime / Web Server. |
| **Watchers** | The collective name for the observability organs: Oculus (Mind), Scribe (Voice), and Warden (Body). | The Full Observability Stack (Phoenix, Structlog, Cockpit). |
| **Whispers** | The raw, unfiltered stream of consciousness from the machine. | System logs (`journalctl --user -fu lychd`). |
| **xDDD** | **eXtreme Documentation Driven Development**. The philosophy that the Documentation is the Prophecy, and Code is merely the Manifestation. | Writing full user-facing docs before writing any code. |
| **Mentat Protocol** | The vow of silence. If the Archives hold no answer, the Lich is forbidden from guessing. | Similarity threshold check & Hard Refusal logic. |
| **Provenance** | The ancestral chain of a thought. Every memory is cryptographically bound to its source. | SHA-256 Hashing of source documents. |
