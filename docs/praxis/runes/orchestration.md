---
title: Orchestration
icon: material/tune-vertical
---

# :material-tune-vertical: Orchestration reference

The `[orchestration]` block in `~/.config/lychd/lychd.toml` tunes how runs are routed to
queues, how many workers each queue runs, and the policy that governs hardware swaps. This
is the reference for every setting. For the operator's-eye view of swaps, see
[Manage Covens](../rites/manage-covens.md); for the law behind it, see the
[Orchestrator (23)](../../adr/23-orchestrator.md).

## `[orchestration.queues]`

One entry per queue, sizing its worker concurrency. Defaults:

| Queue | `concurrency` | Purpose |
| :--- | :--- | :--- |
| `runs` | `2` | Interactive and CLI runs. |
| `rites` | `4` | Background rites. |

```toml
[orchestration.queues.runs]
concurrency = 2

[orchestration.queues.rites]
concurrency = 4
```

## `[orchestration.routing]`

Routing rules map an Intent source to a queue and a base priority. **Priority is higher =
hotter**: a Bridge message (70) outranks a default run (50), which outranks a background
rite (20). Defaults:

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

Each rule has two fields: `queue` (default `"runs"`) and `priority` (default `50`, range
0–100). The code-side `DEFAULT_ROUTING` table stays equal to these defaults; overriding a
rule here changes routing without touching code.

## `[orchestration.switching]`

Governs hardware (coven) swaps.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `policy` | string | `"evict-idle"` | The swap policy. `evict-idle` evicts every idle, unleased, LychD-owned animator to make room. An unknown name fails loudly at startup. |
| `min_priority_for_hard_swap` | int (0–100) | `40` | A hard swap requested below this priority is **declined**, not performed. This gates thrashing. |
| `drain_timeout_s` | float | `120.0` | How long a swap waits for outstanding leases to drain before it fails the transition. |

```toml
[orchestration.switching]
policy = "evict-idle"
min_priority_for_hard_swap = 40
drain_timeout_s = 120.0
```

!!! note "Declined is honest, not broken"
    When a low-priority request would force a hard swap of a busy coven, the Orchestrator
    declines it rather than thrashing the GPU. The run settles with the decision in its
    message — see [Manage Covens](../rites/manage-covens.md).

## `[orchestration.whim]`

Shape for idle-eviction and preload policy. The fields exist now; the whim *rites* that
consume them land in a later wave.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `idle_evict_after_s` | int | `0` | Evict an idle animator after N seconds (`0` = disabled). |
| `preload` | list[string] | `[]` | Capabilities to warm at startup. |

!!! warning "Unmanifested"
    `[orchestration.whim]` is accepted and validated, but its behavior (idle eviction,
    preload) is not yet driven. Setting these values has no effect until the whim rites
    land (roadmap: Wave 6).
