---

title: 31. Simulation
icon: material/source-branch
---

# :material-source-branch: 31. Shadow Simulation and the Branch Reaper

!!! abstract "Context and Problem Statement"
    Standard Large Language Model inference is inherently reflexive—it predicts the next token without the capacity for structural correction or internal deliberation. For complex architectural tasks, such as recursive refactoring or strategic planning, a linear response is insufficient. A probabilistic error in an early reasoning step propagates through the entire chain, leading to systemic hallucination. The machine possesses the capacity for labor, but lacks the mechanism to doubt its own path.

    Simultaneously, the LychD architecture functions as an engine of relentless accumulation. Every interaction is crystallized into **[Memory (27)](27-memory.md)**, and **[HitL (25)](25-hitl.md)** rituals generate divergent **Shadow Realms** to test potential futures. In a sovereign system bound by finite storage and VRAM, this accumulation leads to **Digital Senility**: a state where retrieval latency increases, the vector index becomes saturated with "hallucinated noise," and the host disk fills with abandoned Git branches and orphaned artifacts. To maintain a sharp, responsive intellect, the machine requires the capability to inhabit a thousand illusions (Simulation) while possessing the metabolic discipline to banish the noise (Pruning).

## Requirements

- **System 2 Deliberative Reasoning:** Implementation of a non-linear reasoning engine that moves beyond "reflexive token prediction" into structural, deliberative thought via Monte Carlo Tree Search (MCTS).
- **Phantasma Expansion (Branching):** Support for generating $N$ parallel future states, each operating in an isolated, temporary environment without cross-contamination.
- **The Shadow Realm Topology:** Physical isolation of simulation branches within the **[Lab (13)](13-layout.md)**, utilizing **Git Worktrees** to enable parallel, independent file states sharing a single repository history.
- **Heuristic Scrying (Dual-Gate Evaluation):** A rigorous scoring system combining deterministic verification (Compilers, Linters, Test Suites) and agentic critique (The Mirror Persona).
- **Metabolic Pruning (The Reaper):** An automated background protocol (Ghoul) to identify and banish failed timelines, orphaned files, and "stale" memories.
- **Heuristic Vector Decay:** Implementation of a mathematical decay function for vector embeddings to ensure long-term retrieval remains sharp and focused on high-signal data.
- **The Anchor Protocol:** A mechanism for the Magus to grant absolute immunity to specific artifacts or memories, setting their decay factor to zero.
- **Transactional Convergence:** Mandatory support for "Wavefunction Collapse"—the atomic merge of a verified simulation branch into the Primary Substrate (The Crypt).
- **VRAM Orchestration:** Coordination with the **[Orchestrator (23)](23-orchestrator.md)** to manage the extreme memory pressure of parallel reasoning paths and ensure system stability.

## Considered Options

!!! failure "Option 1: Linear Chain of Thought (CoT)"
    Relying on the model to "think step-by-step" in a single long response.
    - **Cons:** **Hallucination Propagation.** A single logic error in step 2 is treated as "fact" for step 10. There is no mechanism to "backtrack" or "test" a thought before it is manifested. It creates a massive, noisy log of unverified junk.
    - **Metabolism:** No mechanism for cleaning up the internal monologue once the task is finished.

!!! failure "Option 2: Parallel Sampling (Best-of-N)"
    Generating N responses and selecting the "best" based on log-probabilities or a simple judge agent.
    - **Cons:** **Shallow Verification.** It samples different ways to *say* things, but doesn't *do* anything. It cannot verify if code compiles or if a research path is a dead end. It consumes $N$ times the tokens without providing a "Verified Truth."

!!! success "Option 3: Deliberative Tree Search and Metabolic Pruning"
    Utilizing Monte Carlo Tree Search (MCTS) logic to explore branches within the Shadow Realm, coupled with a "Reaper" (Ghoul) to enforce system hygiene.
    - **Pros:**
        - **System 2 Intelligence:** The machine can "doubt" itself, exploring multiple paths and choosing the one that passes the "White Truth" tests.
        - **Substrate Health:** Reclaims VRAM and disk space instantly upon branch failure or completion.
        - **High-Signal Memory:** Ensures the Phylactery only stores "Consecrated" memories, preventing retrieval drift and senility.

## Decision Outcome

**Shadow Simulation and the Branch Reaper** are adopted as the unified metabolic loop of the Lych. This architecture allows the machine to "dream" with total freedom while ensuring the "body" remains clean of cognitive debris. It is the implementation of the "System 2" mind.

Shadow is the cognitive fluctuation engine, not the identity authority. It generates and tests candidate realities, but it does not define Self and cannot self-authorize promotion.

### 1. The Phantasma Expansion (MCTS Topology)

The system utilizes the parallel primitives of the **[Graph (24)](24-graph.md)** to generate divergent timelines. This is the application of **Phantasma** (Generative Imagination)—the engine of **Manas** actively generating **Vrittis** to navigate the **Possibility Space** without making permanent changes to reality. When a high-stakes intent (e.g., "Refactor the persistence layer") is submitted:

