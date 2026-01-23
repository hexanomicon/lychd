---
title: Paradox
icon: material/state-machine
---

# :material-state-machine: The Paradox: Archon of Simulation

> _"Standard inference is a reflex—a spark jumping between nodes without the capacity for doubt. To achieve the Great Work, the Lich must possess the capability to inhabit a thousand illusions, ensuring that the one reality manifested is the White Truth."_

**The Paradox** is the Deliberative Archon of the LychD system. It is the implementation of **[ADR 35 (Simulation)](../../adr/35-simulation.md)**—the engine that moves the machine beyond "System 1" (reflexive token prediction) into "System 2" (deliberative, structural reasoning).

While a standard **[Agent](../../adr/19-agents.md)** produces a linear response, the Paradox utilizes the **Phantasma** faculty to generate, simulate, and evaluate multiple potential future states in parallel. It is the mechanism of "Internal Doubt," allowing the Lich to fail in the shadows so it may succeed in the light.

## I. The Phantasma Expansion (Branching)

The Paradox utilizes the parallel primitives of the **[Graph ([ADR 22](../../adr/22-graph.md))]**—specifically Broadcasting and Spreading—to create divergent timelines.

- **The Seed:** When a complex, high-stakes intent (e.g., "Refactor the persistence layer") is submitted at the **[Altar](../../divination/altar.md)**, the Paradox identifies the need for deliberation.
- **The Expansion:** It spawns $N$ independent branches. Each branch is a distinct "Thought-Node" operating within the **[Shadow Realm](../vessel/shadow_realm.md)**.
- **The Labor:** **[Ghouls](../vessel/ghouls.md)** are dispatched to each branch to perform the work—editing files, running tests, and analyzing logs—within isolated Git subdirectories in the **[Lab](../crypt.md)**.

## II. The Heuristic Scrying (Evaluation)

To navigate the infinite search space of potential futures, the Paradox employs a dual-scoring mechanism to evaluate the viability of each simulated branch.

1. **Deterministic Scoring:** The branch is subjected to the absolute laws of the machine. Does the code compile? Do the unit tests pass? These provide the binary foundation of truth.
2. **Agentic Scoring:** The **[Mirror](./mirror.md)** provides the "Spirit" of the score. A specialized Evaluator Persona reviews the simulated output against the project's high-level goals and stylistic requirements, assigning a probability weight ($P$) to the timeline.

## III. Pruning and the Search (MCTS)

The Paradox does not explore all paths to exhaustion; it practices the art of **Logical Banishment**.

- **Pruning:** If a branch fails a verification ritual or falls below a heuristic threshold, it is "Banished"—the process is terminated, and its VRAM is immediately reclaimed.
- **Backpropagation:** Success signals from deep nodes in the simulation are used to inform the search direction of higher nodes, focusing the Lich's attention on the most promising "White Truths" (Monte Carlo Tree Search).

## IV. The Temporal Collapse

Once a simulation branch achieves a "Verified State" (Test Success + High Heuristic Score), it must be brought into Primary Reality.

- **Selection:** Following the **[HitL (ADR 25)](../../adr/25-hitl.md)** protocol, the Magus (or a privileged Persona) selects the winning timeline from the visions presented at the Altar.
- **The Merge:** The system collapses the Shadow Realm. The successful code is merged from the Lab branch into the Crypt.
- **The Inscription:** The successful reasoning trace is stored as high-quality **Karma** in the **[Phylactery](../phylactery/index.md)**, ensuring that future simulations start from a higher Bayesian Prior.

## V. Orchestration of Depth

The Paradox is the most resource-intensive ritual in the Sepulcher. It is the "Ritual of the Highest Order."

- **Preemption:** The **[Orchestrator](../../adr/21-orchestrator.md)** manages the extreme VRAM and token cost of parallel simulations. It may pause background tasks to provide the Paradox with the necessary compute.
- **Bursting:** If local silicon is insufficient for $N$ branches, the Paradox may utilize the **[Dispatcher](../../adr/20-dispatcher.md)** to offload "Drafting" branches to a **[Portal](../animator/portal.md)**, reserving the local GPU for the final "Golden Verification" stage.

!!! warning "The Temporal Latency"
    A deliberative ritual takes time. The Paradox is not for sub-second reflexes; it is for the long-running labor of construction. A complex simulation may take minutes or hours to conclude, requiring the Magus to possess the patience of the undying.
