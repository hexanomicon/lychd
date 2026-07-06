---
title: 23. Orchestrator
icon: material/scale-balance
---

# :material-scale-balance: 23. Orchestrator: The Physical Will

!!! abstract "Context and Problem Statement"
    The execution of agentic reasoning is physically constrained by the finite resources of the host hardware, specifically GPU VRAM and thermal limits. In a sovereign environment where multiple cognitive processes (reflexes, rituals, and swarm tasks) compete for these resources, a static infrastructure model leads to systemic instability. Repetitive, uncoordinated reloading of large containerized models causes "Hardware Thrashing," characterized by high-latency state swaps and unrecoverable Out-of-Memory (OOM) failures. Furthermore, background labor often blocks interactive user needs, creating a "Physical Deadlock" where the machine cannot respond to immediate stimuli. A logic layer is required to translate abstract capability intents into concrete hardware state transitions while maintaining systemic equilibrium.

## Requirements

- **The Law of Exclusivity:** Mandatory physical enforcement of the constraint that only one resource-intensive operational state (Coven) may occupy a specific hardware coordinate at any given time.
- **Exclusive vs Shared Authority:** The Orchestrator must distinguish between **exclusive** Soulstones (fully owned — may kill, swap, restart) and **shared** Soulstones (read-only — may route to, but cannot manage lifecycle). A shared Soulstone is one the Magus also exposes to external services outside LychD.
- **The Stasis Receiver:** Capability to interpret the `HardwareTransitionRequired` signal from the **[Dispatcher (22)](22-dispatcher.md)** and convert it into a scheduled priority event.
- **The Tipping Point Algorithm:** Implementation of a weight-based scheduling logic to determine if a requested state change is worth the momentum cost of the current state.
- **The Graceful Drain:** Mandatory signaling to active **[Ghouls (14)](14-workers.md)** to finish their current atomic step and persist state to the **[Phylactery (06)](06-persistence.md)** before a container is banished.
- **Fluid Model Tiering:** Mandatory support for VRAM budgeting, allowing for the downgrading of model scales (e.g., 70B to 8B) to accommodate concurrent sensory and reasoning requirements.
- **Lexical Reservation:** Permanent allocation of a specific VRAM margin for the system's core lexical parser to ensure basic cognitive stability during heavy hardware transitions.
- **Embedding Coven Priority:** During memory ingestion windows, embedding covens must be schedulable with explicit priority so metabolic writes do not starve indefinitely.
- **Host-Native Authority:** Mandatory utilization of the host's init system via the **[Host Reactor (10)](10-privilege.md)** to ensure atomic and verifiable service lifecycles.
- **Strategy Extensibility:** Provision of a pluggable architecture to allow for the injection of specialized orchestration policies (e.g., multi-GPU or energy-aware strategies).

## Considered Options

!!! failure "Option 1: Hardcoded Scheduling Logic"
    Embedding specific VRAM management rules and model priorities directly into the core application logic.

    - **Pros:** Minimal internal latency; simple to develop for a specific hardware target.
    - **Cons:** **Functional Rigidity.** Fails to adapt to evolving hardware substrates (NPUs, multi-node acceleration) or unique user policies. It prevents the system from becoming a platform for diverse cognitive extensions.

!!! failure "Option 2: Network-Layer Model Swappers"
    Utilizing API proxies (e.g., LiteLLM, Paddler) to manage the lifecycles of back-end containers based on traffic.

    - **Pros:** Established toolsets; broad compatibility with standard SDKs.
    - **Cons:** **Substrate Ignorance.** These tools operate at the network layer and remain blind to the host's kernel state, thermal pressure, and init system. This introduces a "Split-Brain" risk where the proxy and the operating system disagree on resource allocation, leading to cascading process failures.

!!! success "Option 3: Strategy-Based Sovereign Orchestration"
    A stateful logic engine utilizing a strategy pattern to bridge abstract cognitive intents with **[Systemd Quadlets (08)](08-containers.md)** and host-native resource management.

    - **Pros:**
        - **Deterministic Safety:** Leverages Systemd `Conflicts=` directives to ensure atomic service transitions at the kernel level.
        - **Hardware Resonance:** Directly monitors physical utilization metrics via **[The Oculus (29)](29-observability.md)** to inform model tiering and "Whim" calculations.
        - **Atomic Handoff:** Implements the "Drain" protocol, ensuring no reasoning task is lobotomized mid-thought during a swap.

## Decision Outcome

**The Orchestrator** is adopted as the system's "Physical Will." It functions as the arbiter of reality, sitting between the cognitive cortex and the containerized body.


### 1. The Tipping Point (Whim Algorithm)

