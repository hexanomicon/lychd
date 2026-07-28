---
title: Coven
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Coven: Named Runtime Grouping

> _"Two spirits cannot haunt the same iron. To wake one, another must sleep."_

A **coven** is a named group of model services ([Soulstones](./soulstone.md)) materialized as a
systemd target for compatible operator aggregation. It is not a conflict or eviction policy.
Finite-domain incompatibility is declared separately in each Soulstone's
`[concurrency].conflict_domains` and compiled onto per-Animator targets. The
**[Orchestrator (23)](../../adr/23-orchestrator.md)** decides when a transition may occur; systemd
executes the compiled physical transaction.

Covens are declared by the `groups` field on a Soulstone Rune. Sharing a group requests aggregate
membership only. Bind permits that aggregate only when its members' conflict-domain sets do not
overlap; an internally conflicting Coven fails closed. Different groups do not create
incompatibility. The `alliances` shape remains reserved for later policy and is not an enforcement
boundary. See [Soulstone](./soulstone.md#-coven-management-the-group-rule).

!!! warning "Operator break-glass surface"
    Starting a generated Coven target explicitly starts its compatible Animator targets, and
    stopping it propagates through the generated target/service relationships. Starting an
    individual Animator target is equally direct. Both bypass Orchestrator priority admission,
    lease drain, stale-world validation, WARM convergence, and compensation. They are reserved for
    a host operator performing administration or recovery; application code, agents, and extension
    policy must address the Orchestrator instead.

## The states you will see on the Nexus

The [Nexus](../../divination/altar/nexus.md) shows each capability in one of five operator
states — **active**, **warming**, **awaited**, **cold**, **fault**. The vocabulary and the
phase ladder behind it are defined in [Capabilities](./capabilities.md); the law is the
[Dispatcher (22)](../../adr/22-dispatcher.md). Any managed capability below WARM triggers readying:
**cold** normally requires a hard runtime swap, **awaited** identifies a dynamic runtime that needs
lease-safe activation, and **warming** may be a dynamic or fixed/static runtime already converging.
Internally, any runtime-started non-WARM target uses the `SOFT_SWAP`-labelled target-only barrier;
that label does not promise that a model-load call will occur.

## How a swap happens

When a run needs a managed capability below **WARM**, the Dispatcher raises a readiness transition
and the Orchestrator:

1. Pauses new job claims and closes admission for every affected Animator.
2. Waits for **leases** to release—a hard swap drains the exact active conflict-neighbor set; a
   runtime-started convergence path drains the target Animator (up to `drain_timeout_s`).
3. Revalidates the active world. The Host Reactor separately rejects a stale intent-generation
   digest; the actuator then binds the current Rune graph to the exact Scribe-owned unit set and
   proves the installed/loaded targets, managed relations, source paths, and unit-file state.
4. Hard: ask systemd to start the selected Animator target once; systemd stops its compiled
   conflicts and starts the target in one transaction. Runtime already started: call the adapter's
   model-load seam only for a dynamic target that is not already WARMING; fixed/static and
   already-WARMING targets perform convergence only.
5. Await honest WARM, then let the parked run retry dispatch. A hard readiness failure asks systemd
   to apply one exact inverse: start missing members of the captured prior compatible set or stop
   extra launched targets, then wait for jobs and prove the exact prior target-and-service world.
   A proved restoration—including restoration after cancellation—reopens admission. An uncertain
   hard transaction, runtime-started activation/convergence failure, or failed inverse stays
   fail-closed for operator recovery rather than reopening into unknown runtime state. A
   process-lifetime containment latch rejects every later transition/NO_OP until restart or repair.

A run parked waiting for its own transition holds **no** lease, so it never blocks its own swap.

## Watch a swap

```bash
curl -s http://localhost:7134/orchestrator/queues | jq
curl -s http://localhost:7134/orchestrator/status | jq '.mutation_containment'
```

The response shows each queue's `depth`, `active` count, and `paused` state, plus the `leases`
currently held (each with its `capability_key`, `holder`, and `priority`). Watching this during
a Bridge conversation shows a lease appear, the swap wait for it, and the transition complete.
The status response's `mutation_containment` is normally `null`; a reason means the process has
latched an uncertain mutation and will reject every transition until operator recovery/restart.
The Nexus shows the same capability moving **cold → warming → active**.

## Request a transition manually

To warm a target capability directly, ask the Orchestrator to activate it. `priority` is
higher = hotter:

```bash
curl -s -X POST "http://localhost:7134/orchestrator/activate?target=atelier:chat:qwen3-8b&priority=70"
```

- **202** — the transition was accepted (or used runtime-started convergence / no-op).
- **409** — the hard swap was **declined**: the priority was below `min_priority_for_hard_swap`.
  This is honest back-pressure, not an error — retry with a higher priority if the swap is truly
  warranted. The 409 body carries the plan and the threshold.

---

## Orchestration reference

`[server.jobs]` defines the local job capacity; `[orchestration]` maps
semantic run sources onto that fixed capacity and governs swaps. For the law
behind it, see the [Orchestrator (23)](../../adr/23-orchestrator.md).

### `[server.jobs]`

One explicit concurrency setting per fixed queue.

| Queue | Setting | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `runs` | `interactive_concurrency` | `2` | Interactive and CLI runs. |
| `rites` | `background_concurrency` | `4` | Background rites. |

`admin_ui_enabled` optionally mounts SAQ's diagnostic queue UI at
`admin_ui_path` (default `/saq`) on the Vessel's existing HTTP address. It does
not start a second server or open another port. It is disabled by default and
has no LychD-specific guard, so an eventual Ward/Proxy must not expose it
without an explicit access policy.

```toml
interactive_concurrency = 2
background_concurrency = 4
```

### `[orchestration.routing]`

Routing rules map an Intent source to a queue and a base priority. **Priority is higher =
hotter**: a Bridge message (70) outranks a default run (50), which outranks a background rite (20).

| Rule | `queue` | `priority` |
| :--- | :--- | :--- |
| `default` | `runs` | `50` |
| `cli` | `runs` | `50` |
| `bridge` | `runs` | `70` |
| `rite` | `rites` | `20` |

```toml
[orchestration.routing.bridge]
queue = "runs"
priority = 70
```

Each rule has `queue` (default `"runs"`) and `priority` (default `50`, range 0–100). The
code-side `DEFAULT_ROUTING` table stays equal to these defaults; overriding a rule here changes
routing without touching code.

### `[orchestration.switching]`

Governs hard runtime swaps and runtime-started readiness convergence.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `actuator` | string | `"host-reactor"` | Caged mediated actuation; `"systemd"` is explicit uncaged mode. |
| `host_reactor_dir` | absolute path | XDG `.../lychd/triggers/inbox` | Writable intent inbox; sibling journal is derived and mounted read-only. |
| `policy` | string | `"declared-conflicts"` | The swap policy. `declared-conflicts` computes the exact active conflict-neighbor set; `evict-idle` remains a compatibility alias, not the old all-active algorithm. Omitted dedicated non-residents receive the conservative `default-exclusive` wildcard; group/alliance labels do not alter the graph. An unknown name fails loudly at startup. |
| `min_priority_for_hard_swap` | int (0–100) | `40` | A hard swap requested below this priority is **declined**, not performed. This gates thrashing. |
| `drain_timeout_s` | float | `120.0` | How long a hard evictee set or runtime-started target Animator waits for outstanding leases before readying. |
| `warmup_timeout_s` | float | `180.0` | One absolute WARM convergence budget, including any adapter-estimated first sleep; every poll sleep is capped to the remaining budget. |
| `reactor_ack_timeout_s` | float | `120.0` | How long a Reactor intent may remain unclaimed; claimed work stays fenced to a terminal receipt. |

```toml
[orchestration.switching]
actuator = "host-reactor"
policy = "declared-conflicts"
min_priority_for_hard_swap = 40
drain_timeout_s = 120.0
warmup_timeout_s = 180.0
reactor_ack_timeout_s = 120.0
```

!!! note "Declined is honest, not broken"
    When a low-priority request would force a hard swap of an active conflict set, the Orchestrator
    declines it rather than thrashing the GPU. The run settles with the decision in its message.

!!! warning "A safe Host Reactor decline may repeat"
    Host-side configuration, policy, or stale-active-set preconditions are recorded as
    `.declined.json` before any effect and surface as a typed no-effect failure. The manager reopens
    its barrier without mutation containment. However, the manager's capability projection and
    user-Systemd activity are different observations: a hung unit may remain `active` to Systemd
    while appearing absent to readiness probing. Reconcile or stop that unit before retrying; a
    retry against the same mismatch may be declined again.

!!! warning "Restored is safe; contained is not"
    `.restored.json` means the actuator observed the exact prior target-and-service world, so the
    manager may reopen its barrier. A fresh physical outcome that cannot be proved becomes
    `.contained.json`; startup and later transitions remain fenced for operator reconciliation. If
    the Reactor crashes after claiming work and recovery still cannot classify the world, the
    nonterminal `.processing.json` remains in place. `.rejected.json` denotes an invalid delivery,
    not a claim that an uncertain physical transaction was safely undone.

### `[orchestration.whim]`

Shape for idle-eviction and preload policy. The fields exist now; the whim *rites* that consume
them are not yet driven.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `idle_evict_after_s` | int | `0` | Evict an idle animator after N seconds (`0` = disabled). |
| `preload` | list[string] | `[]` | Capabilities to warm at startup. |

!!! warning "Unmanifested"
    `[orchestration.whim]` is accepted and validated, but its behavior (idle eviction, preload)
    is not yet driven. The fields are accepted and inert; setting them has no effect until the
    whim rites land.

## Tune the policy

- Raise `min_priority_for_hard_swap` to make the system more reluctant to swap busy hardware.
- Adjust `drain_timeout_s` to change how long a swap waits for leases to release.
- Mark a support runtime `persistent_resident = true` in its Soulstone Rune's `[concurrency]`
  table to keep it out of conflict participation and every eviction set.
- Give incompatible managed Soulstones at least one shared `conflict_domains` label. Use explicit
  `[]` only when their combined substrate is known to fit.

## Verify

- `curl .../orchestrator/queues` shows leases appearing and clearing around a run.
- `POST /orchestrator/activate` at priority 70 returns 202; at priority 25 against a busy conflict
  set returns 409.
- The Nexus reflects the capability moving to **active** after a successful swap.