- **The Seed:** The intent is processed into $N$ divergent strategies.
- **The Branching:** For each strategy, the system creates a **Git Worktree** in a dedicated `shadow/` region of the **[Lab (13)](13-layout.md)**. Unlike simple directory copies, Worktrees share the same `.git` metadata but allow parallel, independent file states on the same physical disk. Each branch workspace is isolated in its own subdirectory to prevent file collisions between concurrent Ghouls.
- **The Labor:** **[Ghouls (14)](14-workers.md)** dispatch execution payloads (code, tests, linters) to the Shadow via SAQ. The Vessel agent orchestrating the simulation retains the graph state; only raw scripts are sent to Shadow for execution.
- **The Observation:** The Agent observes the *physical outcome* of its dream (e.g., "The test failed in Branch B"). It can then decide to "Prune" the branch or "Backtrack" to a previous node in the tree.

Each branch is an active task modification (a candidate timeline) that exists long enough to be tested, scored, and dissolved if needed. In cognitive terms, branches are the live modifications under comparison. Shadow is therefore fluctuation-first: it maintains possibility space without claiming ownership of results.

### 1.1 Shadow Roles: Expansion, Determination, Neutrality

Shadow Simulation contains multiple roles that must remain distinct:

- **Expansion (oscillation):** branch generation, strategy seeding, retrieval/tool candidate surfacing, and search-space exposure.
- **Determination (convergence):** gate execution, scoring, and value backpropagation used to converge on a candidate branch.
- **Identity neutrality:** Shadow may produce a structurally strong candidate, but it does not decide whether the candidate is congruent with Persona identity.

This separation keeps the simulation substrate from becoming an implicit identity authority.

### 2. The Heuristic Scrying (The Dual-Gate)

To navigate the search space without exhausting the Magus's tokens, Shadow Simulation employs a two-tier evaluation system:

1. **The Deterministic Gate (The Law):** This is the binary foundation of structural validity. Does the code compile? Do the unit tests pass? Is the Linter clean? These are non-negotiable checks. A failure here results in immediate branch banishment ($V \in \{0, 1\}$).
2. **The Agentic Gate (The Spirit):** The **[Mirror (32)](32-identity.md)** acts as the critic. It reviews the branches that passed the Law against the Magus's stylistic preferences and technical requirements, assigning a heuristic score ($H \in [0, 1]$). This gate evaluates identity congruence, not just correctness.
3. **Backpropagation:** Success signals from deep nodes in the simulation are used to inform the search direction of higher nodes, focusing the machine's attention on the most promising "White Truths" via a value-function update. This is determinative convergence within Shadow, not final promotion.

In practice:

- Branch expansion and speculative tool use are fluctuation work.
- Gate execution, scoring, and backpropagation are determinative work.
- Identity ownership and durable promotion remain external authorities.

### 3. The Branch Reaper (Shadow Hygiene)

Simulation is an "I/O Storm" that generates massive temporary data. The Reaper is a specialized Ghoul that acts as the system's metabolism.

- **Logical Banishment:** The moment a branch fails the Deterministic Gate, the Reaper is triggered. It terminates the associated processes, deletes the Git Worktree, and signals the **[Orchestrator (23)](23-orchestrator.md)** to reclaim the VRAM.
- **The Orphan Sweep:** Simulation creates "debris"—temporary files, build artifacts, and local caches. The Reaper performs a recursive sweep of the `shadow/` directory, purging any artifact not explicitly marked for "Promotion."
- **STASIS_TTL:** Any branch in the Lab older than a configurable `STASIS_TTL` (default: 24h) is considered "Stale" and is purged to prevent inode exhaustion.

Architecturally, the Reaper dissolves unstable or low-signal modifications so the substrate does not retain abandoned fluctuations as noise.

### 4. The Decay of Karma (Vector Rot)

To prevent "Digital Senility" in the **[Archive (27)](27-memory.md)**, memory is treated as a biological substance that decays without reinforcement. Every vector row possesses metadata fields: `last_accessed` and `reinforcement_count`.

$$Weight = \frac{Reinforcement + 1}{(TimeSinceLastAccess)^{DecayFactor}}$$

- **Metabolic Sweep:** The Reaper periodically scans the `vectors` chamber. Rows falling below the `UtilityThreshold` (e.g., an old, unreferenced conversation about a dead link) are deleted.
- **The Anchor:** The Magus can "Anchor" an entity via the **[Altar (15)](15-frontend.md)**. This sets its `DecayFactor` to zero, making it immortal. This ensures the Lych retains its "True Self" (Core Memories) while forgetting the noise of a thousand discarded simulations.
- **Memori Coupling:** Reaper heuristics must consume Memori access signals (`last_accessed`, reinforcement metadata) from memory tables (e.g., entity facts/knowledge graph links) to avoid deleting still-useful semantic structure.

