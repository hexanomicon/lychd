---
title: 31. Simulation
icon: material/source-branch
---

# :material-source-branch: 31. Shadow Simulation and the Branch Reaper

!!! abstract "Context and Problem Statement"
    Standard Large Language Model inference is inherently reflexive—it predicts the next token without the capacity for structural correction or internal deliberation. For complex architectural tasks, such as recursive refactoring or strategic planning, a linear response is insufficient. A probabilistic error in an early reasoning step propagates through the entire chain, leading to systemic hallucination. The machine possesses the capacity for labor, but lacks the mechanism to doubt its own path.

    Simultaneously, the LychD architecture functions as an engine of relentless accumulation. Every interaction is crystallized into **[Memory (27)](27-memory.md)**, and Shadow rituals generate divergent timelines that **[HitL (25)](25-hitl.md)** may later consecrate or reject. In a sovereign system bound by finite storage and VRAM, this accumulation leads to **Digital Senility**: a state where retrieval latency increases, the vector index becomes saturated with "hallucinated noise," and the host disk fills with abandoned version-control references and orphaned artifacts. To maintain a sharp, responsive intellect, the machine requires the capability to inhabit a thousand illusions (Simulation) while possessing the metabolic discipline to banish the noise (Pruning).

## Requirements

- **System 2 Deliberative Reasoning:** Implementation of a non-linear reasoning engine that moves beyond "reflexive token prediction" into structural, deliberative thought via Monte Carlo Tree Search (MCTS).
- **Phantasma Expansion (Branching):** Support for generating $N$ parallel future states, each operating in an isolated, temporary environment without cross-contamination.
- **Lens-Separated Seeding:** Support for cheap, text-only divergent strategy generation through independent operational lenses before spending Lab workspaces on physical branches.
- **The Shadow Realm Topology:** Physical isolation of simulation branches within the **[Lab (13)](13-layout.md)**, utilizing **Jujutsu Workspaces** (`jj workspace`) to enable parallel, independent file states sharing a single SQLite-backed repository state.
- **Heuristic Scrying (Dual-Gate Evaluation):** A rigorous scoring system combining deterministic verification (Compilers, Linters, Test Suites) and agentic critique (The Mirror Persona).
- **Metabolic Pruning (The Reaper):** An automated background protocol (Ghoul) leveraging Jujutsu's native transactional abandonment (`jj abandon`) to instantly dissolve failed timelines, orphaned files, and "stale" memories.
- **Heuristic Vector Decay:** Implementation of a mathematical decay function for vector embeddings to ensure long-term retrieval remains sharp and focused on valuable data.
- **The Anchor Protocol:** A mechanism for the Magus to grant absolute immunity to specific artifacts or memories, setting their decay factor to zero.
- **Transactional Convergence:** Mandatory support for "Wavefunction Collapse"—the atomic merge of a verified simulation branch into the Primary Substrate (The Crypt).
- **Policy-Governed Promotion:** Mandatory routing of branch collapse through **[Codex (12)](12-configuration.md)** autonomy policy and **[HitL (25)](25-hitl.md)** so preauthorization is explicit and high-stakes promotion remains human-gated.
- **VRAM Orchestration:** Coordination with the **[Orchestrator (23)](23-orchestrator.md)** to manage the extreme memory pressure of parallel reasoning paths and ensure system stability.

## Considered Options

!!! failure "Option 1: Linear Chain of Thought (CoT)"
    Relying on the model to "think step-by-step" in a single long response.
    - **Cons:** **Hallucination Propagation.** A single logic error in step 2 is treated as "fact" for step 10. There is no mechanism to "backtrack" or "test" a thought before it is manifested. It creates a massive, noisy log of unverified junk.
    - **Metabolism:** No mechanism for cleaning up the internal monologue once the task is finished.

