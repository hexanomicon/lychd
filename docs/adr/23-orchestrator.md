---
title: 23. Orchestrator
icon: material/scale-balance
---

# :material-scale-balance: 23. Orchestrator: The Physical Will

!!! abstract "Context and Problem Statement"
    The execution of agentic reasoning is physically constrained by the finite resources of the host hardware, specifically GPU VRAM and thermal limits. In a sovereign environment where multiple cognitive processes (reflexes, rituals, and swarm tasks) compete for these resources, a static infrastructure model leads to systemic instability. Repetitive, uncoordinated reloading of large containerized models causes "Hardware Thrashing," characterized by high-latency state swaps and unrecoverable Out-of-Memory (OOM) failures. Furthermore, background labor often blocks interactive user needs, creating a "Physical Deadlock" where the machine cannot respond to immediate stimuli. A logic layer is required to translate abstract capability intents into concrete hardware state transitions while maintaining systemic equilibrium.

## Requirements

- **The Law of One Runtime Physical Will:** Every application- or agent-initiated lifecycle
  mutation must be one explicit serialized plan. A host operator retains an explicit Coven-target
  break-glass path outside these workload guarantees.
  The v1 `evict-idle` policy conservatively treats active, dedicated, non-resident runtimes as one
  switching pool; finer hardware-coordinate/group policy is later work.
- **Exclusive vs Shared Authority:** The Orchestrator must distinguish between **exclusive** Soulstones (fully owned — may kill, swap, restart) and **shared** Soulstones (read-only — may route to, but cannot manage lifecycle). A shared Soulstone is one the Magus also exposes to external services outside LychD.
- **The Stasis Receiver:** Capability to interpret the `HardwareTransitionRequired` signal from the **[Dispatcher (22)](22-dispatcher.md)** and convert it into a scheduled priority event.
- **Single Readiness Owner:** Soft activation, hard lifecycle transitions, and final convergence on `WARM` belong only to the Orchestrator. The Dispatcher may request readiness but may not mutate it.
- **The Tipping Point Algorithm:** Implementation of a weight-based scheduling logic to determine if a requested state change is worth the momentum cost of the current state.
- **The Graceful Drain:** Lease admission for every affected Animator must close before waiting:
  the hard-swap evictee set or the whole target Animator for any runtime-started, non-`WARM`
  convergence path. Existing lease holders may finish their current atomic step, but no new grant
  may enter while readiness is being converged; only a dynamic target may require a model-load
  mutation inside that barrier.
- **Fluid Model Tiering:** Mandatory support for VRAM budgeting, allowing for the downgrading of model scales (e.g., 70B to 8B) to accommodate concurrent sensory and reasoning requirements.
- **Lexical Reservation:** Permanent allocation of a specific VRAM margin for the system's core lexical parser to ensure basic cognitive stability during heavy hardware transitions.
- **Embedding Coven Priority:** During memory ingestion windows, embedding covens must be schedulable with explicit priority so metabolic writes do not starve indefinitely.
- **Host-Native Authority:** Host mutation must cross a configurable, narrow `RuntimeActuator`
  boundary. Direct Systemd and mediated **[Host Reactor (10)](10-privilege.md)** delivery with a
  read-only terminal receipt are trusted implementations; the Orchestrator exposes neither shell
  commands nor arbitrary unit names.
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
        - **Deterministic Safety:** Serializes one explicit stop/start plan so no generated unit can add a physical effect outside admission closure and lease drain.
        - **Hardware Resonance:** Directly monitors physical utilization metrics via **[The Oculus (29)](29-observability.md)** to inform model tiering and "Whim" calculations.
        - **Atomic Handoff:** Implements the "Drain" protocol, ensuring no reasoning task is lobotomized mid-thought during a swap.

## Decision Outcome

**The Orchestrator** is adopted as the system's "Physical Will." It functions as the arbiter of reality, sitting between the cognitive cortex and the containerized body.

The ownership invariant is strict: **Dispatcher selects; Orchestrator readies; Animator adapters
perform runtime-specific mechanics; a narrow actuator performs host lifecycle mutation.** A
non-WARM managed capability always crosses this boundary through a handle-free
`HardwareTransitionRequired` for a readying phase; there is no second activation path hidden in dispatch, a workflow,
or a provider binder.


### 1. The Tipping Point (Whim Algorithm)

