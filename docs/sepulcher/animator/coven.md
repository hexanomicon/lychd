---
title: Coven
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Coven: Named Runtime Grouping

> _“A Coven names what may rise together; it never decides what must sleep.”_

A **Coven** is a named systemd target emitted when two or more compatible
[Soulstones](./soulstone/index.md) share a group. Soulstone `groups` request membership;
`[concurrency].conflict_domains` separately declares finite-resource incompatibility. A Coven is
neither conflict nor eviction policy.

One member emits no target. Different groups create no coexistence promise. Members' effective
conflict sets must not overlap; an internally conflicting Coven fails closed. `alliances` is
accepted shape without enforcement authority.

!!! warning "Operator break-glass surface"
    Starting or stopping a generated Coven target directly propagates through its compatible
    Animator targets. This bypasses Orchestrator admission, lease drain, stale-world validation,
    readiness, and compensation. Reserve it for host administration or recovery.

## What the Nexus Shows

The [Nexus](../../divination/altar/nexus.md) projects the six
[capability phases](./capabilities.md#dynamic-is-not-ready) as five operator labels; Capabilities
owns that mapping.

## The Transition Contract

The [Orchestrator](../../adr/23-orchestrator.md) owns every application-requested transition:

1. refresh the target and compute its exact affected conflict neighborhood;
2. close lease admission and the Run claim gate;
3. drain affected leases;
4. revalidate configuration and the loaded Scribe-owned unit graph;
5. request one physical transaction or supported runtime-native activation;
6. require honest `WARM`, then reopen only under the restoration law.

A parked requester holds no lease. Refusal before effect or an exact restoration reopens
admission. An uncertain mutation remains contained for operator recovery.

## Inspect and Request

```bash
curl -s http://localhost:7134/orchestrator/queues | jq
curl -s http://localhost:7134/orchestrator/status | jq '.mutation_containment'
```

The queues response exposes `depth`, `active`, `paused`, and each lease's `capability_key`,
`holder`, and `priority`. `mutation_containment` is normally `null`; a reason means later
transitions remain fenced.

Request a target capability directly:

```bash
curl -s -X POST \
  "http://localhost:7134/orchestrator/activate?target=atelier:chat:qwen3-8b&priority=70"
```

- **202**: accepted, including runtime-started convergence or no-op.
- **409**: a hard swap was declined because priority was below
  `min_priority_for_hard_swap`; the response carries the plan and threshold.

Priority is **higher = hotter**. This endpoint is an explicit operational surface, not a side door
for an Agent or extension to bypass ordinary dispatch.

## Queue and Routing Context

`[server.jobs]` fixes two in-process queues: `runs` uses `interactive_concurrency = 2`; `rites`
uses `background_concurrency = 4`. These settings bound tasks, not CPU, memory, admission, or
preemption. The optional SAQ diagnostic UI is disabled by default; enabling it starts no second
server. `admin_ui_path` defaults to `/saq`; exposing it requires an explicit access policy.

`[orchestration.routing]` maps Intent source to queue and doctrine priority:

| Source | Queue | Default priority |
| :--- | :--- | :--- |
| `default` | `runs` | `50` |
| `cli` | `runs` | `50` |
| `bridge` | `runs` | `70` |
| `rite` | `rites` | `20` |

Each rule accepts priority 0–100. Queue execution belongs to
[Workers (14)](../../adr/14-workers.md); these values matter here only because transition policy
receives the Run's doctrine priority.

## Switching Settings

| Field | Default | Meaning |
| :--- | :--- | :--- |
| `actuator` | `"host-reactor"` | Caged mediated actuation; `"systemd"` selects explicit uncaged mode. |
| `host_reactor_dir` | XDG trigger inbox | Absolute writable intent inbox; sibling journal is derived read-only. |
| `policy` | `"declared-conflicts"` | Select exact active conflict neighbors; `"evict-idle"` is a compatibility alias. |
| `min_priority_for_hard_swap` | `40` | Decline colder hard swaps. |
| `drain_timeout_s` | `120.0` | Bound lease drain. |
| `warmup_timeout_s` | `180.0` | One absolute readiness-convergence budget. |
| `reactor_ack_timeout_s` | `120.0` | Bound only the unclaimed Reactor phase. |

Unknown policy values fail at startup. Coven and alliance labels never alter the compiled conflict
graph.

The Host Reactor records exact outcomes: `.declined.json` proves no effect,
`.restored.json` proves the prior world, `.contained.json` fences an uncertain physical outcome,
`.processing.json` is claimed and nonterminal, and `.rejected.json` is invalid delivery. A
systemd unit may remain active while the probe sees it absent; reconcile that mismatch before
retrying.

## Tune With Intent

- Raise `min_priority_for_hard_swap` to resist disruptive swaps.
- Change drain and warm-up deadlines to match measured local convergence.
- Mark support services `persistent_resident = true` to keep them outside conflicts and eviction.
- Give incompatible managed Soulstones a shared conflict-domain label; use explicit `[]` only
  after measuring safe coexistence.

`[orchestration.whim]` accepts `idle_evict_after_s` and `preload`, but no Whim rite consumes them.
They are validated and inert. The current graph is not a VRAM capacity solver.

[State of Work](../../state-of-the-work.md#declared-conflict-topology) records the available
conflict contract; [safe runtime transitions](../../state-of-the-work.md#safe-runtime-transitions)
remain partial, including the direct shared-dynamic activation guard gap and real-host proof.