!!! failure "Option 2: Parallel Sampling (Best-of-N)"
    Generating N responses and selecting the "best" based on log-probabilities or a simple judge agent.
    - **Cons:** **Shallow Verification.** It samples different ways to *say* things, but doesn't *do* anything. It cannot verify if code compiles or if a research path is a dead end. It consumes $N$ times the tokens without providing a "Verified Truth."

!!! success "Option 3: Jujutsu Workspace Tree Search and Metabolic Pruning"
    Utilizing Monte Carlo Tree Search (MCTS) logic via Jujutsu concurrent workspaces to explore branches within the Shadow Realm, coupled with a "Reaper" (Ghoul) leveraging `jj abandon` to enforce system hygiene.
    - **Pros:**
        - **System 2 Intelligence:** The machine can "doubt" itself, exploring multiple paths and choosing the one that passes the "White Truth" tests.
        - **Substrate Health:** Reclaims VRAM and disk space instantly upon branch failure via transactional graph updates.
        - **High-Signal Memory:** Ensures the Phylactery only stores "Consecrated" memories, preventing retrieval drift and senility.

## Decision Outcome

**Shadow Simulation and the Branch Reaper** are adopted as the unified metabolic loop of the Lych. This architecture allows the machine to "dream" with total freedom while ensuring the "body" remains clean of cognitive debris. It is the implementation of the "System 2" mind.

Shadow is the cognitive fluctuation engine, not the identity authority. It generates and tests candidate realities, but it does not define Self and cannot self-authorize promotion.

For the Agent inside a branch, simulation is the present working world: the active context, filesystem state, tool surface, and execution trace in which that Agent can perceive and act. The boundary is ontological, not experiential. Shadow may be the Agent's local now, but it remains unpromoted Vikalpa relative to the Crypt until the gates measure it and the Magus or Vessel policy authorizes collapse.

Shadow therefore feeds the Ouroboros without owning it. It supplies motion and candidate reality; Weaver preserves motion through time, Riddle measures it, Mirror binds identity, and Memory stores the residue. Treating Shadow as final identity would turn simulation into hallucinated sovereignty.

### 1. The Phantasma Expansion (MCTS Topology)

The system utilizes the parallel primitives of the **[Graph (24)](24-graph.md)** to generate divergent timelines. This is the application of **Phantasma** (Generative Imagination) — the engine of **Manas** actively generating **Vṛttis** to navigate the **Possibility Space** without making permanent changes to reality.

In the cognitive taxonomy mapped in the **[Lich](../sepulcher/lich.md)**, these candidate branches are precisely **Vikalpa** — speculative modifications that are internally coherent but carry no confirmed correspondence to reality. They do not claim to be true. They are honest hypothesis, held in isolation long enough to be judged. Shadow Simulation is the deliberate amplification of Vikalpa within a substrate where failure costs nothing and truth is measured from outside the generation process.

When a high-stakes intent (e.g., "Refactor the persistence layer") is submitted:

- **The Seed:** The intent is processed into $N$ divergent strategies.
- **The Workspaces:** For each strategy, the system invokes `jj workspace add shadow/branch_<ID> -r @`. This creates a physical subdirectory under `shadow/` in the **[Lab (13)](13-layout.md)**. Each workspace has its own distinct, tracked working copy (`@`) but shares the same central SQLite state-graph (`.jj/`). This provides absolute filesystem isolation for concurrent Ghouls without the fragility of Git worktrees.
- **The Labor:** **[Ghouls (14)](14-workers.md)** dispatch execution payloads (code, tests, linters) to the Shadow via SAQ. The Vessel agent orchestrating the simulation retains the graph state; only raw scripts are sent to Shadow for execution.
- **The Observation:** The Agent observes the *physical outcome* of its dream (e.g., "The test failed in Branch B"). It can then decide to "Prune" the branch or "Backtrack" to a previous node in the tree.