!!! note "The v1 Default Strategy and the Whim"
    The foundation switch policy is deliberately small: `evict-idle` retains every other active,
    dedicated, non-resident Animator in the plan, drains it, and launches the target. The
    Dispatcher prefers warm candidates before an HTR exists, while a configured priority floor may
    decline a hard swap. There is no claim of measured VRAM or context-reprocessing economics yet.

    **The Whim** described below is a *named future strategy*, not the current default. Its constants — Momentum, Inertia Bias, the Tipping Point — become Codex-tunable policy when it lands. The transition ritual (Pause → Drain → Signal → Transmutation → Awakening) is shared by every strategy; only the swap *decision* differs.

Decisions regarding hardware state transitions are not binary; they are calculated using a priority-weighting algorithm called **The Whim**. The Whim decides when exploration must yield to convergence: it prevents VRAM thrashing by refusing swaps whose cost exceeds their priority. (In the cognitive map: it disciplines Manas in favor of Buddhi — see [The Lich](../sepulcher/lich.md).) Critically, this algorithm respects the **Discipline** of the active Soulstone.

- **Momentum:** The total cost of the current state, calculated as $\text{VRAM Load Time} + \text{Context Re-processing Cost}$.
- **Inertia Bias:** A configurable constant used to prevent thrashing.
    - *Note:* **Radix (SGLang)** Covens have a naturally higher Inertia Bias because destroying their radix tree of cached prefixes is expensive.
- **Concurrency Check (The Parallel Gate):**
    - Before calculating swap costs, the Orchestrator checks the active Coven's **Discipline**.
    - **If Kinetic/Radix:** The system checks `Current_Slots_Used < Max_Concurrency`. If true, **NO SWAP IS REQUIRED**. The Orchestrator bypasses the Tipping Point and simply routes the new signal to the active Coven alongside the existing task (Continuous Batching).
    - **If Titan:** The system enforces strict Serial Exclusivity. The Tipping Point calculation proceeds to decide if the new task is important enough to interrupt the current one.
- **The Rule:** A coven swap is only initiated when:
    1. The Coven cannot support the request natively (wrong model), OR
    2. The Coven is at max concurrency, AND $\text{Signal Priority} > \text{Momentum} + \text{Inertia Bias}$.

When the Tipping Point is reached, the Orchestrator executes a coordinated ritual to ensure data integrity and physical stability. This solves the "Lobotomy Risk."

1. **Close Admission:** The Orchestrator marks the complete affected set `DRAINING` in the
   **LeaseLedger** before it waits. For a hard swap that is every planned evictee; for the
   runtime-started path labelled `SOFT_SWAP` it is the target Animator itself. A concurrent
   Dispatcher grant is rejected rather than racing readiness convergence or an optional dynamic
   mutation.
2. **The Pause:** The Orchestrator pauses Ghoul queue intake and broadcasts a soft-stop signal so active work can reach the end of its current leased step.
3. **The Drain:** It waits until the LeaseLedger reports no live lease on the complete affected set
   — never a queue or job count. If a Long Sleep boundary is crossed, the Graph owns its durable
   checkpoint; an ordinary VRAM swap does not itself require graph serialization.
4. **The Transmutation:** For a hard swap, the Orchestrator submits one validated
   `TransitionIntent` through its injected `RuntimeActuator`; generated Soulstone units contain no
   `Conflicts=` side effects, so that stop/start set is the whole physical mutation. On the
   runtime-started path, only a dynamic capability that is not already `WARMING` calls its
   canonical adapter's runtime-native activation seam. A fixed/static capability, or any target
   already `WARMING`, performs no adapter activation and only converges under the same barrier.
5. **The Awakening or Containment:** The Orchestrator awaits honest `WARM` within the configured
   deadline. Pre-mutation drain/pause failures reopen through `finally`. A raising hard actuator
   leaves the gates closed because the current port cannot attest that its best-effort compensation
   restored the original world. After a terminally completed hard mutation, readiness failure
   submits one typed exact inverse and reopens only after compensation succeeds. A hard
   compensation failure or runtime-started activation/readiness failure likewise leaves queue and
   Animator admission deliberately closed for operator recovery. The path conservatively shares
   one failure fence even when a fixed target performed convergence only; v1 has no trustworthy
   model-level inverse or finer post-failure attestation. The first uncertain outcome also latches
   a manager-wide containment reason: every later
   transition request, including a would-be NO_OP or different target, is rejected until operator
   recovery or process restart.

