---
title: 17. Packaging
icon: material/package-variant-closed
---

# :material-package-variant-closed: 17. Packaging

!!! abstract "Context and Problem Statement"
    The capability for autonomous evolution creates a fundamental substrate dilemma. A Lich is a composite organism, its physical body formed by merging disparate manifests (Python, Node, System) and infrastructure intents (Systemd Quadlets) into a single, cohesive runtime. Standard imperative container build cycles suffer from "Substrate Drift"—where external repository shifts or re-tagged base images cause the same source code to produce different binary artifacts over time. In the agentic era, the substrate must also preserve enough inspectable source for the Smith to repair coupled organs instead of freezing a premature extension ABI. A mechanism is required to resolve dependency conflicts and forge a new body for the Daemon that is both mathematically deterministic and synchronized with the machine's physical state.

## Requirements

- **Multi-Manifest Synthesis:** Discovery and merging of `pyproject.toml` (Python) and
  `package.json` (Node) from all active extensions into a single build context.
- **Infrastructure Inscription:** Automatic generation of **[Systemd Quadlets (08)](08-containers.md)** based on the Soulstone definitions in the **[Codex (12)](12-configuration.md)** and extension requirements.
- **Extension Injection:** A formal hook mechanism allowing extensions to register system-level dependencies (e.g., C-libraries) and custom container requirements during the **[Federation (05)](05-extensions.md)** phase.
- **Deterministic Manifests:** Generation of a "Synthesis Manifest"—a pinned record of every dependency and its cryptographic hash to ensure verifiable provenance.
- **Pluggable Forge Strategies:** Support for both a **Mundane Path** (imperative `Containerfile` with Jinja-based injections) and a **Absolute Path** (Nix-based functional image construction).
- **The Great Seal:** Explicitly Read-Only runner environments (`chmod -R a-w`) to prevent runtime tampering and enforce the separation between evolution and execution.
- **Source-Centric Assembly:** Preservation of raw Python source files and docstrings to enable the runtime introspection required for self-reflection.
- **Assimilation Before ABI:** Preservation of coupled source as the pre-v1 compatibility mechanism; public SDK/ABI surfaces are harvested only after stable patterns survive real Forge cycles.
- **Manual Transition Gate:** Air-gapped activation of new images requiring a manual signal via the **CLI** to prevent autonomous "Infection and Restart" loops.
- **Installable Runtime:** A clean wheel install must contain every dependency required by the shipped `lychd` CLI, Vessel, workers, persistence, and agent runtime in its wheel metadata.
- **Development-Only Groups:** Dependency groups may carry documentation, test, lint, and type-check tools; they may not hide packages required by an installed runtime.
- **License-Complete Artifacts:** Source distributions, wheels, images, and synthesized bodies must
  carry every license and attribution notice required by incorporated or adapted source.

## Considered Options

!!! failure "Option 1: Individual Extension Containers (Sidecars)"
    Running every extension in its own isolated container within the Pod.

    -   **Pros:** Maximum isolation between logic components.
    -   **Cons:** **Extreme Resource Tax.** Significant VRAM and CPU overhead for dozens of interpreters. It introduces network latency for internal calls and complicates the orchestration of **[Workers (14)](14-workers.md)**.

!!! failure "Option 2: Imperative Monolithic Build"
    Generating a single, giant `Containerfile` that installs extensions sequentially via shell scripts.

    -   **Pros:** Conceptually simple; utilizes standard OCI tooling.
    -   **Cons:** **Non-Deterministic.** Dependency conflicts between Extensions are only caught at runtime. It fails the standard for verifiable provenance required for a sovereign daemon.

!!! success "Option 3: Two-Phase Synthetic Packaging"
    Utilizing a logical **Synthesis** phase followed by a pluggable **Manifestation** strategy.

    -   **Pros:**
        -   **Logical Sanity:** Resolves dependency math using native tools (`uv` and `npm`) *before* the physical build begins.
        -   **Infrastructure Synchronization:** Ensures the Systemd Quadlets are regenerated to match the new code substrate.
        -   **Pluggable Evolution:** Allows for a low-friction start with standard tools while providing an upgrade path to advanced functional construction.

## Decision Outcome

**Synthetic Functional Packaging** is adopted as the definitive standard for the system substrate. The Forge operates in two distinct phases: logical convergence followed by physical binding.

### 0. The Installable Foundation

Before synthetic extension composition, Nix derivations, or autonomous Rebirth can be trusted,
the ordinary Python artifact must be complete. The foundation therefore has a smaller and
non-negotiable contract:

- All packages imported by the installed CLI, ASGI Vessel, database/migration layer, SAQ workers,
  and Pydantic AI/Graph runtime live in `[project.dependencies]` and therefore in wheel metadata.
- `[dependency-groups]` contains contributor tooling only (`docs`, `test`, `lint`, `typing`, and
  their `dev` aggregate). A production image uses the locked project dependencies without asking
  for a development group or a nonexistent optional extra.
- The installed `lychd --help`, its closed eight-root public grammar, and the internal server,
  migration, worker, and Reactor process entrypoints used by generated units must resolve from the
  wheel without a source checkout on `PYTHONPATH`. Framework-native `serve` and `database`
  commands are not public roots.
- A release gate builds the wheel, creates a clean environment, installs that wheel alone, checks
  its dependency metadata, imports the runtime composition root, and invokes the public and
  internal process help surfaces. It verifies exact package-version parity, the immutable source
  revision embedded in the Altar, byte-identical project and dependency notices, source archive
  completeness, and SHA-256 receipts. Passing inside the developer's already-synchronized
  `.venv` is not evidence of installability.
- Candidate construction begins from a clean checkout at one full Git object ID. It may rewrite
  only the generated `src/lychd/public/` tree while compiling the exact-source Altar.
- Version preparation changes reviewed files only. It does not commit, tag, publish, or push.
- The repository's candidate workflow has read-only repository permission and retains wheel and
  source archives as short-lived workflow artifacts. It has no PyPI or container-registry
  publication authority.

The source and archive gates are implemented foundation law, but they are not a public-release
receipt. State remains Designed until a committed candidate passes the hosted workflow and a
separately approved public artifact pair is validated. Multi-manifest extension synthesis, the
signed Synthesis Manifest, the Nix strategy, and autonomous Forge/Rebirth remain staged work; they
may build on the archive contract but may not weaken it.

!!! warning "Forge doctrine beyond the foundation"
    The sections below define the intended synthetic Forge. Today the repository has a checked-in,
    locked, multi-stage `Containerfile` and the complete wheel dependency floor. Extension manifest
    merging, Jinja injection, a signed synthesis manifest, Nix manifestation, and atomic Rebirth are
    not implemented end to end.

### 1. The Synthesis Stage (Logical Convergence)

When a packaging ritual begins, the system performs a multi-dimensional synthesis by scanning both the **Built-in** registry and the **Crypt (13)** to prepare for the physical build:

- **Anatomical Grafting:** The Manager discovers all **Built-in Extensions** and establishes the kernel's baseline runtime and substrate requirements through the in-tree registration path. This is an in-memory operation that defines the body the Forge must then manifest.
- **The Code Layer (Substrate Synthesis):** All `pyproject.toml` (Python) and `package.json` (Node)
  manifests from active **Crypt Extensions** are merged with the core manifests. A styling
  framework configuration is not a separately composable manifest; trusted client contributions
  join the Altar's native CSS and compile-time component boundary. Near-term Crypt extensions are
  private coupled organs unless they explicitly target a future versioned public API. The system
  executes frozen Python and npm locks to create deterministic build inputs for the composed body.
- **Substrate Injection:** During assimilation, extensions declare system-level dependencies (e.g., C-libraries like `ffmpeg` or specialized binaries) and custom container requirements as part of the composed-runtime law. These are collected into the global synthesis manifest to be Manifested during the Forge. The `register(context)` hook is only the boot-time grafting branch of that law.
- **The Infrastructure Layer:** The system reads `Soulstone` intents from the **Codex (12)** and infrastructure requirements from all active Extensions. It dynamically calculates the `lychd.pod` configuration, aggregating all `ExposePort` requirements and hardware tags for **Containers (08)**.
- **Global Arbitration:** The Manager performs a mandatory conflict check across the entire manifest. It enforces the **Law of Exclusivity**, ensuring no port collisions, image-name overlaps, or dependency version deadlocks exist. Only upon successful arbitration are the "Dumb Blueprints" handed to the **Quadlet Scribe** to manifest the concrete Systemd Quadlet files.
- **Binary Organ Synthesis:** Rust/PyO3 organs are a Forge-mediated future path. A compiled organ may be built into the composed image as a coupled organ, or later target a versioned public API once that product surface exists. The active runtime must not blindly scan `.so` files; binary artifacts require manifest pinning, platform validation, and explicit activation.

