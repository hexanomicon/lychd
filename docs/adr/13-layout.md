---
title: 13. Layout
icon: material/file-tree
---

# :material-file-tree: 13. Layout: The Three Domains

!!! abstract "Context and Problem Statement"
    The LychD architecture functions as a hermetic system, interacting with the host filesystem in a highly structured manner to ensure that agents can effectively manipulate their environment without violating user security boundaries. Standard containerization often creates a disjointed experience where file paths valid on the host are invalid inside the container. Without a definitive and symmetric topology, the system cannot reliably locate its own memory, source code, or configuration across different execution contexts. There is a fundamental need for a map that enforces a clear separation between immutable logic and mutable state while supporting the advanced requirements of federated locking and speculative branching.

## Requirements

- **Path Symmetry:** Mandatory resolution of identical paths whether running on the Host or inside the Container, eliminating the need for context-aware path translation.
- **The XDG Trinity:** Strict adherence to the XDG Base Directory Specification (`CONFIG`, `DATA`, `CACHE`) to ensure standard Linux portability and predictable volume mapping.
- **Separation of Permissions:** Physical distinction between **The Law** (Configuration/Core Logic) mounted Read-Only, and **The Life** (Workspace/Database) mounted Read-Write.
- **Federated Lock Geography:** Provision of a central coordinate for the `lychd.lock` file to anchor the deterministic state of the system's organs.
- **Shadow Realm Infrastructure:** Support for isolated subdirectories within the **Lab** to facilitate speculative execution and branching during creation rituals.
- **Anatomical Persistence:** A dedicated region for the **[Phylactery's (06)](06-persistence.md)** chambers, optimized for Copy-on-Write snapshots.
- **Cartographic Rigidity:** Hardcoded locations for all critical domains to prevent fragmentation of the system's body.

## Considered Options

!!! failure "Option 1: Static Absolute Paths"
    Defining hardcoded paths (e.g., `/app/data` and `/home/user/lychd`).
    - **Cons:** **Path Dissonance.** This breaks when running on the host vs. the container. It requires the logic to constantly ask "Where am I?" and translate strings, leading to "Blindness" when an Agent tries to find a file.

!!! failure "Option 2: Environment-Variable Overload"
    Relying on dozens of `LYCHD_DATA_PATH`, `LYCHD_CONFIG_DIR` variables.
    - **Cons:** **Configuration Fragility.** It makes the system impossible to debug. A single missing variable in a `docker-compose` or `systemd` file bricks the Daemon. It lacks "Geographic Determinism."

!!! success "Option 3: Symmetric XDG Parity"
    Adhering to XDG standards and mapping them 1:1 into the container.
    - **Pros:** **Total Symmetry.** `~/.config/lychd` is the same string on the Host and the Vessel. This allows the machine to reason about its own body without a translation layer. It enforces the "Three Domains" (Law, Life, Industry) naturally.

## Decision Outcome

The filesystem is organized into **Three Domains** that govern the existence of the Daemon.

### 1. The Codex (`XDG_CONFIG_HOME`)

**"The Law."**
This Domain contains immutable configuration files and user-defined intents. It is mounted **Read-Only** into the container. The Agent cannot change the Law; only the Magus can modify these scrolls.

This ADR defines where the Codex lives and how it is mounted. The Codex contract (global `lychd.toml`, `runes/` ownership, anchor rules, singleton behavior, and loader validation) is governed by [Configuration (12)](12-configuration.md).

- **Host Path:** `~/.config/lychd/`
- **Internal Path:** `~/.config/lychd/` (Symmetric)

**Contents (Codex Taxonomy):**

- `lychd.toml`: Global settings

- **Rune Schemas (Anchored Instances):**
    - `animator/`: Animation root defaults and child anchors.
        - `soulstones/`: Local infrastructure intent (container-backed providers).
            - `llamacpp/`: Instances of llama.cpp providers (TOML files).
            - `vllm/`: Instances of vLLM providers.
            - `sglang/`: Instances of SGLang providers.
        - `portals/`: Remote API intent (network-backed providers).
            - `openai/`: Instances of OpenAI portals.
            - `anthropic/`: Instances of Anthropic portals.
            - *(future anchors live here as additional subdirectories)*

**Layout Notes:**

- The taxonomy above shows common built-in anchors for operator orientation.
- Installed extensions may add additional rune anchors under `runes/` while preserving the same directory-based ownership model.
- Loader rules, identity derivation, singleton behavior, and validation doctrine are specified in [Configuration (12)](12-configuration.md).

### 2. The Crypt (`XDG_DATA_HOME`)

**"The Body and Soul."**
This Domain contains the persistent reality of the system. It is the primary storage volume, subdivided into regions of varying permission levels.

- **Host Path:** `~/.local/share/lychd/`
- **Internal Path:** `~/.local/share/lychd/` (Symmetric)

**Internal Regions:**

- **`lychd.lock`:** The Federated Lockfile. Living in the root of the Crypt, it pins the exact hashes of all logic.
- **`core/`:** Core source code. Mounted **Read-Only** at runtime to maintain the **[Security (09)](09-security.md)** seal.
- **`extensions/`:** Plugin source code. Mounted **Read-Only** at runtime.
- **`postgres/`:** The site of the **Phylactery**. A dedicated subvolume containing the partitioned database chambers. Mounted **Read-Write**.
- **`lab/`:** The site of Genesis. A **Read-Write** region containing isolated subdirectories for **Shadow Realm** branches, allowing the machine to dream of new code without impacting reality.

### 3. The Forge (`XDG_CACHE_HOME`)

**"The Industrial District."**
This Domain contains disposable, machine-generated artifacts. It is excluded from backups and snapshots and can be purged at any time.

- **Host Path:** `~/.cache/lychd/`
- **Internal Path:** Ephemeral (Not typically mounted).

**Contents:**

- Build artifacts for the physical image.
- Temporary environment manifests used during the **[Packaging (17)](17-packaging.md)** ritual.

## The Outlands (External Mounts)

Beyond the Three Domains lies **The Outlands**—the User's own filesystem. To interact with these regions, the user must explicitly mount an Outland directory. These are mapped to a dedicated internal workspace target.

- **Internal Path Target:** `~/work/`

## Container-Side Topology

Inside the container, the layout mirrors the Host Domains via volume mounts. By utilizing identity mapping, the container user accesses the Read-Write paths natively without permission mismatches.

| Path                               | Domain   | Permission | Purpose                |
| :-----------------------------------| :---------| :-----------| :-----------------------|
| `~/.config/lychd/`                 | Codex    | **RO**     | Configuration          |
| `~/.local/share/lychd/`            | Crypt    | **RW**     | Lockfile & Persistence |
| `~/.local/share/lychd/core/`       | Crypt    | **RO**     | Core Logic             |
| `~/.local/share/lychd/extensions/` | Crypt    | **RO**     | Extension Logic        |
| `~/work/`                          | Outlands | **RW**     | External Workspace     |

### 4. Dual-Plane Trust Delta

The layout now separates trusted and untrusted execution geography.

- Vessel mounts trusted codex and durable control-plane regions.
- **The Tomb** mounts only task/workspace/artifact regions with minimal write scope.
- Suggested **Tomb** regions:
    - `~/.local/share/lychd/tomb/jobs/` — one subdirectory per SAQ job to prevent file collisions between concurrent Ghouls
    - `~/.local/share/lychd/tomb/workspaces/`
    - `~/.local/share/lychd/tomb/artifacts/`
    - `~/.local/share/lychd/tomb/cache/`
- **The Tomb** must not mount full Codex or host trigger/signaling paths.
- **The Tomb** runs no agent logic, graph runners, or LLM calls. It is a brainless executor. See **[Workers (14)](14-workers.md)**.

### 5. Authority Matrix

| Dimension | Vessel (Trusted Control Plane) | The Tomb (Untrusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Secret-bearing codex paths under `0600` ownership. | No secret-bearing codex paths. |
| Mounts | Codex plus required durable crypt regions. | Task-scoped workspace/artifact/cache mounts. |
| Network | Internal control-plane connectivity. | Minimal connectivity with deny-by-default egress. |
| Queue Ownership | Queue state mapped through trusted persistence paths. | No queue state mounts. |
| Authority Boundaries | Trigger/intent geography available. | No trigger/intent mount access. |

### Consequences

!!! success "Positive"
    - **Operational Simplicity:** The symmetric layout ensures that code and agents behave identically regardless of whether they are executing on the host or in the container.
    - **Physical Integrity:** The placement of the `lychd.lock` and the `postgres/` subvolume within the same Crypt allows for the atomic **[Snapshots (07)](07-snapshots.md)** required for total recall.
    - **Development Fluidity:** The structured `lab/` domain provides the physical space required for safe, autonomous self-modification.

!!! failure "Negative"
    - **Path Rigidity:** Users must adhere to the XDG structure; non-standard layouts require manual environment variable overrides.
    - **Mount Discipline:** The system relies on the **[CLI (19)](19-cli.md)** Hand to correctly map these domains during the binding ritual; an incorrect mount leads to immediate systemic blindness.
