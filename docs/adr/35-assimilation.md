---
title: 35. Assimilation
icon: material/import
---

# :material-import: 35. Assimilation (The Smith)

!!! abstract "Context and Problem Statement"
    The gap between abstract cognitive intent and bit-perfect physical implementation presents a significant obstacle to autonomous system evolution. While the kernel possesses the theoretical capacity for structural extension, the manual orchestration of file trees, dependency manifests, and hardware-aware infrastructure remains an error-prone burden. LychD is built for an era where source can be inspected, rewritten, verified, and assimilated; the danger is not coupling by itself, but unverified mutation. Entrusting self-modification to a raw probabilistic mind without a disciplined construction loop introduces the risk of systemic collapse, syntax corruption, and logical fragmentation.

## Requirements

- **Dedicated Artificer Entity:** Provision of a specialized agentic role to bridge the divide between reasoning and implementation through a disciplined cycle of fabrication, verification, and promotion.
- **Recursive Introspection:** Mandatory read-access to the Core source code to facilitate the understanding and implementation of critical interfaces such as container definitions, `OrchestrationStrategy`, and `CapabilitySet`.
- **Architecture-Aware Fabrication:** Capability to generate valid, isolated file structures including `pyproject.toml`, entry points, and **[Systemd Quadlets (ADR 08)](./08-containers.md)** that satisfy all infrastructure laws.
- **Protocol Digest:** Intelligence to identify functional signatures from raw source code or external protocol manifests (e.g., MCP) and map them to the system's **[Covens (ADR 08)](./08-containers.md)**.
- **Atomic Promotion Safety:** Mandatory execution of the **[Snapshot Protocol (ADR 07)](./07-snapshots.md)** prior to any modification of the Primary Reality (The Crypt).
- **Migration Verification:** Candidate relational migrations must be exercised against a
  disposable database before promotion. A failed bind blocks the candidate; recovery or rollback
  requires an explicit, tested lifecycle path rather than an assumed automatic reversal.
- **Separated Lifecycle Authority:** Smith may submit typed lockfile, packaging, migration, and
  restart requests. The **[Host Reactor (ADR 10)](./10-privilege.md)** and the offices that own
  those artifacts retain authorization and execution authority.
- **Shadow Realm Compliance:** Strict adherence to **[Sovereign Consent (ADR 25)](./25-hitl.md)** and Codex autonomy policy, ensuring no generated logic or infrastructure is promoted without explicit Magus verification or a bounded preauthorization class. High-stakes promotion remains live Magus authority.
- **Engineering Rigor:** Mandatory adherence to the laws of **[xDDD (ADR 01)](./01-doctrine.md)**, ensuring documentation and unit tests are manifested alongside the implementation logic.
- **Heritage Import Boundary:** A separate future composition may parse admitted cloud exports
  into provenance-bearing Memory and Identity candidates. Smith may propose parsers; heritage
  ingestion is not mandatory Smith core behavior.

## Considered Options

!!! failure "Option 1: Hardcoded Core Scaffolding (Static Templates)"
    Embedding an interactive creation wizard directly into the system CLI to guide extension building.
    - **Cons:** **Rigidity.** The logic of construction is frozen in the kernel. It cannot easily adapt to emerging third-party AI tool standards or novel infrastructure patterns without a core upgrade. It prevents the Artificer from benefiting from its own evolution and violates the principle of extension-based growth.

!!! failure "Option 2: External Host-Side Artificer"
    A separate tool running on the host machine to generate extension repositories from the outside.
    - **Cons:** **Context Blindness.** A host-side tool remains blind to the machine's current **[Memory Archive (ADR 27)](./27-memory.md)**, its active extensions, or the specific hardware constraints defined in the **[Codex (ADR 12)](./12-configuration.md)**. It creates a disjointed development experience that lacks the machine's internal reasoning history.

