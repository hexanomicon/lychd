---
title: 23. Orchestrator
icon: material/scale-balance
---

# :material-scale-balance: 23. Orchestrator

!!! abstract "Context and Problem Statement"
    The execution of agentic reasoning is physically constrained by the finite resources of the host hardware, specifically GPU VRAM and thermal limits. In a sovereign environment where multiple cognitive processes (reflexes, rituals, and swarm tasks) compete for these resources, a static infrastructure model leads to systemic instability. Repetitive, uncoordinated reloading of large containerized models causes "Hardware Thrashing," characterized by high-latency state swaps and unrecoverable Out-of-Memory (OOM) failures. Furthermore, background labor often blocks interactive user needs, creating a "Physical Deadlock" where the machine cannot respond to immediate stimuli. A logic layer is required to translate abstract capability intents into concrete hardware state transitions while maintaining systemic equilibrium.

## Requirements

- **One Temporal Will, One Physical Executor:** Every application- or agent-initiated lifecycle
  mutation must pass through one serialized Orchestrator decision and one systemd transaction.
  The Orchestrator owns *when*: the requested transition-target capability, priority, affected-set
  computation, admission closure, drain, stale-world validation, readiness, and compensation.
  Systemd owns *how*: the physical stop/switch/start implied by the generated Animator-target graph.
- **Declared Conflict Closure:** The Orchestrator must derive the exact active conflict
  neighborhood from the same Soulstone `conflict_domains` intent binding compiled. An omitted
  declaration on a dedicated non-resident becomes the conservative `default-exclusive` wildcard;
  an explicit empty list alone declares coexistence. Coven membership never substitutes for this
  graph. Until Animator runtime activity has a canonical state port independent of capabilities,
  every Soulstone must synthesize at least one `CapabilitySpec`; bind and registry load reject an
  unadvertised Soulstone rather than let host and planner truth diverge.
- **Attested Effect:** Before asking systemd to act, the runtime actuator must prove that the loaded
  runtime graph is the exact Scribe-owned projection of current registry truth: no stale
  Animator/Coven target, substituted source, altered managed relation, unauthorized drop-in, or
  pending reload may pass. The mediated Host Reactor must separately reject a stale intent
  configuration digest. A host operator retains explicit Animator/Coven-target break-glass paths
  outside these workload guarantees.
- **Exclusive vs Shared Authority:** The Orchestrator must distinguish between **exclusive** Soulstones (fully owned — may kill, swap, restart) and **shared** Soulstones (read-only — may route to, but cannot manage lifecycle). A shared Soulstone is one the Magus also exposes to external services outside LychD.
- **The Stasis Receiver:** Capability to interpret the `HardwareTransitionRequired` signal from the **[Dispatcher (22)](22-dispatcher.md)** and convert it into a scheduled priority event.
- **Single Readiness Owner:** Soft activation, hard lifecycle transitions, and final convergence on `WARM` belong only to the Orchestrator. The Dispatcher may request readiness but may not mutate it.
- **The Tipping Point Algorithm:** Implementation of a weight-based scheduling logic to determine if a requested state change is worth the momentum cost of the current state.
- **The Graceful Drain:** Lease admission for every affected Animator must close before waiting:
  the exact active conflict-neighbor set or the whole target Animator for any runtime-started,
  non-`WARM` convergence path. Existing lease holders may finish their current atomic step, but no
  new grant may enter while readiness is being converged; only a dynamic target may require a
  model-load mutation inside that barrier.
