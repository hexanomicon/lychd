---
title: 23. Orchestrator
icon: material/scale-balance
---

# :material-scale-balance: 23. Orchestrator

!!! abstract "Context and Problem Statement"
    A selected local capability may be cold because its runtime conflicts with work already on the
    host. Stopping and starting it is a physical transaction with active leases, a possibly stale
    world, and an outcome that can remain unknown. LychD needs one serialized readiness owner.

## Requirements

- Orchestrator alone owns application-initiated readiness transitions; systemd remains the physical transaction engine.
- Fresh capability observations and the compiled conflict graph determine one plan.
- Dedicated local Soulstones alone are lifecycle-managed; shared runtimes and Portals may be warm routes but are not managed.
- Admission closes before complete affected-set lease drain; stale truth declines before effect.
- Host work crosses a frozen TransitionIntent, never a command, path, environment, unit, or generic payload.
- Reopen only after success, proved no effect, or exact restoration. Contain uncertainty.
- Priority orders waiters and may decline a hard swap; it never preempts a submitted transaction.

## Considered Options

| Option | Result |
| --- | --- |
| Dispatcher activates selected runtime | Rejected: matching would acquire mutation authority and race drain. |
| Domain policy scripts stop/start | Rejected: it duplicates the compiled systemd graph. |
| Proxy controls lifecycle | Rejected: it cannot attest local ownership or settled units. |
| Serialized planner plus structured actuator | Selected: policy admits; trusted host validation performs one bounded transaction. |

## Decision Outcome

| Office | May do | Must not do |
| --- | --- | --- |
| [Dispatcher](22-dispatcher.md) | Match and issue warm grants; register leases | Activate or mutate lifecycle |
| Orchestrator | Plan, prioritize, close/drain, converge, compensate, contain | Choose semantic provider or Graph meaning |
| Adapter | Probe and supported runtime-native activation | Cross-Animator eviction |
| Actuator/systemd | Attest, transact target, classify settled world | Invent policy |
| [Graph](24-graph.md) | Stasis and retry after convergence | Mutate hardware |

A non-warm managed route arrives as handle-free HardwareTransitionRequired; canonical registry
truth is fetched again.

### 1. The Tipping Point (Whim Algorithm)

**Whim is Designed, not current behavior.** declared-conflicts (and compatibility alias
evict-idle) only counts selected evictees in total_metabolic_cost. It measures no VRAM, load time,
context rebuild, thermal state, topology, bandwidth, transition peak, or tier substitution.

After refreshing every managed Animator, the current policy gives NO_OP to a warm/open target,
SOFT_SWAP to a started but non-warm runtime, HARD_SWAP to a down dedicated runtime, and refuses a
down shared/non-managed runtime. A hard plan selects active exact neighbours of the undirected
conflict_domains graph. Omitted conflict on dedicated non-resident means conservative
default-exclusive; only explicit [] claims coexistence. Coven membership aggregates metadata: it
never creates or relaxes conflicts. Bind rejects unadvertised Soulstones, conflicting Covens, and
non-dedicated or persistent-resident Animators with non-empty conflicts.

Leased neighbours remain evictees: a lease forces drain; it does not make incompatible work
immortal. Affected set means evictees plus launch targets.

TransitionArbiter has one owner. It orders contenders by descending priority then FIFO; same
capability/same priority joins one in-flight plan, different priorities do not. A hard swap below
min_priority_for_hard_swap declines before effect; NO_OP and SOFT_SWAP are never threshold gated.
A warm/open fast path can return early, but every other plan is recomputed inside the arbiter after
its predecessor settles. Previews bind nothing.

The actual rite is:

1. Refresh and compute target plus exact affected set.
2. Close affected lease admission, then the process claim gate.
3. Wait for no live LeaseLedger grant on any affected Animator; broadcast_soft_stop() is now a no-op.
4. Freeze a TransitionIntent with target, evict/launch sets, expected active pre-world, and capability/conflict digest.
5. Have the host boundary attest freshness, ownership, loaded topology, and pending systemd work.
6. Perform one hard target transaction or one permitted runtime-native soft activation.
7. Require target WARM, and after hard swap every evictee stopped.
8. Reopen only under the restoration law.

Pre-effect drain timeout/cancellation reopens gates. The waiting run has no lease. Hardware Stasis
is live; Graph and Snapshots own durable sleep. The process-local bounded TransitionJournal is for
Nexus/run-event projection, not a Host Reactor journal or complete history.