Snapshot note: this drain/swap ritual protects live work during transitions. "Drain" means Ghouls finish their current atomic inference step and stop claiming new jobs — the Agent's cognitive state remains alive in Vessel process memory throughout. Phylactery serialization is reserved for **Long Sleep** scenarios (human approval pending, multi-day waits, or full system reboots). Durable state capture and Btrfs/COW snapshot strategy are governed separately by **[Snapshots (07)](07-snapshots.md)**.

!!! note "Live vs Durable Stasis"
    Hardware transitions default to **Live Stasis**: the run stays a resident in-process loop with at most an opportunistic checkpoint — the implemented GraphRunner behaviour. The definitions and the normative default table are law in **[Graph (24)](24-graph.md)**; HitL waits, Long Sleep, Vessel-lifecycle intents, and deferred peer (A2A) waits are **Durable** and resume only through Reanimation.

!!! note "Orchestration Boundary"
    The Orchestrator owns physical readiness decisions: transition plans, admission closure, drains, runtime-native activation, hard lifecycle requests, and convergence on WARM. It consumes Dispatcher signals and worker/lease state, but it does not own semantic selection, privacy routing, cognitive binding, graph schema, queue retry semantics, or whole-system snapshot rollback. Those boundaries may receive better class names later, but the authority split is durable.

    A cold capability whose Animator is not dedicated (`dedicated=False`) lies outside the Orchestrator's authority entirely: the Orchestrator cannot move a runtime it does not own. The **[Dispatcher (22)](22-dispatcher.md)** must exclude such candidates or reject them with `dependency_unavailable`; the transition planner never crashes on a capability it has no power to manifest.

!!! note "Lease-truth drain"
    Before each plan, the manager refreshes every lifecycle-managed local Animator with bounded
    probe concurrency. It then replans inside the arbiter after any predecessor finishes, so a
    persistent resident or operator-started unit cannot remain absent from the expected-active and
    eviction view merely because an older in-memory snapshot was stale.

    The v1 switch policy retains every dedicated, non-resident, active Animator in the evict set
    **even when it is leased**. Group/alliance labels do not relax that conservative global pool.
    The manager first closes admission for the full planned set, then waits for
    `LeaseLedger.drained(evict_animators, timeout=drain_timeout_s)`. A run parked awaiting its own
    transition holds no lease, so it never blocks its own swap. Timeout fails loudly and names the
    Animators. Pre-mutation timeout/cancellation reopens admission; after mutation, gates reopen only
    after readiness or successful hard compensation. Because generated units have no hidden conflicts,
    Systemd cannot stop an omitted runtime behind this protocol's back through a generated
    conflict edge. A host operator can still explicitly start or stop a Coven target as a
    break-glass action; that bypass is outside the application runtime protocol and assumes
    operator responsibility.

### Runtime-Started Convergence (`SOFT_SWAP` Plan Label)

Not every transition is a container swap, and not every plan labelled `SOFT_SWAP` invokes a model
load. When any target Animator runtime is already started but the requested capability is not yet
`WARM`, the planner chooses this target-only drain/convergence path. The label means "no Systemd
transition is needed"; it does not mean the capability is dynamic.

The manager pauses claims, closes admission for the entire target Animator, and drains all of its
leases before proceeding. If the capability carries `is_dynamic=True`
(**[Dispatcher (22)](22-dispatcher.md)**) and is neither `WARM` nor already `WARMING`, the canonical
adapter performs its runtime-native activation. A bounded router load may unload another model,
which is why the barrier is mandatory. For a fixed/static capability, and for any capability
already `WARMING`, the manager skips adapter activation and only waits for honest convergence.

- **Activate:** for the `llama.cpp` router, activation is `POST /models/load` against the running router.
- **Phase projection:** the router's reported `status` (`unloaded`, `loading`, `loaded`) maps to the `CapabilityPhase` ladder — `ACTIVATABLE`, `WARMING`, `WARM` respectively — alongside `loaded_model_ids` and `estimated_ready_ms`.
- **Readiness:** the capability is grantable once its model id appears in `loaded_model_ids` and its phase is `WARM`.
- **One deadline:** `warmup_timeout_s` creates one monotonic deadline for the entire `await_warm`
  call. An adapter's `estimated_ready_ms` may seed the first sleep, but that sleep and every poll
  interval are capped to the remaining budget; the estimate cannot double the configured timeout.