- **Fluid Model Tiering:** Mandatory support for VRAM budgeting, allowing for the downgrading of model scales (e.g., 70B to 8B) to accommodate concurrent sensory and reasoning requirements.
- **Lexical Reservation:** Permanent allocation of a specific VRAM margin for the system's core lexical parser to ensure basic cognitive stability during heavy hardware transitions.
- **Embedding Coven Priority:** During memory ingestion windows, embedding covens must be schedulable with explicit priority so metabolic writes do not starve indefinitely.
- **Delegated Provider Capacity:** Provider-backed delegated-agent work must be admitted against
  configured concurrency, quota, cooldown, automation, and spending ceilings without changing
  Graph semantics or evading provider limits.
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
        - **Deterministic Safety:** Serializes one transition decision, closes and drains the exact
          declared conflict set, and delegates one attested physical transaction to systemd.
        - **Hardware Resonance:** Directly monitors physical utilization metrics via **[The Oculus (29)](29-observability.md)** to inform model tiering and "Whim" calculations.
        - **Atomic Handoff:** Implements the "Drain" protocol, ensuring no reasoning task is lobotomized mid-thought during a swap.

## Decision Outcome

**The Orchestrator** is adopted as the system's "Physical Will." It functions as the arbiter of reality, sitting between the cognitive cortex and the containerized body.

The ownership invariant is strict: **Dispatcher selects; Orchestrator decides and readies;
Animator adapters perform runtime-specific mechanics; an attesting actuator asks systemd to
execute host lifecycle mutation.** A non-WARM managed capability always crosses this boundary
through a handle-free `HardwareTransitionRequired` for a readying phase; there is no second
activation path hidden in dispatch, a workflow, or a provider binder.

For a hard transition, the Orchestrator's decision owns the requested capability identity,
priority, exact active conflict-neighbor set, admission and queue barriers, lease drain, stale-world
validation, readiness, and compensation. It does not spell a sequential service stop/start
program. Binding has already compiled the declared topology into per-Animator systemd targets;
after the actuator attests that loaded graph, systemd executes the physical transaction.


### 1. The Tipping Point (Whim Algorithm)

!!! note "The v1 Default Strategy and the Whim"
    The default `declared-conflicts` solver retains `evict-idle` only as a compatibility alias; it
    does not revive the old all-active algorithm. This deliberately small policy recomputes the
    graph from validated Rune intent, retains the target's active neighbors in the affected set,
    drains them, and requests the target transaction. Runes that
    omit `conflict_domains` on dedicated non-residents receive the `default-exclusive` unknown
    wildcard. It conflicts with every dedicated non-resident whose effective domain set is
    non-empty, so older configurations retain their global switching pool and partial migration
    cannot silently widen coexistence. Explicit `[]` alone opts a Soulstone into coexistence. The
    Dispatcher prefers warm candidates before an HTR exists, while a configured priority floor may
    decline a hard swap. There is no claim of measured VRAM or context-reprocessing economics yet.

    **The Whim** described below is a *named future strategy*, not the current default. Its constants — Momentum, Inertia Bias, the Tipping Point — become Codex-tunable policy when it lands. The transition ritual (Pause → Drain → Signal → Transmutation → Awakening) is shared by every strategy; only the swap *decision* differs.

Decisions regarding hardware state transitions are not binary; they are calculated using a
priority-weighting algorithm called **The Whim**. The Whim decides when exploration must yield to
convergence: it prevents VRAM thrashing by refusing swaps whose cost exceeds their priority. In the
cognitive map, it disciplines the Call in favor of the Blade—see [The
Lich](../sepulcher/lich/index.md). Critically, this algorithm respects the **Discipline** of the
active Soulstone.

- **Momentum:** The total cost of the current state, calculated as $\text{VRAM Load Time} + \text{Context Re-processing Cost}$.
- **Inertia Bias:** A configurable constant used to prevent thrashing.
    - *Note:* **Radix (SGLang)** Animators have a naturally higher Inertia Bias because destroying
      their radix tree of cached prefixes is expensive.
