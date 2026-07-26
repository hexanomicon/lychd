---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

**Purpose.** The **Nexus** is the Altar's local capability and transition board: the place where a
Magus can witness how declared ability currently meets physical iron.

**Current boundary.** The Svelte page projects cached capability state into Soulstone Coven cards
and a Portal column, previews local transition plans, and can launch one managed transition through
a process-local event-stream ticket. It is not yet a queue, lease, GPU, VRAM, topology, thermal,
or hardware-pressure console. [State of the Work owns the exact delivery
boundary](../../state-of-the-work.md#nexus-transition-board).

**Safety law.** Looking is not commanding. The board is a projection, not a readiness grant, and a
plan is not a reservation. **Consecrate the Swap** is a real maximum-priority lifecycle mutation,
not a simulation or ordinary navigation action.

!!! danger "Temporary local-browser boundary"
    Use the Nexus only from a dedicated browser profile on the same host, with the listener on
    literal `127.0.0.1`. Do not publish, reverse-proxy, tunnel, or port-forward the Altar. The fixed
    `magus:*` Sigil is not a login, and the current hostile-browser boundary is incomplete. Follow
    [The Awakening](../../summoning.md#the-awakening) and the canonical [browser and bind
    boundary](../../state-of-the-work.md#local-browser-bind-boundary).

> _At the crossing of Intent and iron, the glass bears witness. It does not become the Physical
> Will by naming what it sees._

The authority split is exact: the [Dispatcher](../../adr/22-dispatcher.md) selects a capability;
the [Orchestrator](../../adr/23-orchestrator.md) readies managed physical state; the Nexus projects
their current records and submits an explicit operator request. The Altar never becomes a second
scheduler.

## What the board witnesses

The board loads after the page, refreshes every five seconds, and refreshes once more when a swap
ticket settles. Each local card is labelled by the first group on its Soulstone Rune, or by its
Animator name when no group exists. That **Coven** label is an operator grouping and systemd target,
not a co-residency, eviction, or GPU-placement rule.

A card currently shows:

- its Coven label;
- each canonical capability key, shaped as `{animator}:{family}:{model_id}`;
- a stable visible state chip; and
- a **scry** action for transition planning.

Portals appear in one separate column. Their transition button is disabled because LychD can route
to a Portal but cannot start, stop, or swap the remote provider. A Portal row is not proof of safe
egress, payment policy, or live reachability; its [owning page](../../sepulcher/animator/portal.md)
defines what was declared and what was actually probed.

The board poll reads the latest registry snapshot. It does not perform a new readiness probe, and
it does not guarantee what a later run will receive.

## Read the state without guessing

The visible chip is a stable client vocabulary projected from the raw phase:

- `active` maps from `warm`;
- `warming` maps from a transition in flight;
- `awaited` maps from a dynamic capability that is activatable but not loaded;
- `cold` covers unavailable non-dynamic or cold capability state; and
- `fault` maps from a recorded error.

It remains a projection. For diagnosis, the read-only `/orchestrator/status` JSON surface exposes
each capability's raw `phase`, `warm`, `health`, and `reason`, plus the process-wide
`mutation_containment` reason.

The raw phase ladder is:

- `warm` — the last observation said requests were accepted;
- `warming` — activation or readiness convergence was in flight;
- `activatable` — a dynamic runtime was up while this model was not loaded;
- `cold` — the runtime was down or the endpoint was unreachable;
- `error` — the capability had a recorded fault; and
- `unknown` — no usable observation was available.

These remain observations, not timeless facts. A fresh dispatch still applies its own admission and
lease boundary before it can issue a capability grant.

## Observation and control are different rites

Choosing **scry swap** asks the Orchestrator to refresh lifecycle-managed runtimes and calculate a
dry-run plan. The drawer may show:

- `NO_OP` — the target was already observed warm;
- `SOFT_SWAP` — the runtime was already started and the target needed target-only readiness
  convergence;
  the label does not promise that a model-load call will occur; or
- `HARD_SWAP` — a managed runtime had to be launched and the listed Animators selected for
  eviction.

The displayed **metabolic cost** is currently only the number of selected evictions. It is not a
VRAM, load-time, energy, topology, or context-reconstruction estimate. The current resource-aware
scheduling boundary is recorded in [State](../../state-of-the-work.md#resource-aware-scheduling).

A dry run changes no runtime. If the plan is not `NO_OP`, **Request transition** submits a typed
JSON intent at maximum operator priority.
The Orchestrator replans inside its serialized arbiter, closes admission for the affected
Animators, waits for existing leases to release, applies the bounded transition, and converges on
honest warmth or fail-closed containment. The preview is therefore an explanation of the observed
world, not a promise that its exact evict set is reserved.

## What a swap ticket proves

The initiating page receives one semantic event-stream ticket with one of three states:

- `warming` — the ticket has not yet observed a terminal task result; the initial 202 response uses
  this state;
- `settled` — the task returned and the board refreshes; or
- `failed` — the task raised or was cancelled.

The ticket is process-local UI state. It has no durable owner, history, cancel action, timestamps,
retention promise, restart recovery, or detailed failure record. Queue depth and live leases exist
on the separate `/orchestrator/queues` JSON surface, but they are not shown by the Nexus or
`/orchestrator/status`. Durable evidence, resource intelligence, and native Oculus remain separate
contracts.

## Enter after first life

Only after the four observations in [The Awakening](../../summoning.md#the-awakening) agree—and only
inside the temporary browser boundary above—open:

```text
http://127.0.0.1:7134/nexus
```

Witness one capability card before requesting any transition. If the visible chip and raw status
disagree with the host, stop there and diagnose the owning runtime; do not consecrate a swap merely
to make the glass look calm.
