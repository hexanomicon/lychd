---
title: Manage Covens
icon: material/swap-horizontal-bold
---

# :material-swap-horizontal-bold: Rite — Manage Covens

**Goal:** understand and drive coven swaps — warming a cold capability, watching a hardware
transition, and tuning the swap policy.

**Prerequisites:** a running daemon with at least two local
[Soulstones](../../sepulcher/animator/soulstone.md) that compete for the same hardware.

A **coven** is a group of model services that share hardware and are manifested and banished
together. Because VRAM is finite, only one coven can occupy a hardware coordinate at a time
(the Law of Exclusivity). Moving from one to another is a **swap**, governed by the
[Orchestrator (23)](../../adr/23-orchestrator.md).

## The vocabulary you will see on the Nexus

The [Nexus](../../divination/altar/nexus.md) shows each capability's state:

- **active** — warm and serving now.
- **warming** — loading.
- **awaited** — a `DYNAMIC` model reachable but not loaded; requesting it activates it.
- **cold** — the unit is down; requesting it triggers a swap (if LychD owns its lifecycle).
- **fault** — errored; diagnose via [Exorcism](../exorcism.md).

See [Capabilities](../../sepulcher/animator/capabilities.md) for how these arise.

## How a swap happens

When a run needs a capability that is **cold**, the Dispatcher raises a hardware transition
and the Orchestrator:

1. Pauses new job claims and drains outstanding work.
2. Waits for **leases** to release — a lease is a live grant a run holds against a
   capability. A leased animator is never evicted; the swap waits for it (up to
   `drain_timeout_s`).
3. Evicts the idle, unleased animator and starts the target.
4. The parked run resumes on the new hardware.

A run parked waiting for its own transition holds **no** lease, so it never blocks its own
swap.

## Watch a swap

Inspect queue depth and live leases directly:

```bash
curl -s http://localhost:7134/orchestrator/queues | jq
```

The response shows each queue's `depth`, `active` count, and `paused` state, plus the
`leases` currently held (each with its `capability_key`, `holder`, and `priority`). Watching
this during a Bridge conversation shows a lease appear, the swap wait for it, and the
transition complete.

You can also see the whole picture on the [Nexus](../../divination/altar/nexus.md) as it
moves a capability **cold → warming → active**.

## Request a transition manually

To warm a target capability directly, ask the Orchestrator to activate it. `priority` is
higher = hotter:

```bash
curl -s -X POST "http://localhost:7134/orchestrator/activate?target=atelier:chat:qwen3-8b&priority=70"
```

- A response of **202** means the transition was accepted (or was a soft activation / no-op).
- A response of **409** means the hard swap was **declined** — the priority was below the
  `min_priority_for_hard_swap` gate. This is honest back-pressure, not an error: retry with a
  higher priority if the swap is truly warranted. The 409 body carries the plan and the
  threshold.

## Tune the policy

Swap behavior is configured in `[orchestration.switching]` in `lychd.toml`:

- Raise `min_priority_for_hard_swap` to make the system more reluctant to swap busy hardware.
- Adjust `drain_timeout_s` to change how long a swap waits for leases to release.
- Mark a support runtime `persistent_resident = true` in its Soulstone Rune's
  `[concurrency]` table to keep it out of every eviction set.

Full settings: the [Orchestration reference](../runes/orchestration.md).

## Verify

- `curl .../orchestrator/queues` shows leases appearing and clearing around a run.
- A `POST /orchestrator/activate` at priority 70 returns 202; at priority 25 against a busy
  coven it returns 409.
- The Nexus reflects the capability moving to **active** after a successful swap.