- **Concurrency Check (The Parallel Gate):**
    - Before calculating swap costs, the Orchestrator checks the active Animator's **Discipline**.
    - **If Kinetic/Radix:** The system checks `Current_Slots_Used < Max_Concurrency`. If true, **NO
      SWAP IS REQUIRED**. The Orchestrator bypasses the Tipping Point and admits the new signal to
      the active Animator alongside the existing task (Continuous Batching).
    - **If Titan:** The system enforces strict Serial Exclusivity. The Tipping Point calculation proceeds to decide if the new task is important enough to interrupt the current one.
- **The Rule:** A physical transition is considered only when:
    1. The active Animator cannot support the request natively (wrong model), OR
    2. It is at max concurrency, AND $\text{Signal Priority} > \text{Momentum} + \text{Inertia Bias}$.

When the Tipping Point is reached, the Orchestrator executes a coordinated ritual to ensure data integrity and physical stability. This solves the "Lobotomy Risk."

1. **Recompute and Close:** Inside the serialized arbiter, the Orchestrator refreshes the managed
   world and recomputes the target's exact active conflict-neighbor set from validated Rune intent.
   It marks that complete set `DRAINING` in the **LeaseLedger** before it waits. On the
   runtime-started path labelled `SOFT_SWAP`, the affected set is the target Animator itself.
   A concurrent Dispatcher grant is rejected rather than racing readiness convergence or an
   optional dynamic mutation.
2. **The Pause:** The Orchestrator pauses Ghoul queue intake and broadcasts a soft-stop signal so active work can reach the end of its current leased step.
3. **The Drain:** It waits until the LeaseLedger reports no live lease on the complete affected set
   — never a queue or job count. If a Long Sleep boundary is crossed, the Graph owns its durable
   checkpoint; an ordinary VRAM swap does not itself require graph serialization.
4. **The Seal:** Immediately before mutation, the Orchestrator validates that the observed active
   set has not gone stale. The mediated Host Reactor separately validates the intent's
   configuration digest against current registry truth. The actuator recompiles the graph, binds
   every managed runtime unit to the validated Scribe ownership receipt, enumerates the installed
   and loaded LychD target namespace, and attests target/service/Coven relations, source, unit-file
   state, reload state, and absence of drop-ins. Any mismatch is a typed no-effect decline.
5. **The Transmutation:** For a hard swap, the Orchestrator submits one validated
   `TransitionIntent` through its injected `RuntimeActuator`. The actuator starts the requested
   Animator target once; systemd computes and executes the complete stop-before-start transaction
   from the compiled graph. On the runtime-started path, only a dynamic capability that is not
   already `WARMING` calls its canonical adapter's runtime-native activation seam. A fixed/static
   capability, or any target already `WARMING`, performs no adapter activation and only converges
   under the same barrier.
6. **The Awakening or Containment:** The Orchestrator awaits honest `WARM` within the configured
   deadline. Pre-mutation drain/pause failures and attestation declines reopen through `finally`.
   After a completed hard transaction, readiness failure requests one compensation transaction
   containing the exact typed inverse. From the settled world, the actuator either starts the
   captured prior compatible target set or stops extra launched targets, waits for relevant jobs,
   and trusts final target-and-service observation rather than a client return code. Gates reopen
   only after the exact prior world is proved. Caller cancellation after physical submission is
   likewise fenced through settlement and restoration; a typed restored-cancellation preserves
   cancellation semantics while allowing the barrier to reopen. A transaction whose outcome cannot
   be established, a failed compensation, or runtime-started activation/readiness failure leaves
   queue and Animator admission closed for operator recovery. The first uncertain outcome also
   latches a manager-wide containment reason: every later transition request, including a would-be
   NO_OP or different target, is rejected. A direct process-local latch disappears on Vessel
   restart without proving the physical world safe. In mediated mode, the durable `.contained`
   marker survives application restart and still requires explicit operator recovery.

