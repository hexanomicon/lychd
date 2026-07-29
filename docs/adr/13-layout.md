---
title: 13. Layout
icon: material/file-tree
---

# :material-file-tree: 13. Layout

!!! abstract "Context and Problem Statement"
    The LychD architecture functions as a hermetic system, interacting with the host filesystem in a highly structured manner to ensure that agents can effectively manipulate their environment without violating user security boundaries. Standard containerization often creates a disjointed experience where file paths valid on the host are invalid inside the container. Without a definitive and symmetric topology, the system cannot reliably locate its own memory, source code, or configuration across different execution contexts. There is a fundamental need for a map that enforces a clear separation between immutable logic and mutable state while reserving bounded geography for later governed creation and recovery.

## Requirements

- **Path Symmetry:** Mandatory resolution of identical paths whether running on the Host or inside the Container, eliminating the need for context-aware path translation.
- **The XDG Trinity:** Strict adherence to the XDG Base Directory Specification (`CONFIG`, `DATA`, `CACHE`) to ensure standard Linux portability and predictable volume mapping.
- **Separation of Permissions:** Physical distinction between **The Law** (Configuration/Core Logic) mounted Read-Only, and **The Life** (Workspace/Database) mounted Read-Write.
- **Shadow Realm Geography:** An explicit **Lab** workspace in which future governed creation
  rituals may isolate speculative branches.