- **Failure containment:** v1 does not record enough prior model-level state or post-failure proof
  to distinguish a safely stalled fixed warm-up from an uncertain dynamic load. Any activation or
  `WARM` convergence failure on this path therefore leaves the target Animator and queue claim gate
  closed.

The llama.cpp router adapter implements the dynamic activation seam. Fixed OpenAI-compatible and
generic adapters are not called for activation; their already-started targets use convergence only
and must become `WARM` within the same absolute deadline.

### Host Mutation Port and Privilege Boundary

The domain depends only on `RuntimeActuator.apply(TransitionIntent)`. The frozen intent permits a
transition id, forward/compensation operation, optional completed-forward `rollback_of` reference,
configuration-generation digest, canonical target, evict/launch Animator ids, and the expected
active set. It forbids extra fields and has no command, unit name, filesystem path, environment, or
generic payload surface. Host compensation must exactly invert its referenced completed forward
record; the operation label cannot authorize an arbitrary second plan.

`[orchestration.switching].actuator` selects `systemd` or `host-reactor` at composition:

```toml
[orchestration.switching]
actuator = "host-reactor"
```

`host_reactor_dir` defaults to the XDG-derived LychD Reactor inbox and may be overridden with an
absolute operator-owned path whose final segment remains `inbox`. Its sibling journal is derived;
the configured stasis root cannot overlap either directory, and `lychd init` provisions the
validated paths. These paths are resolved at composition and never copied into a
`TransitionIntent`.

- **`host-reactor` (caged default):** writes one `0600` JSON intent using sibling-temp creation,
  file and directory `fsync`, and atomic no-overwrite publication into an owner-only inbox. Bind
  generates `lychd-reactor.path` and the host-side `lychd reactor consume` oneshot. The consumer
  claims before parsing through a no-follow bounded descriptor read, then validates the typed
  schema/set invariants, filename/transition identity, configuration digest, configured switch
  plan, expected user-unit active set, and host registry mappings before acting. It retains
  processing, completed, declined, or rejected records in a host-owned journal; an existing journal
  ID suppresses duplicate execution. The Vessel mounts that journal read-only and holds the manager
  barrier until its transition receives a terminal completed/declined/rejected record. A stale
  configuration, policy, or expected-active precondition is journaled as `.declined.json` before
  any effect and surfaces as typed `RuntimePreconditionError`; the manager can safely reopen the
  forward barrier without global containment. An uncertain effect failure is `.rejected.json` and
  remains fail-closed.
- **`systemd` (explicit uncaged mode):** resolves canonical local Soulstones through registry truth
  and applies the complete stop/start set to their generated user units in process.

The intent channel remains unidirectional and the journal is not a generic reply protocol. The
Vessel has no journal write authority and observes only transition-correlated terminal filenames.
`reactor_ack_timeout_s` bounds claim: an unclaimed intent is retracted and `fsync`ed before failure
reopens admission. Once claimed, the manager (and a cancellation path) waits through a terminal
record even beyond that deadline. Startup likewise stays closed while pending/processing work
exists. After a completed physical receipt, ordinary capability probes and bounded `await_warm`
remain the separate readiness truth. The filesystem handoff is local-UID authority, not a signature
or network authentication protocol.

!!! warning "Safe decline can still require operator reconciliation"
    The caged manager derives `expected_active_animators` from its capability-readiness projection,
    while the host stale-world check uses user-Systemd activity. A unit can therefore be hung yet
    still `active` to Systemd and absent from the manager's expected set. The host safely declines
    that transition before effects, so admission reopens and containment does not latch, but the
    mismatch is not self-healing: repeated retries may decline again until the operator reconciles
    the runtime or stops the hung unit before retrying.

The structured actuator seam, both implementations, and the Host Reactor consumer/outcome journal
are part of the foundation. The generated path watches both pending and processing work, and the
consumer resumes a crash-surviving intent only when observed user-unit state equals an exact ordered
action prefix; it then applies the suffix or compensates completed prefix/suffix work on failure.
Non-prefix external mutation and failed compensation are rejected rather than guessed. A per-effect
transaction log, general repair of arbitrary physical states, and signature/remote-authentication
policy remain later work. They extend this narrow port; they do not move subprocess or privilege
policy back into the Orchestrator domain.