Each branch is an active task modification (a candidate timeline) that exists long enough to be tested, scored, and dissolved if needed. In cognitive terms, branches are the live modifications under comparison. Shadow is therefore fluctuation-first: it maintains possibility space without claiming ownership of results.

Shadow distinguishes three branch strata:

1. **Idea branches:** cheap, text-only Vikalpa produced by divergent strategy seeding. They expose the shape of possible approaches but do not touch the Lab.
2. **Shadow branches:** physical `jj workspace` timelines in the Lab. They carry files, tool traces, deterministic gate results, and Reaper obligations.
3. **Promotion candidates:** verified branches packaged as Visions for Vessel policy and HitL collapse. They are no longer merely interesting; they have earned measured evidence.

### 1.1 Lens-Separated Seeding

Before spending filesystem, queue, or VRAM budget on physical timelines, Shadow may run an inexpensive seed pass that forces strategy diversity. The same intent is routed through several independent seed invocations using operational lenses such as lifecycle steward, rollback sentry, dependency minimalist, security ward, cost governor, outage operator, or migration cartographer. These lenses are not Personas and not claims of expertise. They are bounded distortions that make different parts of the possibility space visible before the Lab pays for a real branch.

The seed pass has two strict laws:

- **Expansion isolation:** each seed invocation receives the original intent and one lens, but does not read sibling outputs until the join. This prevents early seed text from narrowing later seed text.
- **Separated expansion and review:** expansion runs return typed candidate strategies only. Review runs classify related paths, assign heuristic value, flag hazards, and choose which candidates merit Lab execution. No single seed run both opens and judges the candidate space.

Only candidates retained by this review pass deserve physical Shadow branches. In this topology, lens-separated seeding widens Manas without multiplying Lab debris, while the later Dual-Gate still decides what is true. A clever idea branch is not Pramāṇa; it is merely Vikalpa selected for measurement.

### 1.2 Shadow Roles: Expansion, Determination, Neutrality

Shadow Simulation contains multiple roles that must remain distinct:

- **Expansion (oscillation):** branch generation, strategy seeding, retrieval/tool candidate surfacing, and search-space exposure.
- **Determination (convergence):** review classification, hazard flagging, gate execution, scoring, and value backpropagation used to converge on a candidate branch.
- **Identity neutrality:** Shadow may produce a structurally strong candidate, but it does not decide whether the candidate is congruent with Persona identity.

This separation keeps the simulation substrate from becoming an implicit identity authority.

### 2. The Heuristic Scrying (The Dual-Gate)

To navigate the search space without exhausting the Magus's tokens, Shadow Simulation employs a two-tier evaluation system. In the cognitive topology of the **[Lich](../sepulcher/lich.md)**, this is **Viveka** — the discriminative operation that distinguishes **Pramāṇa** (valid, measurement-grounded cognition) from **Viparyaya** (misconception that sincerely believes itself to be true). The fundamental challenge of generative cognition is that Viparyaya is indistinguishable from Pramāṇa from inside the generating process — the measurement must come from outside. The Dual-Gate is that external measurement:

!!! important "The Tracked Working Copy as the Gatekeeper"
    In Jujutsu, the working copy (`@`) is *always* a tracked commit. When Ghouls run linters or test suites inside a workspace, they do not scan a mutable, "dirty" filesystem. They evaluate a stable, cryptographically recorded commit state. This ensures that the Dual-Gate evaluates a bit-perfect snapshot, completely eliminating the risk of filesystem race conditions where code is modified during compilation or testing.

