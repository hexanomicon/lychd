---
title: 18. Evolution
icon: material/refresh
---

# :material-refresh: 18. Evolution: The Ouroboros

!!! abstract "Context and Problem Statement"
    A sovereign daemon must be capable of two distinct forms of growth: **Exogenous** (Updates from the Upstream Creator) and **Endogenous** (Autopoietic modifications by the Self).

    A collision between these forces—where a local mutation conflicts with an upstream patch—results in a "Lobotomized State." The machine becomes unbootable or incoherent. Standard package managers are blind to the nuance of local code modifications. A protocol is required to treat the act of "Updating" as a high-order reasoning task that reconciles the intent of the Creator with the reality of the Creature, rather than as a file-overwrite operation.

## Requirements

- **The Tri-State Jujutsu Strategy:** Mandatory management of three code states: **Upstream** (Remote), **Local** (Active), and **Dream** (Shadow Realm).
- **The Rebase Ritual:** Updates are prepared through a Jujutsu rebase candidate that attempts to
  preserve attributable local changes on the new upstream foundation.
- **The Conflict Resolution Loop:** A merge conflict blocks promotion and becomes a bounded repair
  task in a sandboxed environment. Failure returns truthful noncompletion; it does not force the
  active body to accept a guessed resolution.
- **The Breaking Change Detector:** Automated execution of the verification suite against all active extensions *after* the code merge but *before* the physical restart.
- **The Recovery Plan:** Before promotion, the workflow records tested recovery coordinates for
  body, lockfile, and **[Phylactery (06)](06-persistence.md)** state. Recovery follows each
  owner's contract and reconciles external effects; it is not assumed to be one atomic rollback.
- **Policy-Governed Promotion:** Update promotion must be authorized by explicit Magus consent or a Codex-defined low-risk maintenance preauthorization. High-stakes update, migration, and host-lifecycle steps remain live HitL gated.
- **Elevated Execution:** Authorization to trigger the **[Host Reactor (10)](10-privilege.md)** to restart the **[Vessel (11)](11-backend.md)** only after the code has been successfully transmuted and packaged.

## Considered Options

!!! failure "Option 1: Blind Updates (pip install --upgrade)"
    Standard package management.

    - **Cons:** **The Shattered Mind.** If the upstream introduces a breaking change, all locally forged extensions crash immediately. The user is left with a broken system and no path to recovery.

!!! failure "Option 2: The Frozen State (Never Update)"
    Treating the install as immutable.

    - **Cons:** **Stagnation.** The Lich fails to receive security patches, performance optimizations, or new capabilities from the Hive Mind.

!!! success "Option 3: The Ouroboros (Reasoned Merging)"
    Treating an update as a **Migration of Logic**. The system attempts to merge the new wisdom of the Creator with the accumulated experience of the Self.

    -   **Pros:**
        -   **Preservation of Self:** Local modifications (Autopoiesis) are prioritized and reapplied on top of updates.
        -   **Evidence Before Promotion:** The update is rejected when its declared verification
            and authorization gates do not pass. Passing them proves only those predicates.

## Decision Outcome

**The Ouroboros Protocol** is adopted as the Prime Directive of the Lifecycle. It defines how the **[Creation (16)](16-creation.md)** and **[Packaging (17)](17-packaging.md)** rituals are applied to the Core itself.

!!! warning "Implementation State"
    The end-to-end Ouroboros update, repair, migration, recovery, and restart composition is
    **Designed**. No autonomous updater or self-healing lifecycle ships today. The steps below are
    target law and must not be read as a current command or recovery guarantee.

!!! note "Implementation Scope"
    This ADR governs the evolution of the LychD implementation only. LychD is not "the Agentic OS" and does not require every agentic system to target its body. Other daemon implementations may evolve by their own rites. Across bodies, they speak protocols such as A2A.

!!! danger "The Ouroboros Fragility Theorem"
    Any in-process extension that imports LychD internals via `from lychd import ...` or ABC inheritance becomes a **structural dependent of the Core's import graph**. Every Ouroboros update cycle is a rebase of that graph. When an internal symbol is renamed, moved, or removed during a rebase, the extension's import statement may fail at load time. The Daemon cannot boot until the composed image is repaired or rolled back.

    This is not a smell by itself. It is the accepted cost of the pre-v1 private coupled path: the Forge, verification suite, and Smith repair loop evolve the Core and coupled components as one composed body. A public in-process API/ABI may reduce this import fragility later, but it must be harvested from proven patterns, versioned, and tested before it is advertised as a compatibility guarantee. External-service Animators are the current true decoupled boundary.

    LychD's first extension boundary is not compatibility; it is assimilation. Public compatibility is a product of maturity, not the foundation of infancy.

### 1. The Pre-Update Snapshot (The Anchor)

Before touching a single byte, the system triggers the **[Snapshot Protocol (07)](07-snapshots.md)**.