### 2. Model Tiering and Reservation

Future resource-aware strategies will manage a fluid manifest:

- **Tier Selection:** If an intent requires concurrent "Vision + Reasoning" exceeding the VRAM capacity, the Orchestrator instructs the Dispatcher to manifest a lower-tier Reasoning Soulstone (e.g., 8B instead of 70B).
- **Lexical Reservation:** The Orchestrator enforces a permanent 1-2GB margin for the system's **Native Lexicon** (a sub-2B parameter model), ensuring the "Brain Stem" remains resident and operational during all swaps.
- **Ingestion Scheduling:** Background memory augmentation may run in batched ingestion epochs. During these epochs, embedding covens receive bounded priority and must yield to high-priority interactive reflexes.

### 3. Swarm Lease Management

To protect the local Magus from resource exhaustion by the **[Legion (42)](42-legion.md)**, the Orchestrator reserves **Workload Tiering** as a policy target:

- **The Lease:** Incoming peer requests are granted a temporary hardware lease. The Orchestrator marks the active Coven as "Leased" while the swarm task runs.
- **Preemption:** Local user activity — any interactive reflex (voice, text, UI) — is the absolute priority trigger. When detected, the Orchestrator immediately revokes the lease.
    1. The swarm Ghoul receives `SIG_SOFT_STOP`.
    2. It completes its current atomic inference step, persists its recovery boundary (graph or job state as applicable) to the **[Phylactery (06)](06-persistence.md)**, and hibernates.
    3. The GPU is reclaimed for the local reflex.
    4. When the local user is satisfied and the GPU is free, the Orchestrator restores the lease and the swarm Ghoul rehydrates from the serialized state.
- **Ghost Lease Cleanup:** If a swarm task fails or the peer disconnects, the dead lease is swept from the registry on the next Watchdog cycle.

### 4. Watchdog and Recovery

The planned Orchestrator Watchdog will supervise active container services. If a hardware state
fails to manifest after a bounded number of attempts or a model consumes resources beyond policy
(as reported by **[The Oculus (29)](29-observability.md)**), it may request a hard reset and alert
the Magus. The foundation currently fails bounded warm convergence loudly; it does not yet run this
autonomous recovery loop.

!!! note "Implemented foundation vs later policy"
    The implemented foundation includes one transition arbiter, fresh in-arbiter replanning,
    configurable hard-swap priority, admission-closed lease drain, leased-evictee retention, the
    structured actuator with configurable Systemd/Host Reactor implementations, the generated Host
    Reactor consumer, read-only terminal-receipt/cancellation/startup fence, exact-action-prefix
    crash recovery, typed exact hard-readiness compensation, same-Animator lease-safe llama.cpp soft
    activation, one-deadline bounded warm convergence, and fail-closed uncertain outcomes. Metabolic
    Whim accounting, model-tier substitution, lexical VRAM reservation, swarm preemption, the
    watchdog, a trustworthy model-level soft inverse, a general physical transaction log/repair
    engine, and remote-authentication policy remain later strategies and recovery work.

    Fail-closed containment is process-lifetime state exposed as
    `OrchestratorManager.containment_reason`. It is not cleared by a later request or by the arbiter
    releasing its serialization slot; this prevents a manual/API transition from unpausing the
    global broker after an uncertain physical outcome.

## Consequences

!!! success "Positive"
    - **Physical Reliability:** One application-runtime readiness/effect owner and conflict-free
      generated units remove hidden automatic stop paths outside the plan.
    - **Lease Honesty:** Admission closure and drain prevent known active grants from being evicted mid-step; durable graph guarantees remain the Graph/Phylactery's responsibility.
    - **Containment Honesty:** An uncertain mutation cannot be papered over by a later NO_OP or
      different API transition; the process rejects every request until recovery/restart.
    - **Configurable Authority:** The same structured transition can use direct user-systemd
      actuation or mediated Host Reactor delivery without changing domain policy.
    - **Policy Growth:** Resource-aware strategies can extend a stable plan/drain/actuate/converge sequence without acquiring a second physical will.

!!! failure "Negative"
    - **State Swap Latency:** Swapping remains a heavy physical operation (20–60 seconds), necessitating the batching of rituals to maintain efficiency.
    - **Policy Complexity:** Implementing a custom Orchestration Strategy requires deep technical knowledge of both the application cortex and the host hardware characteristics.