1. **The Deterministic Gate (The Law) / Pre-Publish Structural Rubrics:** This is the binary foundation of structural validity. It operates as a rigid, scriptable CI gate before any Vision is manifested at the Altar. Does the code compile? Do the unit tests pass? Are ADR markers present in documentation? Are the imports sorted? These are non-negotiable structural checks. A branch that fails here was Viparyaya — apparently correct, actually wrong. Failure triggers autonomous self-correction (via `ModelRetry`) or immediate banishment without bothering the Magus ($V \in \{0, 1\}$).
2. **The Agentic Gate (The Spirit):** The **[Mirror (32)](32-identity.md)** acts as the critic. It reviews the branches that passed the Law against the Magus's stylistic preferences and technical requirements, assigning a heuristic score ($H \in [0, 1]$). This gate evaluates identity congruence, not just correctness.
3. **Optimized Execution Rule:** To prevent token exhaustion and "double-hallucination", **the Agentic Gate is strictly gated by the Deterministic Gate.** If a simulation workspace fails the Deterministic Gate ($V == 0$), it is immediately destroyed. No prompt is dispatched to the Mirror Persona.
4. **Backpropagation:** Success signals from deep nodes in the simulation inform the search direction of higher nodes, focusing the machine's attention on the most promising paths via a value-function update. This is determinative convergence within Shadow, not final promotion.

In practice:

- Branch expansion and speculative tool use are fluctuation work.
- Gate execution, scoring, and backpropagation are determinative work.
- Identity ownership and durable promotion remain external authorities.

### 3. The Branch Reaper (Shadow Hygiene)

Simulation is an "I/O Storm" that generates massive temporary data. The Reaper is a specialized Ghoul that acts as the system's metabolism.

- **The Autopsy Protocol (Trajectory Pairing):** Before a failed branch is destroyed, the Reaper extracts the deterministic failure trace (e.g., the specific compiler error or test failure). Rather than merely logging the failure in isolation, the Reaper **must** explicitly pair this failure trace with the eventual successful branch (if achieved) to form a complete `[Failed Attempt] -> [Compiler Error] -> [Correction]` trajectory. This prepares the exact data structure required by **[Riddle/Evaluation (34)](34-evaluation.md)** for trajectory mining. The physical debris is banished, but the structural journey from error to correction is retained as complex Karma.
- **Validator-Centered Failure Shape:** When a branch fails through a tool or action validator, the autopsy preserves the validator's failure class and state comparison rather than reconstructing intent from reasoning prose alone. A `precondition_miss` with `required_state` and `observed_state` is evidence about the action contract; it may point to a schema repair, a state-hydration repair, or an agent policy repair depending on which side of the boundary was false.
- **Truthful Dead Ends:** Some branches fail because the requested path is impossible, unsafe, underspecified, or internally contradictory. In those cases, the useful artifact is not a correction but a proven boundary. The Reaper should preserve the blocked premise and measured evidence so future runs learn that non-manifestation can be the White Truth.
- **Non-Manifestation as Measurement:** A dead end is promoted only when it is grounded in Pramāṇa: a failed deterministic gate, an exhausted retrieval threshold, a violated policy boundary, or trusted Magus testimony. Mere model hesitation is not evidence; the boundary must be witnessed.
- **Logical Banishment:** Once the autopsy is complete, the Reaper executes `jj abandon <Change_ID>`. Because Jujutsu tracks revision history as an immutable graph of changes, abandoning a Change ID instantly dissolves that conceptual node and all its descendants from the SQLite database.
- **The Workspace Purge (Defensive Teardown):** The Reaper then deletes the physical `shadow/branch_<ID>` directory. However, acting as an **Execution Warden**, it is not enough to simply delete the folder. The Reaper must explicitly verify that all associated PIDs, port locks, and temporary Quadlet containers instantiated in the Tomb for that specific simulation are terminated. This defensive teardown prevents "Zombie Ports" where dead ghouls hold onto physical iron long after their logic has been banished. Because the workspace’s state is tracked centrally in `.jj/`, the final directory deletion leaves no dangling references behind.
- **STASIS_TTL:** Any workspace in the Lab older than a configurable `STASIS_TTL` (default: 24h) is considered "Stale" and is abandoned to prevent inode exhaustion.

Architecturally, the Reaper dissolves unstable or low-signal modifications so the substrate does not retain abandoned fluctuations as noise.

