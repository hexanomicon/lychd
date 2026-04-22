---
title: 18. Evolution
icon: material/refresh
---

# :material-refresh: 18. Evolution: The Ouroboros

!!! abstract "Context and Problem Statement"
    A sovereign daemon must be capable of two distinct forms of growth: **Exogenous** (Updates from the Upstream Creator) and **Endogenous** (Autopoietic modifications by the Self).

    A collision between these forces—where a local mutation conflicts with an upstream patch—results in a "Lobotomized State." The machine becomes unbootable or incoherent. Standard package managers are blind to the nuance of local code modifications. A protocol is required to treat the act of "Updating" as a high-order reasoning task that reconciles the intent of the Creator with the reality of the Creature, rather than as a file-overwrite operation.

## Requirements

- **The Tri-State Git Strategy:** Mandatory management of three code states: **Upstream** (Remote), **Local** (Active), and **Dream** (Shadow Realm).
- **The Rebase Ritual:** Updates must be applied via `git rebase`, preserving local Autopoiesis on top of the new upstream foundation.
- **The Conflict Resolution Loop:** If a merge conflict occurs, the system must not crash; it must treat the conflict as a reasoning task, utilizing the system's cognitive engine to resolve the divergence in a sandboxed environment.
- **The Breaking Change Detector:** Automated execution of the verification suite against all active extensions *after* the code merge but *before* the physical restart.
- **The Atomic Rollback:** If the system fails to prove its own health after an update attempt, it must physically revert the `git` state and the **[Phylactery (06)](06-persistence.md)** schema to the pre-update **[Snapshot (07)](07-snapshots.md)**.
- **Elevated Execution:** Authorization to trigger the **[Host Reactor (10)](10-privilege.md)** to restart the **[Vessel (11)](11-backend.md)** only after the code has been successfully transmuted and packaged.

## Considered Options

!!! failure "Option 1: Blind Updates (pip install --upgrade)"
    Standard package management.

    - **Cons:** **The Shattered Mind.** If the upstream introduces a breaking change, all locally forged extensions crash immediately. The user is left with a broken system and no path to recovery.

!!! failure "Option 2: The Frozen State (Never Update)"
    Treating the install as immutable.

    - **Cons:** **Stagnation.** The Lych fails to receive security patches, performance optimizations, or new capabilities from the Hive Mind.

!!! success "Option 3: The Ouroboros (Reasoned Merging)"
    Treating an update as a **Migration of Logic**. The system attempts to merge the new wisdom of the Creator with the accumulated experience of the Self.

    -   **Pros:**
        -   **Preservation of Self:** Local modifications (Autopoiesis) are prioritized and reapplied on top of updates.
        -   **Immunity to Breakage:** The update is rejected if the system cannot mathematically prove it is healthy.

## Decision Outcome

**The Ouroboros Protocol** is adopted as the Prime Directive of the Lifecycle. It defines how the **[Creation (16)](16-creation.md)** and **[Packaging (17)](17-packaging.md)** rituals are applied to the Core itself.

### 1. The Pre-Update Snapshot (The Anchor)

Before touching a single byte, the system triggers the **[Snapshot Protocol (07)](07-snapshots.md)**.

- **The Body:** It captures the `core/` and `extensions/` git commit hashes.
- **The Soul:** It performs a database checkpoint of the **[Phylactery (06)](06-persistence.md)**.
This is the **Save Point**. If the Ouroboros chokes, the system reverts to this instant.

### 2. The Rebase Ritual (Git Topology)

The system operates on the `core/` repository within the **[Crypt (13)](13-layout.md)**. The system attempts to pull the new reality:

```bash
git fetch upstream
git rebase upstream/main
```

If a **Merge Conflict** occurs, the system utilizes its **[Shadow Realm (25)](25-hitl.md)** capabilities (later defined as the Smith) to reason through the conflict, treating the `.py` files as logic to be repaired rather than plain text.

### 3. The Compatibility Check (The Pain of Growth)

Once the code is merged, the system runs the **Verification Suite**:

1. It reinstalls dependencies (`uv sync`) to match the new lockfile.
2. It runs the test suite for **All Active Extensions**.

**The Crisis:** If a local extension fails because the Upstream renamed a core function, the system launches a **Repair Task** to refactor the local code to match the new reality.

### 4. The Manifestation (Rebirth)

If—and only if—all tests pass, the mutation is consecrated:

1. The system triggers **[The Forge (17)](17-packaging.md)** to build the new container image.
2. It performs any required **Alembic Migrations** on the **[Phylactery (06)](06-persistence.md)**.
3. It writes the `INTENT_RESTART_VESSEL` signal to the **[Host Reactor (10)](10-privilege.md)**.
4. The host system restarts the service. The Lych wakes up. It has the new features of the Upstream, but it retains the memories and modifications of the Self.

### 5. The Great Reject (Rollback)

If the system *cannot* fix the breakage after ($N$) attempts:

1. It aborts the Rebase.
2. It restores the **Save Point**.
3. It notifies the Magus: *"I cannot evolve. The upstream reality is incompatible with my local organs. Manual intervention required."*

### 6. Dual-Plane Trust Delta

Evolution follows the same control/unsafe split:

- Vessel owns update orchestration, snapshot gates, migration decisions, and restart intents.
- Shadow may run unsafe build/test/repair work on speculative branches.
- Shadow cannot trigger host intents, activate rebuilds, or promote durable state.
- Only Vessel can consecrate outcomes into system state.

### Policy Table

| Dimension | Vessel (Trusted Evolution Control) | Shadow (Untrusted Evolution Labor) |
| :--- | :--- | :--- |
| Secrets | Accesses credentials for fetch, package, and migration workflows. | No long-lived credentials or signing material. |
| Mounts | Trusted code, lock, and persistence coordination mounts. | Branch/worktree mounts for speculative repair only. |
| Network | Controlled upstream and internal control-plane routes. | No unrestricted outbound network in base mode. |
| Queue Ownership | Owns durable update workflow and recovery orchestration. | No durable workflow ownership. |
| Authority Boundaries | Emits restart/reload intents through host reactor contract. | Cannot emit infrastructure intents. |

## Consequences

!!! success "Positive"
    -   **Living Code:** The system stays current without sacrificing its unique, locally-grown capabilities.
    -   **Self-Healing:** API breaking changes are automatically refactored by the AI.
    -   **Safety:** The Daemon never enters a "Boot Loop" state from a bad update.

!!! failure "Negative"
    -   **Update Latency:** An update is a "Ritual" that takes minutes, involving testing, potential AI refactoring, and rebuilding.
    -   **Merge Hallucination:** There is a non-zero risk that the AI resolves a merge conflict incorrectly.