Every admitted transition owns one request identity and an observed phase ladder across
`requested`, arbitration/drain/actuation/readiness, compensation when required, and a truthful
terminal phase. Run-origin transitions retain the Graph run and occurrence identity; physical and
compensation requests receive separate correlation identities when those acts are submitted. The
current manager publishes these observations to both the run event stream and a bounded
process-local latest-value journal used by Nexus. That journal is diagnostic projection only: it
is not the Host Reactor journal, a durable transition history, or proof that an intermediate phase
survives process death.

Snapshot note: this drain/swap ritual protects live work during transitions. "Drain" means Ghouls finish their current atomic inference step and stop claiming new jobs — the Agent's cognitive state remains alive in Vessel process memory throughout. Phylactery serialization is reserved for **Long Sleep** scenarios (human approval pending, multi-day waits, or full system reboots). Durable state capture and Btrfs/COW snapshot strategy are governed separately by **[Snapshots (07)](07-snapshots.md)**.

!!! note "Live vs Durable Stasis"
    Hardware transitions default to **Live Stasis**: the run stays a resident in-process loop with at most an opportunistic checkpoint — the implemented GraphRunner behaviour. The definitions and the normative default table are law in **[Graph (24)](24-graph.md)**; HitL waits, Long Sleep, Vessel-lifecycle intents, and deferred peer (A2A) waits are **Durable** and resume only through Reanimation.

!!! note "Orchestration Boundary"
    The Orchestrator owns physical readiness decisions: transition target and priority,
    affected-set computation, admission closure, drains, stale-world validation, runtime-native
    activation, hard lifecycle requests, readiness, and compensation. It consumes Dispatcher
    signals and worker/lease state, but it does not own semantic provider selection, privacy
    routing, cognitive binding, graph schema, queue retry semantics, physical transaction
    expansion, or whole-system snapshot rollback. Systemd expands the attested hard target request
    into stop/switch/start effects. Those boundaries may receive better class names later, but the
    authority split is durable.

    A cold capability whose Animator is not dedicated (`dedicated=False`) lies outside the Orchestrator's authority entirely: the Orchestrator cannot move a runtime it does not own. The **[Dispatcher (22)](22-dispatcher.md)** must exclude such candidates or reject them with `dependency_unavailable`; the transition planner never crashes on a capability it has no power to manifest.

!!! note "Lease-truth drain"
    Before each plan, the manager refreshes every lifecycle-managed local Animator with bounded
    probe concurrency. It then replans inside the arbiter after any predecessor finishes, so a
    persistent resident or operator-started unit cannot remain absent from the expected-active and
    eviction view merely because an older in-memory snapshot was stale.

    The switch policy retains every active neighbor in the target's declared conflict neighborhood
    **even when it is leased**. Group/alliance labels neither widen nor relax that set. Omitted
    conflict domains on dedicated non-residents map to the `default-exclusive` wildcard, so an
    omitted Rune conflicts with every non-empty managed declaration; explicit `[]` is the
    operator's deliberate coexistence assertion. Persistent residents and shared runtimes are
    rejected from non-empty conflict participation at bind.

    The manager first closes admission for the full planned set, then waits for
    `LeaseLedger.drained(evict_animators, timeout=drain_timeout_s)`. A run parked awaiting its own
    transition holds no lease, so it never blocks its own swap. Timeout fails loudly and names the
    Animators. Pre-mutation timeout/cancellation reopens admission; after mutation, gates reopen
    only after readiness or successful hard compensation.

    Generated conflicts are safe only because they are not hidden from policy: bind and the
    Orchestrator derive the same graph, and the actuator binds the loaded graph to the exact
    Scribe-owned unit set and sources immediately before the one target transaction. A host operator
    can still explicitly start or stop an Animator or Coven target as a break-glass action; that
    bypass is outside the application runtime protocol and assumes operator responsibility.

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

- **Activate:** the `llama.cpp` router uses `POST /models/load`; ExLlamaV3 uses the official
  TabbyAPI `POST /v1/model/load` endpoint against its running server.
