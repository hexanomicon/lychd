---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

The **Nexus** is the local readiness and transition board. Viewing changes nothing.
**Preview** calculates a non-binding plan; **Request transition** is a real maximum-priority
lifecycle mutation.

## What the board witnesses

The board loads a timestamped snapshot, refreshes every five seconds, and refreshes after a ticket
settles. A containment alert appears when runtime admission is fenced.

Managed capabilities are grouped under the Soulstone's first Coven, falling back to the Animator.
Each row shows:

- the capability key, normally `{animator}:{family}:{model_id}`;
- its state chip and `checked` time, or **freshness unknown**; and
- **Preview**.

**Portals** use the same observation row but remain read-only. **Delegated runtime pools** are also
read-only and show display/delivery state, adapter and transport, owning extension, Coffin
profiles, Provider Gate posture, capacity posture, and declared limitations.

This is cached observation, not a probe or reservation. Refreshing the board does not reserve what
a later Run will receive.

## Read the state without guessing

The chip mapping is exact:

- `active` ← raw `warm`;
- `warming` ← raw `warming`;
- `awaited` ← raw `activatable` on a dynamic capability;
- `fault` ← raw `error`;
- `cold` ← every other raw state, including `cold`, `unknown`, and non-dynamic `activatable`.

For the distinction hidden by the chip, `/orchestrator/status` exposes raw `phase`, `warm`,
`health`, `reason`, and process-wide `mutation_containment`. Compare the row's `checked` time with
the board snapshot time before treating it as current.

## Observation and control are different rites

Choose **Preview** on a managed capability. The **Non-binding preview** drawer shows:

- `action`: `NO_OP`, `SOFT_SWAP`, or `HARD_SWAP`;
- `target`;
- Animator ids selected for `evict`;
- Animator ids selected for `launch`; and
- `policy cost`, currently the number of planned evictions.

`NO_OP` disables the action. Otherwise **Request transition** submits a real request at maximum
operator priority. The server recalculates the plan before acting, so preview is neither a
reservation nor a promise of the same evict set. Policy cost is not VRAM, time, energy, or topology.

## What a swap ticket proves

The accepted request returns HTTP 202 with a process-local ticket:

- `warming` — no terminal result observed yet;
- `settled` — the task returned and Nexus refreshes; or
- `failed` — the task raised or was cancelled.

The ticket strip shows target, current transition phase, and request id. Terminal ticket truth is
retained for a 60-second reconnect window by default. The bounded store refuses a new request
before launch rather than evicting active or fresh-terminal tickets. Tickets have no cancel action,
durable history, or restart recovery.

**Latest transition observations** shows up to 24 newest retained requests from both Run and
operator sources. Select one, or open `/nexus?transition={request_id}`, to inspect:

- `request`, `source`, `target`, `phase`, and chosen `action`;
- Run `occurrence`, when supplied;
- `physical` transition identity; and
- compensation identity, labelled `restoration`.

Observed phases can be `requested`, `arbitrating`, `draining`, `actuating`, `verifying`,
`compensating`, `completed`, `declined_no_effect`, `failed_restored`, `cancelled_restored`,
`contained_uncertain`, or `failed`.

An Orb link may add `event={event_id}`. Nexus preserves it only while that request is selected and
returns to `/orb/{run_id}?event={event_id}` when Run correlation exists. Closing the inspector or
selecting another transition drops the event context.

## The Designed Body Map

No graph-shaped body map is delivered. Nexus is a card board, preview drawer, ticket strip, and
latest-observation inspector. It does not show queue order, leases, GPU/VRAM/topology/thermal
pressure, durable history, configuration editing, provider accounts, billing, or credentials.

## Enter after first life

After the four observations and same-host browser boundary in
[The Awakening](../../summoning.md#the-awakening) agree, open:

```text
http://127.0.0.1:7134/nexus
```

1. Confirm the snapshot and each row's `checked` time.
2. Stop if **Runtime admission is contained** appears.
3. Choose **Preview** and read action, target, evictions, launches, and cost.
4. Request only the transition you intend to make real.
5. Watch the ticket reach `settled` or `failed`, then inspect its latest transition observation.
6. If you arrived from Orb, use **Return to evidence in the Orb**.

If the chip, raw status, and host disagree, diagnose the runtime; a transition request is not a
way to make the board look calm.