!!! note "Why Multi-Language Synthesis Is Possible"
    Cross-language synthesis is possible because the Forge builds one composed runtime image and verifies it before promotion. It is not proof of a stable in-process ABI. Until LychD has a versioned public API and conformance suite, binary organs are either coupled to the composed image or isolated behind an external-service Animator boundary. An external-service Animator may expose model inference, tools, observability, peer delegation, or any other typed capability; the boundary is the service contract, not the presence of an LLM.

    Pre-v1, packaging is the repair boundary: source and manifests are assembled together so the Smith can inspect and adapt the organ. At v1, repeated stable seams may be harvested into a public API. Post-v1, that API becomes a compatibility product rather than an assumption baked into infancy.

### 2. The Forge Strategies

#### The Mundane Path (Current Standard)

This is the primary mechanism for manifestation, currently using a checked-in multi-stage
**`Containerfile`**. Forge-time Jinja injection is the planned extension-composition layer; the
foundation build does not claim to render the Containerfile dynamically.

1. **Injections:** Extension-registered system dependencies are injected into the `RUN apt-get install` block of the template.
2. **Builder Stage:** Mounts the `uv` binary and cache to perform a frozen sync of the synthesized manifests.
3. **Runner Stage:** A hardened, non-root environment based on `python-slim`.
4. **The Seal:** The `/app` directory is stripped of write permissions. `PYTHONDONTWRITEBYTECODE=1` is set to ensure the source remains readable for Agentic introspection.

The checked-in foundation avoids the `psycopg-binary` distribution and its bundled native-library
set. It uses pure-Python `psycopg` with Debian `libpq5`, preserves Debian package copyright records,
and generates a fail-closed inventory of the Python distributions installed in the Vessel. This
narrows the redistributable surface; it does not promote the current Containerfile to a published
or fully attested image.

#### The Sovereign Path (The Nix Sigil)

This is the advanced, functional upgrade path for the image construction.

1. **Transmutation:** Consumes the synthesized manifests and transmutes them into a functional derivation.
2. **Calculation:** Nix calculates the filesystem structure into a local store, ensuring every binary is cryptographically pinned.
3. **OCI Construction:** Nix manufactures the layered image directly from the store, bypassing the non-determinism of standard base images.

### 3. The Rebirth Gate

The resulting image is loaded into the local registry as `lychd:custom`. To ensure the Magus remains the ultimate arbiter, the activation of the new body is an air-gapped ritual. The system refuses to restart the container or apply the new **[Quadlets (08)](08-containers.md)** until it receives a manual confirmation command via the **CLI**.

### 4. Runtime Trust Profiles

The Forge target emits three separately auditable runtime profiles:

- Vessel image: trusted control plane.
- **The Tomb** image: untrusted execution runtime. Carries Python, `uv`, `nono`, and common CLI tools only. No agent framework, no LLM client libraries, no graph runner dependencies.
- **Tomb** dependency expansion uses curated cache/broker channels by default.
- **The Coffin** image: delegated-agent runtime. Carries only audited adapter CLIs, the effectful
  supervisor, `nono`, and required transport libraries. It has no Core graph runner, database
  client, promotion tool, browser/keychain integration, or real provider credential.

Tomb and Coffin may share a hardened base layer, but they remain distinct generated profiles with
different entrypoints, dependency manifests, network policies, and adversarial receipts. Shipping
an executable or Python policy compiler in the Vessel does not prove either lower-trust image.

### 5. Authority Matrix

| Dimension | Vessel artifact | Tomb artifact | Coffin artifact |
| :--- | :--- | :--- | :--- |
| Secrets | Required control-plane injection only. | At most one narrow execution-queue credential. | Phantom Provider Gate capability only; no real provider or database secret. |
| Mounts | Trusted Codex/persistence contract. | Minimal disposable execution mounts. | Immutable projection or disposable candidate worktree plus scratch/artifacts. |
| Network | Controlled provider/control-plane access. | Brokered resources outside the zero-network child. | Exact Provider Gate protocol only. |
| Authority | May participate in controlled rebirth. | Claim/settle execution jobs; no rebirth. | Run one delegated job; no queue, promotion, rebirth, or infrastructure transition. |

### Consequences

!!! success "Positive"
    - **Install Honesty:** The wheel declares the complete shipped runtime instead of relying on an already-populated development environment.
    - **Provenance Path:** Frozen manifests provide the base from which stronger synthesis attestations can be built.
    - **Synchronized Reality:** Infrastructure (Quadlets) and Logic (Code) are updated in a single, atomic ritual, preventing "Blindness" where code expects a port that is not published.
    - **Predictable Evolution:** Dependency conflicts between Extensions are caught at build-time, preventing runtime instability.

!!! failure "Negative"
    - **Build Latency:** The synthesis and multi-stage build rituals are significantly slower than simple hot-loading.
    - **Storage Pressure:** Maintaining previous images and functional derivations increases the disk footprint of the Crypt.