- **Phase projection:** llama.cpp router status and TabbyAPI's health/inventory/current-model
  contract map onto `ACTIVATABLE`, `WARMING`, and `WARM`. In particular, a healthy TabbyAPI with
  `GET /v1/model` reporting no loaded model is `ACTIVATABLE`, never `WARM`.
- **Streaming ambiguity:** TabbyAPI emits multiple SSE load stages and continues a detached load
  after client disconnect. Its adapter consumes through EOF and verifies `GET /v1/model`; timeout
  or disconnect stays `WARMING` while the observer is alive and converges only through bounded
  polling. If the observer ends without a trustworthy terminal event and no active model can be
  verified, the capability becomes contained `ERROR`; restarting the caged Vessel resets Tabby and
  the in-memory load epoch together.
- **Authority and containment:** TabbyAPI data and admin calls use separate keys from one
  Vessel/Tabby-only Podman secret. The Tabby unit has `BindsTo=lychd-vessel.service`, so a detached
  load cannot survive loss of the process that owns admission and mutation authority.
- **Resource-profile boundary:** the phase-one adapter requests only model identity/backend.
  TabbyAPI still chooses cache, context, split, and reserve defaults, while a model-local
  `tabby_config.yml` can override request values. Until a typed requested/effective load profile
  and managed override policy land, ExLlamaV3 is dynamically switchable but not quantitatively
  admissible by VRAM/topology.
- **Readiness:** the capability is grantable once its model id appears in `loaded_model_ids` and its phase is `WARM`.
- **One deadline:** `warmup_timeout_s` creates one monotonic deadline for the entire `await_warm`
  call. An adapter's `estimated_ready_ms` may seed the first sleep, but that sleep and every poll
  interval are capped to the remaining budget; the estimate cannot double the configured timeout.
- **Failure containment:** v1 does not record enough prior model-level state or post-failure proof
  to distinguish a safely stalled fixed warm-up from an uncertain dynamic load. Any activation or
  `WARM` convergence failure on this path therefore leaves the target Animator and queue claim gate
  closed.

The llama.cpp router and ExLlamaV3/TabbyAPI adapters implement the dynamic activation seam. Fixed
OpenAI-compatible and generic adapters are not called for activation; their already-started targets
use convergence only and must become `WARM` within the same absolute deadline.

### Host Mutation Port and Privilege Boundary

The domain depends only on `RuntimeActuator.apply(TransitionIntent)`. A hard-transition intent
carries a transition id, forward/compensation operation, optional completed-forward `rollback_of`
reference, configuration-generation digest, canonical target Animator, exact target capability,
exact evict and launch sets, and the exact expected-active pre-world. It forbids extra fields and
has no command, unit name, filesystem path, environment, or generic payload surface. The system
boundary resolves those logical identities only through the bound registry.

Fresh intents always name the exact capability used by policy. Compensation must be the exact
inverse declared by its referenced completed forward record. Its one bounded physical request may
start the captured prior compatible target set or stop extra launched targets according to the
settled world; job quiescence and exact final observation, not the client return code, prove
restoration. An operation label cannot authorize an arbitrary second plan.

`[orchestration.switching].actuator` selects `systemd` or `host-reactor` at composition:

```toml
[orchestration.switching]
actuator = "host-reactor"
systemctl_timeout_s = 120.0
```

`host_reactor_dir` defaults to the XDG-derived LychD Reactor inbox and may be overridden with an
absolute operator-owned path whose final segment remains `inbox`. Its sibling journal is derived;
`lychd init` provisions the validated paths. These paths are resolved at composition and never copied into a
`TransitionIntent`.