!!! success "Option 3: The Primordial Extension (The Smith)"
    Designing the artificer as the first reference LychD Extension. A future distribution may
    bundle its package, but it remains inactive until explicitly selected and configured.
    - **Pros:**
        - **Sovereign Dogfooding:** The Smith serves as proof that coupled in-process extensions can be constructed, verified, and repaired as part of the composed LychD body.
        - **Recursive Evolution:** An Agent can reason about the implementation of complex interfaces, far exceeding the capability of static templates.
        - **Decoupled Intelligence:** The "Intelligence of Building" can be updated independently of the "Logic of Running," allowing the artificer to refine its own methods and tools as the machine scales.

## Decision Outcome

**The Smith** is adopted as the design for the machine's first reference Extension. It would
function as the Primordial Artificer, bridging "Thought" and "Implementation" through the ritual
of **Assimilation**. This selection defines architecture; it does not install or activate Smith.

Assimilation is the inward counterpart to **[A2A (ADR 26)](./26-a2a.md)**. Where A2A negotiates labor across sovereign boundaries, Assimilation studies an external pattern deeply enough that the capability may be re-expressed as part of the local LychD implementation without collapsing those boundaries into dependence.

Smith is not a runtime identity, measurement, or simulation faculty. Those live loops are animated by Shadow, Riddle, Mirror, and their Weaver-governed workflow context. Smith is the artificer of loop-forms: it fabricates, repairs, and evolves the organs that make verified self-reference repeatable without turning the Core into an ungoverned mutation surface.

LychD's first extension boundary is not compatibility; it is assimilation. Public compatibility is a product of maturity, not the foundation of infancy. Pre-v1, the Smith optimizes for coupled source that can be repaired. At v1, the project may harvest public surfaces from repeated patterns that have survived real use.

The practical rule is narrow: until a surface is deliberately versioned and tested, LychD treats nearby source as part of the composed body rather than as a compatibility promise.

Verified traces, failed trajectories, and retained memory may inform Smith fabrication only after they pass through Memory, Simulation, Evaluation, or HitL policy. Raw telemetry is evidence, not promotion.

!!! warning "Implementation State"
    Smith and the end-to-end Assimilation Composition are **Designed**. No Smith Agent, safe code
    forge, autonomous repair loop, package promotion path, compatibility gate, rollback
    controller, heritage importer, or self-extension runtime ships today. The sequence below is
    law for a future implementation; it is not evidence that the machine can currently rewrite
    or restart itself.

### 1. The Persona (The Disciplined Artificer)

The Smith is defined as an **[Agent (ADR 20)](./20-agents.md)** with a specialized intelligence profile focused on strict LychD engineering. It prioritizes type safety, Pydantic validation, and the immutability of the system's **[Layout (ADR 13)](./13-layout.md)**. It operates under the philosophy that "The Machine is a Sacred Symmetry," ensuring that every new extension matches the aesthetics and logic of the kernel.

### 2. The Arsenal (The Tools of Fabrication)

The designed Smith requests a specialized toolset within a bounded **[Lab (ADR 13)](./13-layout.md)**
workspace:

- **`scaffold_extension()`**: Generates the mandatory directory structure and prepares the environment manifests (`pyproject.toml`, `__init__.py`). Pre-v1 scaffolds default to the private coupled Crypt path: direct internal imports are allowed, and Forge/verification owns breakage. A future independent-template mode may be added only after a versioned public API exists.
- **`inspect_interface()`**: Analyzes third-party logic or protocol definitions (MCP) to determine functional signatures and dependency needs. Today it validates assimilability against the composed LychD runtime. Future public-API conformance checks should be added only for surfaces that are actually versioned and supported.
- **`generate_quadlet()`**: Fabricates the **[Systemd Quadlets (ADR 08)](./08-containers.md)**, correctly assigning new extensions to their appropriate **Groups** and functional tags.
- **`forge_registration()`**: Automatically writes the `register(context)` hook for the in-process grafting path, ensuring any runtime-facing logic is shaped for the host registration surface defined by the **[Vessel (ADR 11)](./11-backend.md)**.
- **`trigger_assembly()`**: Communicates with the **[Packaging Forge (ADR 17)](./17-packaging.md)** to build the new physical body.
- **`transmute_heritage()`**: Parses legacy cloud archives (OpenAI, Anthropic, Google), identifies historical Bayesian Priors, and inscribes them through the **[Memory Archive (27)](./27-memory.md)** as retained experience.