### Runtime-Started Convergence (`SOFT_SWAP` Plan Label)

SOFT_SWAP says only that the runtime is started. It need not load a model. The whole target
Animator drains because a dynamic load can unload another model behind a lease. A dynamic
non-WARM/non-WARMING capability asks its canonical adapter to activate; WARMING and static
started routes merely await honest warmth.

Dispatcher never asks this of a shared non-warm route. Direct surfaces retain a narrower gap:
they test runtime_started before dedicated, so an explicit already-started shared dynamic Animator
can enter SOFT_SWAP; that violates the ownership law and is not support evidence.

llama.cpp router and ExLlamaV3/TabbyAPI prove the seam in repository tests, not live model/GPU
operation; State records their Operator-validation receipts. One warm-up deadline bounds observation.
Soft activation has no sufficient prior model state for a trustworthy inverse: failure leaves its
claim and admission gates closed for operator recovery.

### Host Mutation Port and Privilege Boundary

RuntimeActuator.apply(TransitionIntent) is the lone domain mutation port. Its closed intent has
logical Animator identities, no shell or unit payload. Compensation names one completed forward
transition and is its exact typed inverse.

Direct systemd is explicit uncaged mode: under the lifecycle lock it resolves registry identities,
attests the loaded Scribe-owned graph, requests one target transaction, awaits jobs, and classifies
service state. Caged Host Reactor atomically publishes owner-only JSON, revalidates after claim,
shares the lock, uses an attested absolute systemctl, and records the result; local-UID handoff is
not a signed remote protocol.

| Reactor result | Meaning |
| --- | --- |
| .completed | Exact requested world observed |
| .declined | Preconditions failed before effect |
| .restored | Exact prior world observed |
| .processing | Claimed work unresolved |
| .contained | Fresh outcome uncertain |
| .rejected | Invalid delivery, not physical success |

Unclaimed publication may be retracted after claim deadline. Claimed cancellation/timeout does not
prove systemd stopped; wait for terminal classification. Exact desired state wins even after a bad
client return; exact prior state is restored; otherwise one typed compensation must prove exact
restoration. Rejected/contained or unresolved compensation fails closed. Direct containment latches
only process lifetime; Reactor .processing/.contained survive and fence startup/effects until
operator recovery. Inert private-systemd tests prove ordering, not Quadlet/Podman/GPU embodiment.

### 2. Model Tiering and Reservation

Resource-aware scheduling is Designed. Preload and idle-eviction fields are validated but unused;
explicit coexistence and persistent_resident are declarations, not capacity proof. Future measured
envelopes must keep plan/drain/attest/actuate/converge intact.

### 3. Delegated Provider Capacity

After semantic selection, a future policy may delay/decline delegated work for admitted physical
or economic capacity, never rewrite task, choose provider, alter Graph, or manufacture capacity.
ProviderCapacityPolicy is only a pure Partial seam: conservative/balanced/maximize never exceed
the minimum authorized/provider/configured ceilings, disablement/cooldown stops admission, and
unknown quota means at most one slot. No scheduler, observation, durable reservation/release,
Provider Gate, or spend ledger is wired.

### 4. Swarm Lease Management

Swarm leasing is Designed. Current leases are process-local; expires_at has no enforcement,
renewal, distributed fence, peer lease, preemption, handoff, or ghost sweep. Legion must reuse
this admission/drain law.

### 5. Watchdog and Recovery

No autonomous watchdog or general repair engine exists. Pre-effect/drain failure reopens; hard
failure seeks one exact inverse; post-submission cancellation waits for settlement/restoration; soft
failure contains; unknown worlds are operator-owned. Conflict topology is Available in focused
tests; transition protocol and Nexus tickets are Partial; Host Reactor protocol has inert
private-systemd evidence; real host/model runtimes need Operator validation; resource-aware Whim,
tiering, swarm preemption, watchdog, and repair are Designed. The direct shared-dynamic admission
gap remains open.

## Consequences

!!! success "Accepted"
    - Selection, adapter activation, and physical execution have distinct owners.
    - Lease closure precedes drain; stale and unauthorized topology declines before effect.
    - Exact restoration, not optimistic retry, releases containment.

!!! failure "Cost"
    - No capacity solver verifies declared coexistence.
    - Broker gate and leases are process-local; soft activation lacks an inverse; direct containment dies on restart.
    - Live hosts still require named operator receipts.