- **`host-reactor` (caged default):** writes one `0600` JSON intent using sibling-temp creation,
  file and directory `fsync`, and atomic no-overwrite publication into an owner-only inbox. Bind
  generates `lychd-reactor.path` and a host-side oneshot that invokes the private Reactor consumer
  process entrypoint. That process is generated-service machinery, not a public Pulse root. The
  consumer claims before parsing through a no-follow bounded descriptor read, then validates the typed
  schema/set invariants, filename/transition identity, configuration digest, configured switch
  plan, expected user-unit active set, host registry mappings, Scribe ownership and sources, the
  installed/loaded LychD target namespace, and every managed target/service/Coven relation before
  acting. Its host-owned journal distinguishes six outcomes: `.processing` is claimed but
  unresolved work; `.completed` proves the requested world; `.declined` proves a pre-effect
  precondition failure; `.restored` proves the exact prior world after failure or cancellation;
  `.contained` records a fresh physically uncertain effect; and `.rejected` records an invalid
  delivery rather than a physical result. An existing journal ID suppresses duplicate publication.
  The consumer holds the same interprocess lifecycle lock used by `init`, `bind`, `start`, `stop`,
  and `del` across validation and effects, and its direct actuator receives a freshly resolved
  root-controlled absolute `systemctl` path rather than searching `PATH`. Lock identity is
  independent of process-local `TMPDIR`, so the generated service and an operator shell cannot
  select separate exclusion domains. The Vessel mounts that journal read-only and holds the manager
  barrier until its transition reaches `.completed`, `.declined`, `.restored`, `.contained`, or
  `.rejected`; safe decline/restoration reopens the barrier, while contained/rejected outcomes fail
  closed. A fresh uncertain physical outcome becomes `.contained.json`. A crash-reclaimed
  `.processing.json` remains unchanged whenever recovery still cannot classify the world, so
  startup stays fenced rather than converting uncertainty into a false terminal result. Recovery
  waits for relevant systemd jobs, observes every managed Animator target and service, accepts an
  exact requested world, retries from an exact prior world, and otherwise attempts one bounded
  inverse before requiring exact restoration. It never invents progress from an action-prefix
  cursor. Containment is host-global, not merely a Vessel-side status: a pre-existing
  `.contained` record refuses every new Reactor effect, and a newly contained or unresolved
  processing record aborts the current batch before the next inbox item is claimed.
- **`systemd` (explicit uncaged mode):** resolves canonical local Soulstones through registry truth
  and attests the loaded graph in process, then makes one blocking Animator-target request. A
  forward hard swap starts the selected target; an inverse may start the prior compatible set or
  stop extra targets. The composition injects the shared lifecycle lock around attestation,
  observation, the compound effect, settlement, and compensation; contention is a typed no-effect
  precondition rather than an uncertain partial transition.

The intent channel remains unidirectional and the journal is not a generic reply protocol. The
Vessel has no journal write authority and observes only transition-correlated terminal filenames.
`systemctl_timeout_s` bounds each trusted `systemctl` client. A timed-out client is terminated,
escalated to kill if necessary, and reaped. Before physical submission, timeout is a typed
no-effect decline. After submission, client death does not prove cancellation of the systemd job:
the actuator still waits for relevant jobs, classifies the settled target-and-service world, and
either accepts the desired world, proves exact restoration, compensates, or contains uncertainty.
`reactor_ack_timeout_s` bounds claim: an unclaimed intent is retracted and `fsync`ed before failure
reopens admission. Once claimed, the manager (and a cancellation path) waits through a terminal
record even beyond that deadline; this claimed-work terminal fence is intentionally not shortened
by the client timeout. Startup likewise stays closed while pending or `.processing` work exists and
while any durable `.contained` marker remains. After a completed physical receipt, ordinary
capability probes and bounded `await_warm` remain the separate readiness truth. The filesystem
handoff is local-UID authority, not a signature or network authentication protocol.

!!! warning "Safe decline can still require operator reconciliation"
    The caged manager derives `expected_active_animators` from its capability-readiness projection,
    while the host stale-world check uses user-Systemd activity. A unit can therefore be hung yet
    still `active` to Systemd and absent from the manager's expected set. The host safely declines
    that transition before effects, so admission reopens and containment does not latch, but the
    mismatch is not self-healing: repeated retries may decline again until the operator reconciles
    the runtime or stops the hung unit before retrying.

