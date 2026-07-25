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
- **Ownership Before Removal:** A known LychD path identifies geography, not deletion authority;
  teardown must be bounded by exact creation and binding receipts.

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

This ADR defines where the Codex lives and how it is mounted. The Codex contract (global `lychd.toml`, `runes/` ownership, anchor rules, schema cardinality, and loader validation) is governed by [Configuration (12)](12-configuration.md).

- **Host Path:** `~/.config/lychd/`
- **Internal Path:** `~/.config/lychd/` (Symmetric)

**Contents (Codex Taxonomy):**

- `lychd.toml`: Global settings

- **Rune Schemas (Anchored Instances):**
    - `runes/`: Validated TOML instance declarations.
        - `animator/`: Animation root defaults and child anchors.
            - `soulstones/`: Local infrastructure intent (container-backed providers).
                - `exllamav3/`: Dynamic ExLlamaV3 instances served by TabbyAPI.
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
- Loader rules, identity derivation, schema cardinality, and validation doctrine are specified in [Configuration (12)](12-configuration.md).

### 2. The Crypt (`XDG_DATA_HOME`)

**"The Body and Soul."**
This Domain contains the persistent reality of the system. It is the primary storage volume, subdivided into regions of varying permission levels.

- **Host Path:** `~/.local/share/lychd/`
- **Internal Path:** `~/.local/share/lychd/` (Symmetric)

**Internal Regions:**

- **`lychd.lock`:** The Federated Lockfile. Living in the root of the Crypt, it pins the exact hashes of all logic.
- **`core/`:** Core source code. Mounted **Read-Only** at runtime to maintain the **[Security (09)](09-security.md)** seal.
- **`extensions/`:** Private Crypt extension source. Pre-v1 this is assimilable, Forge-composed code rather than a stable third-party plugin ABI. Mounted **Read-Only** at runtime.
- **`postgres/`:** The **Phylactery** boundary. `data/` may be an external mount, a LychD-created
  Btrfs subvolume, or an ordinary directory; it is mounted **Read-Write** into PostgreSQL.
- **`lab/`:** The site of Genesis. A **Read-Write** region containing isolated subdirectories for **Shadow Realm** branches, allowing the machine to dream of new code without impacting reality.

### 3. The Forge (`XDG_CACHE_HOME`)

**"The Industrial District."**
This Domain contains disposable, machine-generated artifacts. It is excluded from backups and snapshots and can be purged at any time.

- **Host Path:** `~/.cache/lychd/`
- **Internal Path:** Ephemeral (Not typically mounted).

**Contents:**

- Build artifacts for the physical image.
- Temporary environment manifests used during the **[Packaging (17)](17-packaging.md)** ritual.

## Lifecycle Ownership

`lychd init` distinguishes exact paths it creates from durable substrate it may provision. It
journals each successful creation batch in an owner-only lifecycle receipt. After the complete
transaction converges, the same receipt deliberately adopts the current device/inode identities of
the dedicated Codex, Crypt, and Forge roots as recursively removable installation authority. Each
root is opened relative to its parent and must share the parent's Linux mount ID; an unsafe
existing root blocks before any effect, even when another root is still absent. The dry run states
this grant; geography alone does not create it.

Shared XDG parents and mounted Postgres data never enter that root authority. An ordinary
unmounted Phylactery directory beneath Crypt is inside the explicitly adopted dedicated root; a
model shelf, source checkout, foreign mount, or mounted Phylactery is not adopted merely because
the map knows its location. A mounted Phylactery instead requires live mount and Btrfs identity
evidence during `del`.

Initialization observes the nearest existing filesystem beneath the PostgreSQL target. When
`data/` is absent on Btrfs and trusted `btrfs`, `chattr`, and `lsattr` tools are available, it
attempts a subvolume plus `+C` and verifies both. Existing storage is never retrofitted: the CLI
reports its filesystem and No-COW directory policy while preserving it exactly. `+C` governs new
file extents beneath that directory; it does not prove that pre-existing PostgreSQL extents were
rewritten. Non-Btrfs hosts receive an ordinary directory fallback.

`lychd del` is a separate, explicitly destructive installation lifecycle. Its dry run joins exact
receipt ownership with a live inventory of LychD services, containers, bindings, the Three
Domains, snapshots, and the Phylactery. Execution stops the installation before deleting managed
state and requires clear confirmation; it may therefore remove durable LychD data that `init`
correctly refused to claim as ordinary rollback authority.