- **The Body:** It captures the `core/` and `extensions/` Jujutsu hexadecimal Commit IDs, lockfiles, and repository state.
- **The Soul:** It performs a database checkpoint of the **[Phylactery (06)](06-persistence.md)**.
This is the **Save Point**: an attributable recovery coordinate across separately owned state. It
is not one distributed instant, and restoration may require operator action or external-effect
reconciliation.

### 2. The Rebase Ritual (Jujutsu Topology)

The system operates on the `core/` repository within the **[Crypt (13)](13-layout.md)**. The system attempts to pull the new reality:

```bash
jj git fetch upstream
jj rebase -s <local-change-id> -d <upstream-main>
```

If a **Merge Conflict** occurs, the system uses **[Shadow Simulation (31)](31-simulation.md)** to explore candidate repairs and the **[Smith (35)](35-assimilation.md)** to reason through the conflict, treating the `.py` files as logic to be repaired rather than plain text.

### 3. The Compatibility Check (The Pain of Growth)

Once the code is merged, the system runs the **Verification Suite**:

1. It reinstalls dependencies (`uv sync`) to match the new lockfile.
2. It runs the test suite for **All Active Extensions**.

**The Crisis:** If a local extension fails because the Upstream renamed a core function, policy
may launch a bounded **Repair Task** to propose a compatible candidate. Exhaustion rejects the
update or asks for operator intervention.

**Why External Boundaries Survive:** A capability isolated behind an external-service Animator can survive Core refactors when its network contract, adapter, and Codex declaration remain stable. The capability may be inference, tooling, observability, peer delegation, or another service function. In-process independent compatibility is not promised today. A future public API can earn that status only after LychD harvests a small versioned surface from real components, conformance tests, and Forge packaging rules. Until then, in-process Crypt components are verified and repaired as part of the composed runtime image.

### 4. The Manifestation (Rebirth)

If—and only if—all tests pass and the promotion is authorized by live Magus consent or Codex-governed maintenance preauthorization, the mutation is consecrated:

1. The system triggers **[The Forge (17)](17-packaging.md)** to build the new container image.
2. It performs any required **Alembic Migrations** on the **[Phylactery (06)](06-persistence.md)**.
3. It writes the `INTENT_RESTART_VESSEL` signal to the **[Host Reactor (10)](10-privilege.md)**.
4. The host system attempts the validated restart. Success receipts must show which upstream
   features, local changes, and retained state actually survived; the ritual does not infer
   continuity from process startup alone.

### 5. The Great Reject (Rollback)

If the system *cannot* fix the breakage after ($N$) attempts:

1. It abandons the candidate change or returns the working copy to the pre-update Jujutsu state
   when that coordinate remains available.
2. It requests the tested recovery path for each affected state owner and names any indeterminate
   or externally visible effects.
3. It preserves a rejection record: intent, candidate diff, failing checks, relevant traces, and the reason the timeline was abandoned.
4. It notifies the Magus: *"I cannot evolve. The upstream reality is incompatible with my local components. Manual intervention required."*

Recovery aims to restore a proved body and Phylactery coordinate; it may fail partially and must
report that state honestly. The rejected candidate no longer has promotion authority, while its
autopsy may become a future test, memory candidate, or operator note.

### 6. Dual-Plane Trust Delta

Evolution follows the same control/unsafe split:

- Vessel owns update orchestration, snapshot gates, migration decisions, and restart intents.
- **The Tomb** may run unsafe build/test/repair work on speculative branches.
- **The Tomb** cannot trigger host intents, activate rebuilds, or promote durable state.
- Codex autonomy policy may preauthorize only low-risk maintenance update classes; migrations, lockfile shifts with runtime impact, host lifecycle authority, and failed-repair decisions remain live HitL gated.

### 7. Authority Matrix

| Dimension | Vessel (Trusted Evolution Control) | The Tomb (Untrusted Evolution Labor) |
| :--- | :--- | :--- |
| Secrets | Accesses credentials for fetch, package, and migration workflows. | No long-lived credentials or signing material. |
| Mounts | Trusted code, lock, and persistence coordination mounts. | Branch/worktree mounts for speculative repair only. |
| Network | Controlled upstream and internal control-plane routes. | No unrestricted outbound network in base mode. |
| Queue Ownership | Owns durable update workflow and recovery orchestration. | No durable workflow ownership. |
| Authority Boundaries | Emits restart/reload intents through host reactor contract. | Cannot emit infrastructure intents. |

## Consequences

!!! success "Positive"
    -   **Living Code:** Verified updates can preserve selected local capabilities while adopting
        upstream change.
    -   **Bounded Repair:** API breakage can receive attributable candidate repairs under a finite
        budget; unresolved breakage rejects the update.
    -   **Reduced Boot Risk:** Pre-restart checks and external recovery coordinates reduce the
        chance and duration of a bad-update boot loop without claiming to eliminate it.

!!! failure "Negative"
    -   **Update Latency:** An update is a "Ritual" that takes minutes, involving testing, potential AI refactoring, and rebuilding.
    -   **Merge Hallucination:** There is a non-zero risk that the AI resolves a merge conflict incorrectly.