- **Anatomical Persistence:** A dedicated region for the
  **[Phylactery's (06)](06-persistence.md)** chambers, with optional Btrfs and No-COW preparation
  for live PostgreSQL data.
- **Cartographic Rigidity:** Canonical XDG-derived locations for critical domains to prevent
  fragmentation of the system's body.
- **Ownership Before Removal:** A known LychD path identifies geography, not deletion authority;
  teardown must be bounded by exact creation and binding receipts.
- **Shared Binding Safety:** Host Binding sites must be prepared under one owner/mode/ancestor law;
  initialization may create them, while binding may only consume them.
- **Storage Creation Identity:** A Btrfs subvolume created by initialization must retain its exact
  kernel and Btrfs identity before it can receive later unmounted deletion authority.

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
- Selected and enabled extensions may add additional rune anchors under `runes/` while preserving the same directory-based ownership model.
- Loader rules, identity derivation, schema cardinality, and validation doctrine are specified in [Configuration (12)](12-configuration.md).

### 2. The Crypt (`XDG_DATA_HOME`)

**"The Body and Soul."**
This Domain contains the persistent reality of the system. It is the primary storage volume, subdivided into regions of varying permission levels.

- **Host Path:** `~/.local/share/lychd/`
- **Internal Path:** `~/.local/share/lychd/` (Symmetric)

**Internal Regions:**

- **`core/`:** Reserved core-source geography. When populated by a future governed
  installation flow, it is mounted **Read-Only** to maintain the
  **[Security (09)](09-security.md)** seal.
- **`extensions/`:** Private Crypt extension source. Pre-v1 this is assimilable, Forge-composed code rather than a stable third-party plugin ABI. Mounted **Read-Only** at runtime.
- **`postgres/`:** The **Phylactery** boundary. `data/` may be an external mount, a LychD-created
  Btrfs subvolume, or an ordinary directory; it is mounted **Read-Write** into PostgreSQL.
- **`lab/`:** The site of Genesis. A **Read-Write** region containing isolated subdirectories for **Shadow Realm** branches, allowing the machine to dream of new code without impacting reality.
- **`snapshots/`:** Reserved recovery-snapshot geography. Current initialization creates the
  shelf; it does not yet coordinate whole-body snapshots or restore.

There is intentionally no parallel `compositions/` source region in the Crypt. `extensions/`
answers where optional code enters the body; a Composition answers which application the Magus
operates after eligible contributions have been registered. One Extension package may contribute
several Compositions, and one Composition may assemble contributions from several Extension
packages, so mirroring the two names as sibling loaders would encode a false one-to-one
relationship.

Future immutable Composition and Suite descriptors belong to Weaver's logical Portfolio registry,
their explicit enablement belongs to the Codex boundary reserved by
[Configuration (12)](12-configuration.md#extension-activation-and-application-selection), and
their mutable campaigns, schedules, inventories, and other domain records belong to the
Phylactery. A future export, cache, or artifact bundle may acquire governed physical geography
only through its owning lifecycle law; no runtime may infer applications by scanning a
`compositions/` directory.

### 3. The Forge (`XDG_CACHE_HOME`)

**"The Industrial District."**
This Domain contains disposable, machine-generated artifacts. It is excluded from backups and snapshots and can be purged at any time.

- **Host Path:** `~/.cache/lychd/`
- **Internal Path:** Ephemeral (Not typically mounted).

**Contents:**

- **`assembly/`:** Reserved disposable staging for future build artifacts and packaging
  manifests. Current initialization creates the geography; no active Forge promotion pipeline
  populates it yet.

## Lifecycle Ownership

The two Binding sites are shared host namespaces, not recursively owned LychD roots.
Initialization creates each missing path component with mode `0700`. It preserves existing
directories rather than changing their mode, and refuses a site that is a symlink, is not a
directory, is owned by another UID, lacks owner read/write/search or effective access, permits
group/other writes, or lies beneath an ancestor writable by another principal unless that ancestor
is a sticky directory owned by UID 0 or the invoking UID, or the foreign-owned ancestor sits on a
kernel-reported read-only mount. `bind` applies this same law
during planning and commit and never creates a missing site.

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
attempts a subvolume plus `+C` and verifies both. Successful subvolume creation is not represented
as an ordinary directory: `btrfs subvolume show` must return a canonical subvolume UUID and an ID
outside Btrfs's reserved object range, and initialization records those values with the target's
device and inode in the version-2 lifecycle receipt. This authority is issued only for the exact
PostgreSQL target created in that initialization transaction. Loading an older receipt, rerunning
initialization over an existing target, or observing a live subvolume never backfills or adopts
that authority. Existing and missing ordinary layout paths are traversed component-by-component
through directory descriptors with no symlink following. A missing component is first created
under a private same-directory staging name, opened and device/inode-attested, then installed at
its public name with atomic no-replace semantics. Terminal interruption around publication or
rollback classifies both descriptor-relative names: a private candidate may be removed exactly,
while a published winner or incomplete quarantine becomes typed recovery. The opened identity and
original parent descriptor remain the journal authority; the receipt records those creation-time
values without restatting the replaceable public name. Failed journaling atomically quarantines
the current name through that parent before identity comparison. A replacement is restored rather
than deleted.
Linux has no inode-conditioned `rmdir`, so even an exact published creation remains at its
quarantine as a typed recovery handoff; only a never-published private staging candidate is
eligible for immediate removal. A newly materialized Btrfs target follows the typed path instead.

The same creation law governs paths materialized after the base layout pass. Rune anchors and
configured Reactor inbox/journal chains compose the descriptor-pinned directory provisioner and
carry its exact creation identities into the lifecycle receipt; precomputed absence never becomes
ownership. Codex and generated Rune files do not create parent directories. They require the
already provisioned parent, publish a fully written and file-`fsync`ed same-directory candidate
with atomic no-clobber semantics, re-attest the public identity through the pinned parent, and
directory-`fsync` before journaling. Failed journaling quarantines and compares the exact winner
before unlinking. A replacement or race winner is preserved and never enters initialization's
creation report; clean rollback preserves native `KeyboardInterrupt` and `SystemExit`, while
indeterminate settlement remains a typed recovery failure with the terminal cause attached.

Initialization reopens its previously observed parent and requires the same device/inode before
the Btrfs effect. Both `subvolume create` and the confirming `subvolume show` address the leaf
through that explicitly inherited parent descriptor at `/proc/self/fd/<fd>/<leaf>`, never through
the replaceable public parent pathname. Every failed, timed-out, or terminally interrupted create
is followed by a no-follow observation of that pinned leaf. Proven absence permits ordinary
fallback only for a nonterminal command failure; a present-but-unattested or indeterminate leaf
raises typed creation evidence and retains its substrate ancestry. It deliberately does not adopt
a UUID/ID after a failed mutator, because the present leaf could belong to a concurrent creator.
A successful create whose confirming `show` cannot produce canonical identity is retained under
the same typed rule. The new target is then opened relative to the same parent; its No-COW mutation
is issued through the child descriptor and its UUID/ID plus device/inode are re-attested before
journaling, so a path replacement cannot redirect creation, inspection, or `+C`, or produce a
mixed receipt. A verified No-COW false result is a nonblocking warning and the typed subvolume can
still be journaled. An exception after canonical identity is known, or a receipt failure, retains
the subvolume and its canonical substrate ancestry, then emits that identity as an explicit
recovery handoff rather than deleting a replaceable pathname or reinterpreting it as a directory.

Existing storage is never retrofitted: the CLI reports its filesystem and No-COW directory policy
while preserving it exactly. `+C` is an inheritance policy for newly created file extents beneath
an empty directory; it does not rewrite existing PostgreSQL files or prove that every extent is
No-COW. Non-Btrfs hosts receive an ordinary directory fallback.

`lychd del` is a separate, explicitly destructive installation lifecycle. Its dry run joins exact
receipt ownership with a live inventory of LychD services, containers, bindings, the Three
Domains, snapshots, and the Phylactery. Execution stops the installation before deleting managed
state and requires clear confirmation; it may therefore remove durable LychD data that `init`
correctly refused to claim as ordinary rollback authority.

That explicit scope does not turn path geography into permission to guess. Symlinks, unknown
mounts, ambiguous external resources, invalid receipts, or identity drift fail closed. Recursive
walks are descriptor-relative, reject mount-ID crossings, and stop at every traversed directory
with a possible Btrfs root/stub inode signature (`2` or `256`), including the dedicated root
itself. This is deliberately conservative on non-Btrfs filesystems: only typed receipt plus live
storage attestation may defer an exact Phylactery subvolume to the privileged handoff.

Final tree retirement does not perform `stat(name)` followed by `unlink(name)` or `rmdir(name)` on
the same predictable public name. After a root, child directory, or non-directory entry is opened
and revalidated, `del` atomically moves the current leaf beneath its pinned parent to a
collision-resistant private name with no-replace semantics. It opens and re-attests that
quarantine, then applies the type-specific unlink or empty-directory removal there. An identity
mismatch is restored to the public name without clobbering a concurrent occupant. A failed delete
is likewise restored for retry when possible; if restoration is blocked, the typed error and its
`LifecycleError` cause name the retained quarantine, and later tree inspection treats that marker
as a recovery blocker. In the Codex, ordinary entries retire first, but the privileged-handoff
checkpoint and lifecycle receipt remain protected inside the root. The root is detached under a
private sibling name; those authority files then move to exact private sibling backups, and they
are finalized only after empty-root removal is confirmed. Failure or terminal cancellation before
that confirmation restores both authorities and the root without clobbering. Failure after root
removal retains typed authority-backup evidence. A later `del` detects root or authority recovery
markers beside the root and blocks instead of silently reporting completion.

This protocol closes observable and accidental namespace concurrency between verification and
deletion. It does not claim isolation from a malicious process running as the same host UID that
deliberately discovers and mutates the fresh private quarantine inside the final syscall window;
that principal already possesses equivalent authority to unlink the user's LychD files directly.
Initialization rollback remains a different, stricter protocol: it never pathname-deletes a
published creation after attestation.

A separately mounted exact Btrfs Phylactery may enter the existing mounted-storage handoff only
through complete live `findmnt` and Btrfs identity: its mount target, source device, filesystem UUID,
filesystem root, source mapping, subvolume UUID, and subvolume ID must agree. Unmounted storage has
a narrower path. Only the exact PostgreSQL subvolume in the version-2 initialization receipt may
enter it, and live `lstat` device/inode plus `btrfs subvolume show` UUID/ID must still equal the
receipt. The covering filesystem must be proven Btrfs with a canonical filesystem UUID and source
device, an already mounted top-level (`fs_root=/`) anchor, and a safe lexical mapping from that
anchor to the target. A live unmounted subvolume without this creation receipt, a version-1
receipt, unavailable evidence, or any identity drift blocks the whole deletion plan.

After those checks, LychD records the same filesystem/subvolume identity in its continuation
checkpoint and prints a trusted absolute
`btrfs subvolume delete --subvolid ID TOP_LEVEL` operator handoff; the unmounted path needs no
unmount command. Resume re-attests the checkpoint and proceeds to generic tree removal only after
the subvolume is absent. LychD never invokes `sudo`. A source checkout and external model shelves
remain outside the Three-Domain deletion scope unless a distinct installer or artifact owner proves
authority over them. Until equivalent immutable creation receipts exist, Podman containers, pods,
secrets, and the installed package are also reported as preserved residue.

## The Outlands (External Mounts)

Beyond the Three Domains lies **The Outlands**—the User's own filesystem. To interact with these regions, the user must explicitly mount an Outland directory. These are mapped to a dedicated internal workspace target.

- **Internal Path Target:** `~/work/`

## Container-Side Topology

Inside the container, the layout mirrors the Host Domains via volume mounts. By utilizing identity mapping, the container user accesses the Read-Write paths natively without permission mismatches.

| Path                               | Domain   | Permission | Purpose                |
| :-----------------------------------| :---------| :-----------| :-----------------------|
| `~/.config/lychd/`                 | Codex    | **RO**     | Configuration          |
| `~/.local/share/lychd/lab/`        | Crypt    | **RW**     | Operator workspace     |
| `~/.local/share/lychd/core/`       | Crypt    | **RO**     | Core Logic             |
| `~/.local/share/lychd/extensions/` | Crypt    | **RO**     | Extension Logic        |
| `~/.local/share/lychd/triggers/inbox/` | Crypt | **RW**  | Reactor intents when selected |
| `~/.local/share/lychd/triggers/journal/` | Crypt | **RO** | Reactor outcomes when selected |
| `~/work/`                          | Outlands | **RW**     | External Workspace     |

There is no blanket read-write Crypt mount. Phylactery data belongs to the PostgreSQL unit, not
the Vessel; other runtime volumes are explicit Soulstone or operator declarations.

The host-readiness report's SELinux state is deliberately narrower than this mount map. An
`enforcing` observation proves the current SELinux mode only. Generated `:Z` mount intent does not
prove that a particular filesystem accepts relabeling or that the resulting service starts; that
requires real-host binding and startup evidence.

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
| Mounts | Codex RO; Lab RW; Core/Extensions RO; Reactor inbox RW and journal RO only when selected. No blanket Crypt mount. | Task-scoped workspace/artifact/cache mounts; no Codex mount (the No-Codex Law). |
| Network | Internal control-plane connectivity. | Tomb loop may use minimal queue/proxy connectivity; sandboxed `nono` subprocesses have zero network. |
| Queue Ownership | Queue state mapped through trusted persistence paths. | Claims, acknowledges, and retries execution-plane jobs only; no control-plane queue ownership. |
| Authority Boundaries | Trigger/intent geography available. | No trigger/intent mount access. |

### Consequences

!!! success "Positive"
    - **Operational Simplicity:** The symmetric layout ensures that code and agents behave identically regardless of whether they are executing on the host or in the container.
    - **Physical Integrity:** The prepared PostgreSQL storage and reserved snapshot shelf provide
      substrate for the future coordinated **[Snapshots (07)](07-snapshots.md)** ritual; they do
      not yet make whole-body recall atomic.
    - **Development Fluidity:** The structured `lab/` domain provides an explicit operator
      workspace for future governed creation flows; autonomous promotion is not yet delivered.

!!! failure "Negative"
    - **Path Rigidity:** Users must adhere to the XDG structure; non-standard layouts require manual environment variable overrides.
    - **Mount Discipline:** The system relies on the **[CLI (19)](19-cli.md)** Hand to correctly map these domains during the binding ritual; an incorrect mount leads to immediate systemic blindness.