The implemented hard-switch foundation now joins the structured actuator seam and both transport
shapes to the conflict-target compiler, Scribe-owned loaded-graph attestation, one compound systemd
transaction, target-and-service world classification, exact-prior-world compensation, typed safe
cancellation, and durable Host Reactor containment/recovery fences. [State of
Work](../state-of-the-work.md#declared-conflict-topology) owns the bounded repository proof and the
separate real-host receipt. General repair of arbitrary physical states and
signature/remote-authentication policy remain later work. They extend this narrow port; they do not
move subprocess or privilege policy back into the Orchestrator domain.

### 2. Model Tiering and Reservation

Future resource-aware strategies will manage a fluid manifest:

- **Tier Selection:** If an intent requires concurrent "Vision + Reasoning" exceeding the VRAM capacity, the Orchestrator instructs the Dispatcher to manifest a lower-tier Reasoning Soulstone (e.g., 8B instead of 70B).
- **Lexical Reservation:** The Orchestrator enforces a permanent 1-2GB margin for the system's **Native Lexicon** (a sub-2B parameter model), ensuring the "Brain Stem" remains resident and operational during all swaps.
- **Ingestion Scheduling:** Background memory augmentation may run in batched ingestion epochs. During these epochs, embedding covens receive bounded priority and must yield to high-priority interactive reflexes.

### 3. Delegated Provider Capacity

The Orchestrator also owns physical and economic admission for delegated-agent provider pools after
the Dispatcher has selected a compatible capability. This is capacity policy, not semantic
routing: it may delay or decline a selected `AgentJob`, but it cannot rewrite the task, choose a
different provider, create Graph branches, or make a result true.

Each pool is configured from legitimately authorized provider accounts or seats and records the
minimum of operator, provider, contract, and observed ceilings. The adapter may report usage,
rate-limit, reset, cooldown, and health observations; an absent or unverifiable limit is
**unknown**, never invented. Unknown quota degrades to the conservative configured hard ceiling.

The named quota posture is selected on the provider pool or scheduler, never embedded as meaning in
a Pattern:

| Posture | Admission intent |
| :--- | :--- |
| `conservative` | Reserve substantial headroom, admit at most one slot by default, and avoid speculative work. |
| `balanced` | Use a configured middle share while retaining recovery and interactive headroom. This is the default. |
| `maximize` | Use the highest configured and authorized concurrency and the remaining admitted quota before a trustworthy reset. |

Every posture remains below the same hard concurrency, request/token/spend, timeout, cooldown, and
automation-policy ceilings. `maximize` does not mean unbounded: it never rotates or farms accounts,
evades rate limits, violates provider terms, fabricates reset times, or silently falls back to
paid capacity. A reset estimate affects pacing only when its source and freshness are retained.

Capacity reservation, admission, release, and denial produce correlated evidence. Job cancellation
releases the local slot only after process settlement and Gate revocation; a disappeared child is
not evidence that its upstream request stopped.

The present typed capacity policy is a Partial calculation seam. It does not prove a provider
observation loop, durable reservation ledger, Gate integration, or effectful scheduler. [State of
the Work](../state-of-the-work.md#delegated-agent-execution) owns that boundary.

### 4. Swarm Lease Management

To protect the local Magus from resource exhaustion by the **[Legion (42)](42-legion.md)**, the Orchestrator reserves **Workload Tiering** as a policy target:

- **The Lease:** Incoming peer requests are granted a temporary hardware lease. The Orchestrator
  marks the granted Animator set as leased while the swarm task runs.
- **Preemption:** Local user activity — any interactive reflex (voice, text, UI) — is the absolute priority trigger. When detected, the Orchestrator immediately revokes the lease.
    1. The swarm Ghoul receives `SIG_SOFT_STOP`.
    2. It completes its current atomic inference step, persists its recovery boundary (graph or job state as applicable) to the **[Phylactery (06)](06-persistence.md)**, and hibernates.
    3. The GPU is reclaimed for the local reflex.
    4. When the local user is satisfied and the GPU is free, the Orchestrator restores the lease and the swarm Ghoul rehydrates from the serialized state.
- **Ghost Lease Cleanup:** If a swarm task fails or the peer disconnects, the dead lease is swept from the registry on the next Watchdog cycle.

### 5. Watchdog and Recovery

The planned Orchestrator Watchdog will supervise active container services. If a hardware state
fails to manifest after a bounded number of attempts or a model consumes resources beyond policy
(as reported by **[The Oculus (29)](29-observability.md)**), it may request a hard reset and alert
the Magus. The foundation currently fails bounded warm convergence loudly; it does not yet run this
autonomous recovery loop.

!!! note "Implemented foundation vs later policy"
    The implemented foundation includes one transition arbiter, fresh in-arbiter replanning,
    configurable hard-swap priority, admission-closed lease drain, leased-evictee retention, the
    structured actuator with configurable Systemd/Host Reactor implementations, the generated Host
    Reactor consumer, exact Scribe-owned loaded-graph attestation, one compound target request,
    settled target-and-service world classification, typed hard-readiness compensation, safe
    cancellation restoration, durable `.processing`/`.contained` startup fences, same-Animator
    lease-safe llama.cpp soft activation, one-deadline bounded warm convergence, and fail-closed
    uncertain outcomes.

    The declared conflict-domain schema, per-Animator target compiler, exact-neighborhood policy,
    graph attestor, compound transaction, failure classifier, and exact restoration path have
    focused repository tests. [State of
    Work](../state-of-the-work.md#declared-conflict-topology) owns that bounded software claim and
    the separate real-host receipt. Metabolic Whim accounting, model-tier substitution, lexical
    VRAM reservation, swarm preemption, the watchdog, a trustworthy model-level soft inverse, a
    general physical repair engine, and remote-authentication policy remain later strategies and
    recovery work.

    Fail-closed containment is process-lifetime state exposed as
    `OrchestratorManager.containment_reason`. It is not cleared by a later request or by the arbiter
    releasing its serialization slot; this prevents a manual/API transition from unpausing the
    global broker after an uncertain physical outcome. In mediated mode, a fresh uncertain host
    effect also becomes a durable `.contained` marker so application restart cannot erase that
    uncertainty; unresolved crash recovery remains `.processing`.

## Consequences

!!! success "Positive"
    - **Physical Reliability:** The Orchestrator decides from the complete declared graph and
      systemd executes one transaction from its attested compiled form.
    - **Lease Honesty:** Admission closure and drain prevent known active grants from being evicted mid-step; durable graph guarantees remain the Graph/Phylactery's responsibility.
    - **Containment Honesty:** An uncertain mutation cannot be papered over by a later NO_OP or
      different API transition. Direct mode has only a process-local latch; mediated mode preserves
      a durable `.contained` marker across restart until operator recovery.
    - **Configurable Authority:** The same structured transition can use direct user-systemd
      actuation or mediated Host Reactor delivery without changing domain policy.
    - **Policy Growth:** Resource-aware strategies can extend a stable
      plan/drain/attest/actuate/converge sequence without acquiring a second temporal will or
      replacing the host's transaction engine.

!!! failure "Negative"
    - **State Swap Latency:** Swapping remains a heavy physical operation (20–60 seconds), necessitating the batching of rituals to maintain efficiency.
    - **Policy Complexity:** Implementing a custom Orchestration Strategy requires deep technical knowledge of both the application cortex and the host hardware characteristics.
    - **Configuration Consequence:** An explicit empty conflict set is a real coexistence assertion;
      an incorrect declaration can admit an OOM that no scheduler without resource measurement can
      predict.