!!! note "The v1 Default Strategy and the Whim"
    The canonical v1 `OrchestrationStrategy` is **Warm-First with Metabolic Accounting**: candidates already warm are preferred, and a swap is chosen only when its metabolic cost (VRAM load time plus context re-processing) is justified. This degenerate, predictable strategy is the shipped default, not a placeholder.

    **The Whim** described below is a *named future strategy*, not the current default. Its constants — Momentum, Inertia Bias, the Tipping Point — become Codex-tunable policy when it lands. The transition ritual (Pause → Drain → Signal → Transmutation → Awakening) is shared by every strategy; only the swap *decision* differs.

Decisions regarding hardware state transitions are not binary; they are calculated using a priority-weighting algorithm called **The Whim**. This algorithm governs the transition from **Manas** (divergent exploration) to **Buddhi** (convergent logic). It enforces **Stillness** (metabolic discipline) to prevent the VRAM thrashing that occurs during uncontrolled parallel branching (excessive *Vṛttis*). Critically, this algorithm respects the **Discipline** of the active Soulstone.

- **Momentum:** The total cost of the current state, calculated as $\text{VRAM Load Time} + \text{Context Re-processing Cost}$.
- **Inertia Bias:** A configurable constant used to prevent thrashing.
    - *Note:* **Weaver (SGLang)** Covens have a naturally higher Inertia Bias because destroying their **Radix Tree** is expensive.
- **Concurrency Check (The Parallel Gate):**
    - Before calculating swap costs, the Orchestrator checks the active Coven's **Discipline**.
    - **If Kinetic/Weaver:** The system checks `Current_Slots_Used < Max_Concurrency`. If true, **NO SWAP IS REQUIRED**. The Orchestrator bypasses the Tipping Point and simply routes the new signal to the active Coven alongside the existing task (Continuous Batching).
    - **If Titan:** The system enforces strict Serial Exclusivity. The Tipping Point calculation proceeds to decide if the new task is important enough to interrupt the current one.
- **The Rule:** A coven swap is only initiated when:
    1. The Coven cannot support the request natively (wrong model), OR
    2. The Coven is at max concurrency, AND $\text{Signal Priority} > \text{Momentum} + \text{Inertia Bias}$.

When the Tipping Point is reached, the Orchestrator executes a coordinated ritual to ensure data integrity and physical stability. This solves the "Lobotomy Risk."

1. **The Pause:** The Orchestrator instructs the **[Ghoul (14)](14-workers.md)** broker to pause the claiming of new jobs associated with the *Current Coven*.
2. **The Drain:** It broadcasts a `SIG_SOFT_STOP` to active workers. The workers complete their *current atomic step* (e.g., finishing a sentence) and reach a safe wait or checkpoint boundary. If that boundary is a **Long Sleep** condition, they persist graph or job state to the Phylactery; an ordinary VRAM swap does not by itself require graph serialization.
3. **The Signal:** Once the drain is confirmed (active worker count = 0), the Orchestrator writes a structured intent file to the shared volume, triggering the **[Host Reactor (10)](10-privilege.md)**.
4. **The Transmutation:** The Host Reactor executes `systemctl start [Target Coven]`. Because of the `Conflicts=` directives in the **[Quadlets (08)](08-containers.md)**, Systemd automatically and cleanly kills the old coven before starting the new one.
5. **The Awakening:** The Orchestrator polls the **[Dispatcher (22)](22-dispatcher.md)** until the new endpoint pulses "Warm." It then unpauses the Ghouls, allowing waiting tasks to continue on the new hardware.

Snapshot note: this drain/swap ritual protects live work during transitions. "Drain" means Ghouls finish their current atomic inference step and stop claiming new jobs — the Agent's cognitive state remains alive in Vessel process memory throughout. Phylactery serialization is reserved for **Long Sleep** scenarios (human approval pending, multi-day waits, or full system reboots). Durable state capture and Btrfs/COW snapshot strategy are governed separately by **[Snapshots (07)](07-snapshots.md)**.

!!! note "Stasis as Parked Vritti: Live vs Durable"
    Stasis is not a separate Magus-initiated ritual. It is the condition of an active cognitive fluctuation (**Vritti**) parked at a recoverable boundary because physical reality is not ready. Two kinds are distinguished not by *whether state was written* but by *who resumes the run*.

    - **Live Stasis:** the run remains a resident in-process loop and resumes itself once the substrate is ready. A checkpoint to the Phylactery may be taken opportunistically, and its absence is lawful — the loop never exited, so nothing needs reanimating.
    - **Durable Stasis:** the run exits the process; a checkpoint to the Phylactery is mandatory, and resumption requires Reanimation.

    The defining axis is the pause locus, not the checkpoint. Hardware transitions default to **Live Stasis with an opportunistic checkpoint** — the implemented GraphRunner behaviour. HitL waits (**[HitL (25)](25-hitl.md)**), Long Sleep, Vessel-lifecycle intents, and deferred peer (A2A) waits are **Durable**. Replay resumes from a persisted boundary; rollback discards or restores the timeline according to Worker, Graph, Simulation, or Snapshot law.