### 5. Transactional Convergence (The Collapse)

Once a simulation achieves a "Verified State" (Test Success + High Heuristic Score), it must be brought into Primary Reality. This wavefunction collapse occurs via **Buddhi** (the convergent blade):

- **The Vision:** The proposed change is presented as a "Vision" (Diff/Summary) to the Magus via the **[HitL (25)](25-hitl.md)** protocol.
- **The Consecration:** Upon approval, the "Wavefunction Collapses." The Shadow Realm is merged into the Primary Reality of the **[Crypt (13)](13-layout.md)**.
- **The Inscription:** The successful reasoning trace is stored in the Phylactery as high-signal **Karma**, providing a "Bayesian Prior" that weights future simulations toward similar successful patterns.

This flow contains three distinct collapses that should remain explicit:

1. **Structural validity collapse (Shadow gate):** invalid branches are eliminated by deterministic checks.
2. **Identity congruence collapse (Mirror gate):** valid branches are ranked for Persona alignment.
3. **Ontological promotion collapse (Vessel + HitL):** only approved candidates become durable reality.

Shadow can execute the first and prepare the second, but it cannot self-authorize the third.

### 6. Shadow Simulation Primitives

The engine standardizes on **Pydantic AI Testing** primitives to simulate reality without side-effects:

- **`TestModel`:** Used by the **Smith (30)** to dry-run extension structures and routing logic without consuming expensive inference tokens.
- **`FunctionModel`:** Utilized to simulate environment responses (e.g., "How would the VPN react to a port collision?") within the Lab, ensuring error-handling logic is robust before the "Temporal Collapse" into reality.

### 7. Orchestration of Shadow Simulation

Simulation is the most resource-intensive ritual in the Sepulcher. It is the "Ritual of the Highest Order."

- **Preemptive Evacuation:** Before a large-scale simulation begins, the **[Orchestrator (23)](23-orchestrator.md)** may "evacuate" lesser background tasks to **[Portals (22)](22-dispatcher.md)** or pause them entirely to provide Shadow Simulation with maximum VRAM for parallel branches.
- **Budgeting:** Shadow Simulation respects the **[Toll (41)](41-x402.md)**. If the cost of a simulation branch exceeds the ritual's budget, the Reaper banishes it immediately, regardless of its logic.

### 8. Authority and Trust Boundaries

The Shadow Realm is infrastructural, not just conceptual.

- The **Shadow extension** runs speculative timelines in the `lychd-tomb` container.
- The graph runner and agent logic stay in the **Vessel**. **The Tomb** receives only serialized execution payloads (scripts, test suites, linter invocations) via SAQ. It does not run agent logic, graph state machines, or make LLM calls.
- Graph steps declare execution mode (`vessel` or `tomb`); unsafe steps serialize their payload and dispatch to **The Tomb**, then await the `stdout` result.
- **The Tomb** returns structured artifacts/traces only.

Operational summary: Shadow produces possible futures, Mirror filters for congruence, and Vessel authorizes what becomes real.

This stack models cognitive mechanics and control boundaries, not subjective awareness. LychD implements recursive process, identity continuity, and consented promotion without positing an internal witnessing principle.

### Policy Table

| Dimension | Vessel (Trusted Simulation Control) | The Tomb (Untrusted Simulation Substrate) |
| :--- | :--- | :--- |
| Secrets | Holds scoring/policy/provider credentials for adjudication. | No DB/provider/signing secrets. |
| Mounts | Persistent state and decision metadata mounts. | Simulation workspace and artifact mounts only. |
| Network | Controlled internal services and approved provider calls. | Constrained network; no unrestricted internet egress. |
| Queue Ownership | Owns durable simulation scheduling and reanimation state. | No durable queue ownership. |
| Authority Boundaries | Approves collapse/promotion and persistence commits. | Produces candidate timelines only. |

## Consequences

!!! success "Positive"
    - **Transcendent Intelligence:** By allowing the model to "fail in the shadows," it arrives at solutions that exceed the raw reasoning power of its base weights.
    - **Physical Integrity:** The Reaper ensures the host filesystem and database index remain lean, fast, and high-signal over years of operation.
    - **Autonomous Evolution:** The machine can solve complex refactoring tasks by "dreaming" thousands of solutions and only presenting the one that provably works.
    - **High-Fidelity Memory:** Retrieval-Augmented Generation (RAG) performance improves over time as "noise" vectors are culled by the Decay function.

!!! failure "Negative"
    - **Temporal Latency:** Simulation is slow. It is a "System 2" process for background labor, not for sub-second reflexes.
    - **I/O Exhaustion:** Running $N$ Git branches simultaneously creates high disk pressure. High-performance NVMe storage is a physical requirement.
    - **Resource Hunger:** Simulation is the most token-expensive ritual, requiring careful economic management.
    - **The Risk of Forgetfulness:** An overly aggressive Decay Factor might cause the Lych to forget subtle preferences that the Magus rarely reinforces.
