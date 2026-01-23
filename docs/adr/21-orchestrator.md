---
title: 21. Orchestrator
icon: material/scale-balance
---

# :material-scale-balance: 21. Orchestrator: The Sovereign Will

!!! abstract "Context and Problem Statement"
    LychD operates as a sovereign system on dedicated hardware where multiple processes compete for limited resources, specifically GPU VRAM.. The system infrastructure is organized into mutually exclusive **[Covens (08)](08-containers.md)** designed to optimize the machine's state for specific cognitive tasks. Without a central arbiter of physical reality, the system is prone to "Hardware Thrashing"—the high-latency, repetitive reloading of containerized models—or "Deadlock," where background rituals block interactive user reflexes. A logic layer is required to translate abstract capability requirements from the **[Dispatcher (20)](20-dispatcher.md)** into concrete **Systemd** state transitions while maintaining the stability of the local iron.

## Requirements

- **The Law of Exclusivity:** Mandatory physical enforcement of the constraint that only one resource-intensive coven may occupy a specific hardware coordinate (GPU) at any given time.
- **Capability-Driven Manifestation:** Ability to receive a `CapabilitySet` and identify the optimal physical state transition to fulfill the reasoning intent.
- **Fluid Model Tiering:** Mandatory support for VRAM budgeting; the Orchestrator must be able to downgrade model tiers (e.g., 70B to 8B) to allow multiple concurrent senses to inhabit memory.
- **Strategy Extensibility:** Mandatory support for pluggable orchestration logic; the "how" of scheduling must be swappable via the **[Extension Protocol (05)](05-extensions.md)**.
- **Tunable Physics Weights:** Exposure of the "Tipping Point" logic—Inertia Bias and Priority Multipliers—to the Magus via the **[Codex (12)](12-configuration.md)**.
- **Host-Native Authority:** Utilization of the host’s init system (`systemctl --user`) to ensure atomic, reliable service lifecycles and recovery.
- **Swarm Workload Pooling:** Mandatory implementation of separate pools for local **Reflexes** and remote **Swarm Rituals** to prevent external A2A requests from overrunning local resources.
- **Deadlock & Recursion Safety:** Implementation of "Watchdog" timers, task leases, and Hop-Limits (TTL) to prevent circular waits in decentralized collaboration.
- **Sovereign Override:** Provision of a "Manual Flip" capability at the Altar to allow the Magus to physically force state transitions or purge the queue.

## Considered Options

!!! failure "Option 1: Hardcoded Scheduling Logic"
    Embedding the VRAM management rules directly into the Core kernel.
    - **Cons:** **Rigidity.** As hardware evolves (e.g., Multi-GPU, NPU, or specialized AI accelerators), a hardcoded Orchestrator becomes a bottleneck. It prevents the Magus from implementing specialized "Sovereign Policies" for different environments (e.g., battery-saving vs. high-performance).

!!! failure "Option 2: Proxy-Level Model Swappers (llama-swap / Paddler)"
    Using an API-layer proxy to manage container lifecycles.
    - **Cons:** **Substrate Ignorance.** Tools operating at the network layer are blind to the host's init system and kernel state. This introduces a "Split-Brain" risk where the proxy and the OS disagree on hardware allocation, leading to unrecoverable OOM failures.

!!! success "Option 3: Strategy-Based Sovereign Orchestration"
    A state machine utilizing a **Strategy Pattern** to bridge abstract intent with Systemd Quadlets and host-native resource management.
    - **Pros:**
        - **Modular Governance:** Allows extensions to register new `OrchestrationStrategy` implementations (e.g., a "Multi-GPU" strategy).
        - **Deterministic Safety:** Leverages Systemd `Conflicts=` logic for atomic service transitions.
        - **Hardware Resonance:** Directly monitors VRAM pressure to inform model tiering decisions.

## Decision Outcome

The Orchestrator is adopted as the **Sovereign logic layer** sitting between the **[Graph (22)](22-graph.md)** and the physical **Runes**. It acts as the "Will" of the Daemon, translating logical desire into physical manifestation.

### 1. The Pluggable Policy Engine (Strategy Pattern)

The Orchestrator delegates state decisions to a registered `OrchestrationStrategy`. This allows the machine's "Will" to be upgraded without core modifications:

- **Default Strategy (The Tipping Point):** Uses the "Physics Weights" defined in the Codex to calculate the scales of intent. A swap only occurs when `Whim > Momentum + Inertia_Bias`.
- **Extension Hook:** Extensions can register custom strategies (e.g., `PriorityQueueStrategy`, `BatteryAwareStrategy`) via the `context.add_orchestration_strategy()` hook.
- **Momentum & Whim:**
    - **Momentum:** sum of `Stop Delay` + `Reload Delay` + `Context Reprocessing Cost`.
    - **Whim:** `Intent Priority * Context Multiplier` (e.g., Speech Reflex = 10x, Training Ritual = 1x).

### 2. The Rite of State Transition

When the active strategy tips the scales, the Orchestrator executes a coordinated five-step ritual:

1. **The Drain:** The Orchestrator signals active **[Ghouls (14)](14-workers.md)** to complete their current atomic task and persist their state to the **[Phylactery](../sepulcher/phylactery/index.md)**. This prevents "Soul Fragmentation" where a cognitive process is terminated in mid-execution.
1. **The Pause:** Signals the  to suspend job-claiming for the current coven.
2. **The Signal:** Writes a structured `SWAP_COVEN_INTENT` to the **[Host Reactor (10)](10-privilege.md)**.
3. **The Transmutation:** The Host Reactor issues the stop/start commands. Systemd gracefully banishes the old coven before the new Runes are summoned.
4. **The Verification:** Pings the new endpoints via the Dispatcher to ensure the models are "Warm."
5. **The Awakening:** Unpauses the worker queues and releases the hibernating **[Graph (22)](22-graph.md)** nodes.

### 3. Model Tiering and Lexical Reservation

The Orchestrator maintains a **Fluid Hardware Manifest** to maximize GPU utility:

- **Tier Selection:** If a task demands "Vision + Reasoning" exceeding capacity, the Orchestrator instructs the Dispatcher to provide a lower-tier Reasoning Soulstone (e.g., 8B) to ensure the Vision sense remains resident.
- **Lexical Reservation:** The Orchestrator enforces a permanent 1-2GB "VRAM Reserve" for the **Native Lexicon** (SmolLM), ensuring the system's "Brain Stem" never participates in swaps.

### 4. Swarm Workload Pooling (A2A Ward)

To protect local iron from the swarm, the Orchestrator implements **Workload Tiering**:

- **The Remote Pool:** Incoming **[A2A (23)](23-a2a.md)** requests are placed in a restricted queue.
- **Resource Leases:** Swarm tasks are granted a **Lease**. If a local user **Reflex** requires the VRAM, the Orchestrator revokes the lease, persists the swarm state via **`BaseStatePersistence`**, and reclaims the GPU for the Magus.
- **Recursion Safety:** Every request includes a `TTL` (Hop-Limit) to prevent cross-node VRAM deadlocks.

### 5. Watchdog and Deadlock Prevention

- **Task Watchdog:** Every background Ghoul operates under a watchdog timer. If a ritual hangs or exceeds its VRAM quota, the Orchestrator issues a `SIGTERM` and enters **Stasis Mode**.
- **Stasis Recovery:** If a coven fails to manifest after three attempts, the Orchestrator halts all queues and alerts the Magus via the Altar.

### 6. Scrying at the Altar

The Orchestrator's internal balance is streamed to **[The Altar (15)](15-frontend.md)**:

- **The Scales:** A real-time visualization of current `Whim` vs. `Momentum`.
- **Manual Flip:** A privileged override allowing the Magus to physically force a Coven manifestation or purge the queue.

## Consequences

!!! success "Positive"
    - **Physical Reliability:** VRAM is never over-committed; the system transitions between valid hardware states with 100% determinism.
    - **Economic Efficiency:** The "Tiering" logic maximizes local GPU utility, reducing cloud fallback costs.
    - **Governance Sovereignty:** The Magus can define complex orchestration policies through extensions, adapting the system to any hardware substrate.

!!! failure "Negative"
    - **State Swap Latency:** Swapping remains a heavy operation (20-60s), requiring the user to batch rituals.
    - **Strategy Complexity:** Implementing a custom `OrchestrationStrategy` requires deep knowledge of both Pydantic AI and host hardware characteristics.