!!! note "Orchestration Boundary"
    The Orchestrator owns physical lifecycle decisions: warm/cold checks, transition plans, drains, leases, runtime-native activation, and host lifecycle requests. It consumes Dispatcher signals and worker drain status, but it does not own privacy routing, cognitive binding, graph schema, queue retry semantics, or whole-system snapshot rollback. Those boundaries may receive better class names later, but the authority split is durable.

    A cold capability whose Animator is not dedicated (`dedicated=False`) lies outside the Orchestrator's authority entirely: the Orchestrator cannot move a runtime it does not own. The **[Dispatcher (22)](22-dispatcher.md)** must exclude such candidates or reject them with `dependency_unavailable`; the transition planner never crashes on a capability it has no power to manifest.

### Soft Activation Contract

Not every transition is a container swap. When the target runtime's Animator unit is already up and its capability carries the `DYNAMIC` lifecycle (**[Dispatcher (22)](22-dispatcher.md)**), the Orchestrator performs a soft activation — an in-runtime load without a Systemd transition. `STATIC`-lifecycle capabilities have no such seam: a reachable endpoint already means `WARM`, so their only path from `COLD` is a hard swap.

- **Activate:** for the `llama.cpp` router, activation is `POST /models/load` against the running router.
- **Phase projection:** the router's reported `status` (`unloaded`, `loading`, `loaded`) maps to the `CapabilityPhase` ladder — `ACTIVATABLE`, `WARMING`, `WARM` respectively — alongside `loaded_model_ids` and `estimated_ready_ms`.
- **Readiness:** the capability is grantable once its model id appears in `loaded_model_ids` and its phase is `WARM`.

!!! note "Implementation status"
    Soft activation is doctrine ahead of code. Current adapters return `False` from `activate_capability`; the `llama.cpp` router lifecycle is modelled but not yet driven. Until it is, every activation resolves to a Hard Swap or a `dependency_unavailable` rejection.

### 2. Model Tiering and Reservation

To maximize hardware utility, the Orchestrator manages a fluid manifest:

- **Tier Selection:** If an intent requires concurrent "Vision + Reasoning" exceeding the VRAM capacity, the Orchestrator instructs the Dispatcher to manifest a lower-tier Reasoning Soulstone (e.g., 8B instead of 70B).
- **Lexical Reservation:** The Orchestrator enforces a permanent 1-2GB margin for the system's **Native Lexicon** (a sub-2B parameter model), ensuring the "Brain Stem" remains resident and operational during all swaps.
- **Ingestion Scheduling:** Background memory augmentation may run in batched ingestion epochs. During these epochs, embedding covens receive bounded priority and must yield to high-priority interactive reflexes.

### 3. Swarm Lease Management

To protect the local Magus from resource exhaustion by the **[Legion (42)](42-legion.md)**, the Orchestrator implements **Workload Tiering**:

- **The Lease:** Incoming peer requests are granted a temporary hardware lease. The Orchestrator marks the active Coven as "Leased" while the swarm task runs.
- **Preemption:** Local user activity — any interactive reflex (voice, text, UI) — is the absolute priority trigger. When detected, the Orchestrator immediately revokes the lease.
    1. The swarm Ghoul receives `SIG_SOFT_STOP`.
    2. It completes its current atomic inference step, persists its recovery boundary (graph or job state as applicable) to the **[Phylactery (06)](06-persistence.md)**, and hibernates.
    3. The GPU is reclaimed for the local reflex.
    4. When the local user is satisfied and the GPU is free, the Orchestrator restores the lease and the swarm Ghoul rehydrates from the serialized state.
- **Ghost Lease Cleanup:** If a swarm task fails or the peer disconnects, the dead lease is swept from the registry on the next Watchdog cycle.

### 4. Watchdog and Recovery

The Orchestrator maintains a "Watchdog" for every active container service. If a hardware state fails to manifest after three attempts or if a model enters an infinite loop consuming VRAM beyond its quota (as reported by **[The Oculus (29)](29-observability.md)**), the Orchestrator issues a hard reset and alerts the Magus via the interface.

## Consequences

!!! success "Positive"
    - **Physical Reliability:** GPU VRAM is never over-committed; transitions occur with 100% kernel-enforced determinism.
    - **Zero-Data Loss:** The "Drain" protocol ensures that active work reaches a safe boundary before its physical substrate is swapped.
    - **Economic Efficiency:** The tiering logic maximizes the utility of local silicon, reducing reliance on expensive cloud fallbacks.
    - **Governance Sovereignty:** The Magus can define complex orchestration policies through extensions, adapting the system to any specific hardware configuration.

!!! failure "Negative"
    - **State Swap Latency:** Swapping remains a heavy physical operation (20–60 seconds), necessitating the batching of rituals to maintain efficiency.
    - **Policy Complexity:** Implementing a custom Orchestration Strategy requires deep technical knowledge of both the application cortex and the host hardware characteristics.