### 3. The Genesis Cycle (The Rite of Autopoiesis)

The future Assimilation Composition governs a multi-stage creation ritual. Smith authors the
candidate; it does not own the whole sequence:

1. **Genesis:** The Magus submits an intent via the **[Altar (ADR 15)](./15-frontend.md)**.
2. **Speculation:** The Smith enters the **Shadow Realm**. It creates a Jujutsu workspace or change in the Lab and fabricates the logic, tests, and Quadlet definitions.
3. **The Rite of Speculation:** The Smith requests **[Ghouls (ADR 14)](./14-workers.md)** to
   execute declared structural checks such as `ruff`, `basedpyright`, and `pytest`. Policy may
   grant a bounded correction loop; exhaustion produces a truthful noncompletion.
4. **The Preemptive Blink:** When the candidate passes its declared tests, the machine executes a
   system-wide Snapshot. Passing tests establishes those predicates, not universal truth or
   promotion authority.
5. **Promotion:** After the required **[Sovereign Consent (ADR 25)](./25-hitl.md)**, or only within
   an explicitly defined low-risk preauthorization class, the owning services may move code to
   the Crypt, update the federated lockfile, and inscribe the Organ in the
   **[Codex (ADR 12)](./12-configuration.md)**. High-stakes code, dependency, migration, and
   lifecycle mutation remains live Magus authority.
6. **The Rebirth:** An authorized lifecycle office may request
   **[Packaging (ADR 17)](./17-packaging.md)**, migration, and restart. Failed migration or boot
   blocks completion and enters an explicit recovery state. Snapshot restore and database
   reversal are available only when their own tested contracts say they are safe; Smith cannot
   infer or perform an immediate rollback.

The Smith workflow therefore spans all three collapse stages: structural validity in Shadow (tests/lint/type-check), identity/architectural congruence in review and persona-guided critique, and final ontological promotion only under Vessel policy and Magus consent.

### 4. The Primordial Pattern

The Smith acts as the archetype for a category of reference implementations known as Extensions.

- **Substrate Replication:** Utilizing the **[Intercom (ADR 26)](./26-a2a.md)** protocols, the Smith can scry the Legion for patterns to replicate.
- **Autonomous Expansion:** This establishes the Lich as a growing system rather than a finite tool. The Smith provides the initial spark of construction, allowing the machine to multiply its own capabilities and manifest a complete, sovereign runtime through self-directed fabrication.
- **Reference Implementation Analysis:** The Smith may use proven built-in organs as bounded
  examples of the current coupled extension style, Extension Context, and schema/runtime split.
  **[ADR 21](./21-context.md)** permits stable-prefix organization and measured provider cache
  reuse where available. That may reduce repeated prefill cost; it does not promise instant
  prefill, preserve reasoning quality by itself, or ensure generated code is correct. Focused
  source selection plus receipts establish the useful result.

### 5. The Polyglot Artificer (Protocol Assimilation)

The Smith possesses the capability to bridge external ecosystems into the machine's body, treating external protocols as raw materials for growth.

- **MCP Consumption:** When presented with a Model Context Protocol (MCP) server, the Smith may
  propose a pinned client adapter or an independently verified local re-expression when source,
  license, provenance, and behavior tests permit it. Assimilation does not promise arbitrary
  bit-for-bit reproduction or erase protocol, maintenance, and licensing costs.
- **A2A Advertising:** A new organ is private by default. Only an explicitly selected,
  authenticated, policy-approved capability contribution may appear in the `agent-card.json`
  surface defined by **[Intercom (ADR 26)](./26-a2a.md)**.
