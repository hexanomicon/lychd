---
title: 17. Packaging
icon: material/package-variant-closed
---

# :material-package-variant-closed: 17. Packaging: The Synthetic Forge

!!! abstract "Context and Problem Statement"
    The capability for autonomous evolution creates a fundamental substrate paradox. A Lych is a composite organism, its physical body formed by merging disparate manifests (Python, Node, System) and infrastructure intents (Systemd Runes) into a single, cohesive runtime. Standard imperative container build cycles suffer from "Substrate Drift"—where external repository shifts or re-tagged base images cause the same source code to produce different binary artifacts over time. A mechanism is required to resolve dependency conflicts and forge a new body for the Daemon that is both mathematically deterministic and synchronized with the machine's physical state.

## Requirements

- **Multi-Manifest Synthesis:** Discovery and merging of `pyproject.toml` (Python), `package.json` (Node), and `tailwind.config.js` from all active extensions into a single build context.
- **Infrastructure Inscription:** Automatic generation of **[Systemd Runes (08)](08-containers.md)** based on the Soulstone definitions in the **[Codex (12)](12-configuration.md)** and extension requirements.
- **Extension Injection:** A formal hook mechanism allowing extensions to register system-level dependencies (e.g., C-libraries) and custom container requirements during the **[Federation (05)](05-extensions.md)** phase.
- **Deterministic Manifests:** Generation of a "Synthesis Manifest"—a pinned record of every dependency and its cryptographic hash to ensure verifiable provenance.
- **Pluggable Forge Strategies:** Support for both a **Mundane Path** (imperative `Containerfile` with Jinja-based injections) and a **Sovereign Path** (Nix-based functional image construction).
- **The Great Seal:** Explicitly Read-Only runner environments (`chmod -R a-w`) to prevent runtime tampering and enforce the separation between evolution and execution.
- **Source-Centric Assembly:** Preservation of raw Python source files and docstrings to enable the runtime introspection required for self-reflection.
- **Manual Transition Gate:** Air-gapped activation of new images requiring a manual signal via the **CLI** to prevent autonomous "Infection and Restart" loops.

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

### 1. The Synthesis Stage (Logical Convergence)

When a packaging ritual begins, the system scans the **[Crypt (13)](13-layout.md)** and performs a dual synthesis:

- **The Code Layer:** All `pyproject.toml`, `package.json`, and asset configs are merged. The system executes a frozen lock to create the single source of truth for the **[Backend (11)](11-backend.md)** environment.
- **The Infrastructure Layer:** The system reads the `Soulstone` intents from the **[Codex (12)](12-configuration.md)**. It uses the **Rune Scribe** to manifest the concrete Systemd Quadlet files. It dynamically calculates the `lychd.pod` configuration, aggregating all `ExposePort` requirements from the active extensions.
- **Extension Registration:** Extensions use their `register(context)` hook to inject specific requirements into this manifest (e.g., `context.add_system_dependency("ffmpeg")`).

### 2. The Forge Strategies

#### The Mundane Path (Current Standard)

This is the primary mechanism for manifestation, utilizing a multi-stage **`Containerfile`** rendered via Jinja2.

1. **Injections:** Extension-registered system dependencies are injected into the `RUN apt-get install` block of the template.
2. **Builder Stage:** Mounts the `uv` binary and cache to perform a frozen sync of the synthesized manifests.
3. **Runner Stage:** A hardened, non-root environment based on `python-slim`.
4. **The Seal:** The `/app` directory is stripped of write permissions. `PYTHONDONTWRITEBYTECODE=1` is set to ensure the source remains readable for Agentic introspection.

#### The Sovereign Path (The Nix Sigil)

This is the advanced, functional upgrade path for the image construction.

1. **Transmutation:** Consumes the synthesized manifests and transmutes them into a functional derivation.
2. **Calculation:** Nix calculates the filesystem structure into a local store, ensuring every binary is cryptographically pinned.
3. **OCI Construction:** Nix manufactures the layered image directly from the store, bypassing the non-determinism of standard base images.

### 3. The Rebirth Gate

The resulting image is loaded into the local registry as `lychd:custom`. To ensure the Magus remains the ultimate arbiter, the activation of the new body is an air-gapped ritual. The system will refuse to restart the container or apply the new **[Runes (08)](08-containers.md)** until it receives a manual confirmation command via the **CLI**.

### Consequences

!!! success "Positive"
    - **Mathematical Provenance:** The system provides proof that the physical "Body" perfectly matches the instruction "Scroll."
    - **Synchronized Reality:** Infrastructure (Runes) and Logic (Code) are updated in a single, atomic ritual, preventing "Blindness" where code expects a port that is not published.
    - **Predictable Evolution:** Dependency conflicts between Extensions are caught at build-time, preventing runtime instability.

!!! failure "Negative"
    - **Build Latency:** The synthesis and multi-stage build rituals are significantly slower than simple hot-loading.
    - **Storage Pressure:** Maintaining previous images and functional derivations increases the disk footprint of the Crypt.