That explicit scope does not turn path geography into permission to guess. Symlinks, unknown
mounts, ambiguous external resources, invalid receipts, or identity drift fail closed. Recursive
walks are descriptor-relative and reject mount-ID crossings. If an inspected Btrfs subvolume needs
elevation, LychD checkpoints the canonical filesystem UUID, subvolume UUID, subvolume ID, source
mapping, and mount target before printing a trusted absolute operator command; resume blocks unless
that whole identity can be re-attested. LychD never invokes `sudo`. A source checkout and external
model shelves remain outside the Three-Domain deletion scope unless a distinct installer or
artifact owner proves authority over them. Until equivalent immutable creation receipts exist,
Podman containers, pods, secrets, and the installed package are also reported as preserved residue.

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

The layout doctrine separates trusted and untrusted execution geography. The generated v1
foundation manifests only the trusted core; Tomb paths and mounts below are reserved target
geography, not evidence that a Tomb unit currently exists.

- Vessel mounts trusted Codex and durable control-plane regions. Agents, graph state, LLM calls, routing, validation, and promotion policy stay in this trusted plane.
- Safe creation/control-plane work may remain in Vessel when it does not require arbitrary code execution or risky host mutation. Tomb is chosen by execution risk, not by the word "creation" alone.
- **The Tomb** mounts only task/workspace/artifact regions with minimal write scope. It is the execution hand for unsafe labor, not an agent home.
- Suggested **Tomb** regions:
    - `~/.local/share/lychd/tomb/jobs/` — one subdirectory per SAQ job to prevent file collisions between concurrent Ghouls
    - `~/.local/share/lychd/tomb/workspaces/`
    - `~/.local/share/lychd/tomb/artifacts/`
    - `~/.local/share/lychd/tomb/cache/`
- **The Tomb** must not mount writable Codex, provider secrets, or host trigger/signaling paths.
- **The Tomb** may receive a narrow queue-only SAQ/Postgres credential for execution-plane job claiming, acknowledgement, and retry bookkeeping, but no control-plane database authority.
- **The Tomb** runs no agent logic, graph runners, or LLM calls. It is a brainless executor. See **[Workers (14)](14-workers.md)**.

!!! note "The No-Codex Law"
    The Tomb mounts **no Codex**—not read-only, not sanitized, not projected. A job carries its complete runtime envelope in its payload (**[Backend (11)](11-backend.md)**'s task-safe, secret-forbidden Tomb config). If a job seems to need configuration its payload cannot carry, the design of the job is wrong, not the mount table. This law deletes the notion of a "sanitized Codex projection" outright; **[Security (09)](09-security.md)**, **[Backend (11)](11-backend.md)**, and **[Configuration (12)](12-configuration.md)** cross-reference this statement rather than each defining a sanitizer.

### 5. Authority Matrix

| Dimension | Vessel (Trusted Control Plane) | The Tomb (Untrusted Execution Plane) |
| :--- | :--- | :--- |
| Secrets | Secret-bearing Codex paths under `0600` ownership. | Narrow queue-only SAQ/Postgres execution credential when required; no provider keys, Codex secrets, or control-plane credentials. |
| Mounts | Codex plus required durable Crypt regions. | Task-scoped workspace/artifact/cache mounts; no Codex mount (the No-Codex Law). |
| Network | Internal control-plane connectivity. | Tomb loop may use minimal queue/proxy connectivity; sandboxed `nono` subprocesses have zero network. |
| Queue Ownership | Queue state mapped through trusted persistence paths. | Claims, acknowledges, and retries execution-plane jobs only; no control-plane queue ownership. |
| Authority Boundaries | Trigger/intent geography available. | No trigger/intent mount access. |

### Consequences

!!! success "Positive"
    - **Operational Simplicity:** The symmetric layout ensures that code and agents behave identically regardless of whether they are executing on the host or in the container.
    - **Physical Integrity:** The placement of the `lychd.lock` and the `postgres/` subvolume within the same Crypt allows for the atomic **[Snapshots (07)](07-snapshots.md)** required for total recall.
    - **Development Fluidity:** The structured `lab/` domain provides the physical space required for safe, autonomous self-modification.

!!! failure "Negative"
    - **Path Rigidity:** Users must adhere to the XDG structure; non-standard layouts require manual environment variable overrides.
    - **Mount Discipline:** The system relies on the **[CLI (19)](19-cli.md)** Hand to correctly map these domains during the binding ritual; an incorrect mount leads to immediate systemic blindness.