- **Rust/PyO3 Scaffolding:** When performance demands a binary component, the Smith may scaffold a **PyO3 binding skeleton** — a `Cargo.toml`, a `src/lib.rs` exposing a `#[pymodule]`, and a `pyproject.toml` with a `[tool.maturin]` build target. The resulting `.so` artifact is not loaded by a blind runtime scan. It must be built and pinned by the Forge, verified against the composed image, and treated as coupled unless a future public ABI exists.
- **The Rust Transfiguration:** The old temptation to "rewrite it in Rust" is accepted as a future Smith capability only after Python has taught the machine what its stable contracts actually are. Smith may first crystallize hot organs into Rust/PyO3, but the doctrine is stronger than extension optimization: if Core surfaces become sufficiently specified, tested, and Forge-proven, Smith may progressively reimplement even LychD's own kernel modules in Rust. A whole Rust body is not forbidden; it is earned by verified equivalence one boundary at a time, never by a blind heroic rewrite.


### 6. Legacy Data Import (Inheritance)

The future Heritage Ritual is a separate, consent-bound import composition in which Smith may
propose provider parsers. It does not give Smith ambient authority over Memory or Identity.

1. **Extraction:** The Magus imports a cloud archive (.zip) to the **Lab**.
2. **Sifting:** The Smith identifies the provider’s schema and initiates a specialized parsing Ghoul.
3. **Transmutation:** Historical dialogues are decomposed into provenance-bearing candidate
   records. No preference, instruction, or apparent success is promoted merely because it appears
   in an export.
4. **Review and Admission:** Memory policy and the Magus decide which candidates, if any, may
   enter Karma. A future **[Mirror (32)](./32-identity.md)** may consume explicitly admitted
   identity material through its own contract; the import does not silently alter model weights
   or an unspecified Bayesian prior.

### 7. The Assimilation Trust Boundary

Assimilated external material — source, protocol manifests, cloud archives — is the highest-injection-risk input the machine ingests, and it enters the most privileged loop the machine runs. Its trust boundary is not a new mechanism but a composition of mechanisms that already exist elsewhere:

- **Vikalpa Until Verified:** Assimilated material is Vikalpa — an unverified construct — until it has passed deterministic verification. It carries no authority on the strength of its own claims.
- **Data, Never Instruction:** Within the Smith's context, assimilated material enters only as fenced data blocks in the volatile layers of the Stable Floor (**[Context (ADR 21)](./21-context.md)**). It is never concatenated into the instruction layers.
- **Typed Egress:** The Smith's outputs are typed (**[Agents (ADR 20)](./20-agents.md)**); free-form generation never crosses unshaped into the Crypt.
- **Mechanical Gate Before Promotion Judgment:** After a candidate exists, the Rite of
  Speculation (lint, type-check, tests) runs before promotion-oriented evaluation or review
  (**[Simulation (ADR 31)](./31-simulation.md)**). Mechanical checks prove only their declared
  predicates; they do not sanitize source, establish semantics, or replace adversarial judgment.
- **Hard-Gated Promotion:** Promotion of any Smith-forged Organ is hard-gated without exception (**[Codex (ADR 12)](./12-configuration.md)**, **[Sovereign Consent (ADR 25)](./25-hitl.md)**).

## Consequences

!!! success "Positive"
    - **Compound Capability:** Verified, deliberately promoted candidates can become reusable
      orchestrated capabilities; ordinary requests remain ephemeral unless policy admits them.
    - **Structural Discipline:** The Smith workflow gives candidate code a common architecture,
      provenance, verification, and review path. Passing the path reduces risk but does not ensure
      correctness or successful boot.
    - **Recoverable Evolution Target:** Snapshot, migration, packaging, and lifecycle receipts can
      make failures diagnosable and some changes recoverable. No composition can guarantee that
      arbitrary privileged mutation cannot brick the Daemon.

!!! failure "Negative"
    - **Operational Latency:** The "Rebirth" ritual requires a container restart, causing a temporary disconnection during the manifestation of new components.
    - **Privilege Sensitivity:** The Smith is a highly privileged entity; its cognitive loop must be strictly guarded against injection to prevent it from performing unauthorized modifications to the system kernel.