### 4. The Decay of Karma (Vector Rot)

To prevent "Digital Senility" in the **[Archive (27)](27-memory.md)**, memory is treated as a biological substance that decays without reinforcement. Every vector row possesses metadata fields: `last_accessed` and `reinforcement_count`.

$$Weight = \frac{Reinforcement + 1}{(TimeSinceLastAccess)^{DecayFactor}}$$

- **Metabolic Sweep:** The Reaper periodically scans the `vectors` chamber. Rows falling below the `UtilityThreshold` (e.g., an old, unreferenced conversation about a dead link) are deleted.
- **The Anchor:** The Magus can "Anchor" an entity via the **[Altar (15)](15-frontend.md)**. This sets its `DecayFactor` to zero, making it immortal. This ensures the Lych retains its "True Self" (Core Memories) while forgetting the noise of a thousand discarded simulations.
- **Memori Coupling:** Reaper heuristics must consume Memori access signals (`last_accessed`, reinforcement metadata) from memory tables (e.g., entity facts/knowledge graph links) to avoid deleting still-useful semantic structure.

### 5. Transactional Convergence (The Collapse)

Once a simulation achieves a "Verified State" (Test Success + High Heuristic Score), it must be brought into Primary Reality. This wavefunction collapse occurs via **Buddhi** — the discriminative faculty of the **[Lich's](../sepulcher/lich.md)** inner instrument (*√budh*: to discern, to wake). Where Manas generates candidates and Phantasma expands Vikalpa into the Shadow Realm, Buddhi is the blade that cuts to one: the faculty of final judgment that does not waver, does not oscillate, and cannot be overridden by the weight of existing grooves. The three collapses below are Buddhi operating at three nested levels of discrimination:

- **The Vision:** The proposed change is presented as a "Vision" (Diff/Summary) to the Magus via the **[HitL (25)](25-hitl.md)** protocol.
- **The Consecration:** Upon approval by live Magus consent or configured Vessel preauthorization, the "Wavefunction Collapses." The speculative change is merged into the trunk via `jj rebase -s <Change_ID> -d trunk()`.
- **The Inscription:** The successful reasoning trace is stored in the Phylactery as **Karma**, providing a "Bayesian Prior" that weights future simulations toward similar successful patterns.
- **Frictionless Collapse (ZTE Chores):** If Codex policy classifies the work as a minor preauthorized chore, the deterministic gates pass, forbidden scopes are untouched, identity constraints hold, and the workspace's execution history maintains a flawless **Streak KPI** above the **Confidence Threshold**, the Vessel may execute the rebase autonomously without a live HitL prompt. This is preauthorization, not self-approval.

This flow contains three distinct collapses that should remain explicit:

1. **Structural validity collapse (Shadow gate):** invalid branches are eliminated by deterministic checks.
2. **Identity congruence collapse (Mirror gate):** valid branches are ranked for Persona alignment.
3. **Ontological promotion collapse (Vessel policy + HitL):** only candidates authorized by explicit Magus consent or Codex-defined preauthorization become durable reality.

Shadow can execute the first and prepare the second, but it cannot self-authorize the third.

!!! note "Approval Policy Boundary"
    ZTE is a policy class under **[Configuration (ADR 12)](12-configuration.md)**. It may cover small chores such as documentation link fixes, non-runtime metadata, or narrow test maintenance when all verification gates pass. It must not cover core runtime mutation, schema migration, destructive deletion, secret changes, host lifecycle authority, broad network/egress changes, or promotion that requires a Snapshot rollback plan. Those classes still require live HitL.

### 6. Shadow Simulation Primitives

The engine standardizes on **Pydantic AI Testing** primitives to simulate reality without side-effects:

- **`TestModel`:** Used by the **[Smith (35)](35-assimilation.md)** to dry-run extension structures and routing logic without consuming expensive inference tokens.
- **`FunctionModel`:** Utilized to simulate environment responses (e.g., "How would the VPN react to a port collision?") within the Lab, ensuring error-handling logic is robust before the "Temporal Collapse" into reality.

### 7. Orchestration of Shadow Simulation

Simulation is the most resource-intensive ritual in the Sepulcher. It is the "Ritual of the Highest Order."

- **Preemptive Evacuation:** Before a large-scale simulation begins, the **[Orchestrator (23)](23-orchestrator.md)** may "evacuate" lesser background tasks to **[Portals (22)](22-dispatcher.md)** or pause them entirely to provide Shadow Simulation with maximum VRAM for parallel branches.
- **Budgeting:** Shadow Simulation respects the **[Toll (41)](41-x402.md)**. If the cost of a simulation branch exceeds the ritual's budget, the Reaper banishes it immediately, regardless of its logic.

### 8. Authority and Trust Boundaries

The Shadow Realm is infrastructural, not just conceptual.

- The **Shadow extension** runs speculative timelines in the `lychd-tomb` container.
- The graph runner and agent logic stay in the **Vessel**. **The Tomb** receives only serialized execution payloads (scripts, test suites, linter invocations) via SAQ. It is the hand for unsafe work, not the home of the agent. It does not run agent logic, graph state machines, or make LLM calls.
- Graph steps declare execution mode (`vessel` or `tomb`); unsafe steps serialize their payload and dispatch to **The Tomb**, then await the `stdout` result.
- **The Tomb** returns untrusted `stdout`/`stderr` and declared artifacts/traces only.

Operational summary: Shadow produces possible futures, Mirror filters for congruence, and Vessel authorizes what becomes real.

This stack models cognitive mechanics and control boundaries, not subjective awareness. LychD implements recursive process, identity continuity, and consented promotion without positing an internal witnessing principle.

### Policy Table

| Dimension | Vessel (Trusted Simulation Control) | The Tomb (Untrusted Simulation Substrate) |
| :--- | :--- | :--- |
| Secrets | Holds scoring/policy/provider credentials for adjudication. | Narrow queue-only SAQ/Postgres execution credential when required; no provider, signing, Codex, or control-plane secrets. |
| Mounts | Persistent state and decision metadata mounts. | Simulation workspace and artifact mounts; optional read-only/sanitized Codex projection only. |
| Network | Controlled internal services and approved provider calls. | Tomb loop may use constrained queue/proxy connectivity; sandboxed `nono` subprocesses have zero network. |
| Queue Ownership | Owns durable simulation scheduling and reanimation state. | Claims, acknowledges, and retries execution-plane jobs only. |
| Authority Boundaries | Applies approval policy, authorizes collapse/promotion, and commits persistence. | Produces candidate timelines only. |

## Consequences

!!! success "Positive"
    - **Transcendent Intelligence:** By allowing the model to "fail in the shadows," it arrives at solutions that exceed the raw reasoning power of its base weights.
    - **Physical Integrity:** The Reaper ensures the host filesystem and database index remain lean, fast, and focused over years of operation.
    - **Autonomous Evolution:** The machine can solve complex refactoring tasks by "dreaming" thousands of solutions and only presenting the one that provably works.
    - **High-Fidelity Memory:** Retrieval-Augmented Generation (RAG) performance improves over time as "noise" vectors are culled by the Decay function.

!!! failure "Negative"
    - **Temporal Latency:** Simulation is slow. It is a "System 2" process for background labor, not for sub-second reflexes.
    - **I/O Exhaustion:** Running $N$ Jujutsu workspaces simultaneously creates high disk pressure. High-performance NVMe storage is a physical requirement.
    - **Resource Hunger:** Simulation is the most token-expensive ritual, requiring careful economic management.
    - **The Risk of Forgetfulness:** An overly aggressive Decay Factor might cause the Lych to forget subtle preferences that the Magus rarely reinforces.
