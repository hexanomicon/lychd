---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

**Purpose.** The **Nexus** is the Altar's local capability and transition board: the place where a
Magus can witness how declared ability currently meets physical iron.

**Current boundary.** The Svelte page projects cached capability state into managed Coven cards and
a read-only Portal column, labels transition plans as non-binding previews, and can launch one
managed transition through a process-local event-stream ticket. It also exposes the latest bounded
process-local observation of run-origin and operator-origin transition requests, including run,
occurrence, physical-transition, and compensation identities where available. This is neither a
durable history nor a queue, lease, GPU, VRAM, topology, thermal, or hardware-pressure console.
[State of the Work owns the exact delivery
boundary](../../state-of-the-work.md#nexus-transition-board).

**Safety law.** Looking is not commanding. The board is a projection, not a readiness grant, and a
plan is not a reservation. **Request transition** is a real maximum-priority lifecycle mutation,
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
- a **Preview** action for transition planning.

Portals appear in one separate, read-only column because LychD can route to a Portal but cannot
start, stop, or swap the remote provider. A Portal row is not proof of safe
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

Choosing **Preview** asks the Orchestrator to refresh lifecycle-managed runtimes and calculate a
dry-run plan. The drawer labels that plan as non-binding and may show:

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

The ticket is process-local UI state. It now carries the request identity, observed transition
phase, and physical/compensation identities when the Orchestrator supplies them. It still has no
durable owner, complete history, cancel action, restart recovery, or detailed failure record.

Beside tickets, Nexus retains a separate bounded **latest transition observation** journal. It
accepts the same traced phases from automatic Graph Stasis and explicit operator requests and gives
each request a direct `/nexus?transition={request_id}` URL. It is a latest-value diagnostic
projection, not a durable audit log: a
process restart or capacity eviction can remove it. Queue depth and live leases exist on the
separate `/orchestrator/queues` JSON surface, but they are not shown by the Nexus or
`/orchestrator/status`. Durable evidence, resource intelligence, and native Oculus remain separate
contracts.

When Orb opens an exactly correlated transition, it adds `event={event_id}` as disposable return
context. Nexus preserves that parameter only for the selected request and returns to
`/orb/{run_id}?event={event_id}`. Selecting a different transition or closing the inspector drops
the event context; the query does not become transition evidence.

## The Designed Body Map

Nexus is where the stable bodies belong. A future graph-shaped projection may render a Soulstone as
a faceted local body and a Portal as a distinct ring beyond the local-host boundary, but shape
expresses type—not health, safety, cost, or authority. Text, icon, source, freshness, and exact
state remain visible.

The useful questions are concrete:

- **What capability state was observed, by whom, and how recently?** Show the exact phase,
  freshness, bounded historical trend, and `unknown`; do not forecast availability.
- **Who holds this capability, and what blocks a transition?** A lease ring or relation is lawful
  only when backed by exact LeaseLedger records and accompanied by a holder list. Area and glow do
  not imply measured capacity.
- **What is waiting for this capability?** Queue marks require stable request identity and
  destination. Show exact priority or order only when the owning queue provides it; otherwise show
  depth and **order unknown**.
- **What would a transition affect?** A preview may highlight the server-computed affected set,
  admission closure, and expected drain. It remains a dry-run explanation. The Orchestrator
  replans, and the later admitted transition and actual outcome are separate records.

Every canvas relation has a card or table twin. A compact Orb correlation may open the matching
Nexus object, but scrying never swaps an Animator by moving a Run. Nexus may show bounded
orchestration-relevant declarations contextually; the Codex remains their authority, and no
dedicated Bindings instrument exists. Nexus remains the surface for present physical evidence and
explicit lifecycle intent.

## Enter after first life

Only after the four observations in [The Awakening](../../summoning.md#the-awakening) agree—and only
inside the temporary browser boundary above—open:

```text
http://127.0.0.1:7134/nexus
```

Witness one capability card before requesting any transition. If the visible chip and raw status
disagree with the host, stop there and diagnose the owning runtime; do not consecrate a swap merely
to make the glass look calm.
