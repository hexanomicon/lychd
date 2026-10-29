---
title: Nexus
icon: material/transit-connection-variant
---

# :material-transit-connection-variant: Nexus

Use **Nexus** to understand the current readiness of the iron before changing it. Begin with its
observations, open **Preview** to calculate a nonbinding plan, then choose **Request transition**
only when you intend the real maximum-priority lifecycle mutation. Viewing the board alone
changes no lifecycle state.

Complete [Altar’s startup and local-access steps](index.md#bring-one-intent), then open
`http://127.0.0.1:7134/nexus` within the same-host browser boundary.

## Read the observation before planning

The board loads a timestamped snapshot, refreshes every five seconds, and refreshes when a ticket
settles. Stop if **Runtime admission is contained** appears: runtime admission is fenced.

Managed capabilities are grouped under their Soulstone's first Coven, falling back to the
Animator. A row shows its capability key, normally `{animator}:{family}:{model_id}`, a state chip,
its `checked` time or **freshness unknown**, and **Preview**. Compare `checked` with the board's
snapshot time before treating a row as current.

| Displayed chip | Raw observation |
| --- | --- |
| `active` | `warm` |
| `warming` | `warming` |
| `awaited` | `activatable` on a dynamic capability |
| `fault` | `error` |
| `cold` | Everything else, including `cold`, `unknown`, and non-dynamic `activatable` |

Expand a capability's **Observation details** for the served `warm`, `health`, and `reason`,
Animator, runtime and model. The checked time remains on the row. An unknown value remains unknown even when its compact
chip reads `cold`. `/orchestrator/status` also exposes raw `phase` and process-wide
`mutation_containment`.

**Portals** remain read-only. **Delegated runtime pools** also remain read-only and show
display/delivery state, adapter and transport, owning extension, Coffin profiles, Provider Gate
posture, capacity posture, and declared limitations. These are cached observations, not probes or
reservations. A refresh does not reserve a capability for a later Run.

## Preview the change you intend

Choose **Preview** on the managed capability you intend to use. The target stays visible during
loading, and closing the preview prevents a late response from reopening it. Read the
**Non-binding preview** for `action` (`NO_OP`, `SOFT_SWAP`, or `HARD_SWAP`), `target`, Animator ids
selected for `evict` and `launch`, and `policy cost`.

That cost currently counts planned evictions. It supplies no estimate of VRAM, time, energy,
or topology.

`NO_OP` disables the action. Otherwise, **Request transition** submits the real request at maximum
operator priority. The server recalculates before acting, so the preview reserves nothing and
cannot promise the same eviction set.

Evictions are named by Animator while board rows are keyed by capability. A Coven cannot hold
two conflicting Animators, so an eviction lands on another card, not the previewed one. The
current board does not mark those affected rows from the plan; read the served eviction identities
directly.

## Keep one request identity through uncertainty

The browser allocates a request id before submission. If the response is uncertain, keep Nexus
open and choose **Request transition** again for the same target to reuse that id. Admission
reserves the first target before task launch. PostgreSQL preserves this fence across Vessel
restarts; the memory profile preserves it for one process. Reusing the id for a different target
is rejected.

A retry returns the live ticket if one is still available. When its ticket has expired or its
process has ended, the same request id is refused without relaunch: the remaining ticket state
cannot establish the physical outcome.

Nexus keeps that refused id while the page stays open. Leaving or reloading discards the prepared
retry, so cancel the navigation warning while the outcome remains unknown. PostgreSQL retains
the admission fence, not the browser's retry state. Keep the original identity until the physical
outcome is reconciled; losing the answer does not justify creating another physical request.

## Follow the ticket and the physical observation

An accepted request returns HTTP 202 with a process-local ticket:

| Ticket | What it establishes |
| --- | --- |
| `warming` | No terminal task result has been observed. |
| `settled` | The task returned; Nexus refreshes the board. |
| `failed` | The task raised or was cancelled. |

The **Request ticket** keeps its target, current transition phase, and full request id visible
even while you preview a different target. **Request outcomes** also retains full identities after
uncertain submission, including after you close the preview.

Terminal ticket truth remains for a 60-second reconnect window by default. If the bounded store
is full, it refuses new work before launch instead of evicting active or fresh-terminal tickets.
Tickets provide no cancellation, durable history, or restart recovery. Durable admission prevents
duplicate effects but cannot settle, fail, or resume a ticket that was lost.

**Latest transition observations** shows up to 24 newest retained requests from Run and operator
sources. Select one, or open `/nexus?transition={request_id}`, to inspect `request`, `source`,
`target`, `phase`, chosen `action`, Run `occurrence` when supplied, `physical` transition identity,
and compensation identity labeled `restoration`.

Its phases are `requested`, `arbitrating`, `draining`, `actuating`, `verifying`, `compensating`,
`completed`, `declined_no_effect`, `failed_restored`, `cancelled_restored`, `contained_uncertain`,
or `failed`. Ticket settlement and these physical observations answer different questions; read
both before judging what happened.

An Orb link may add `event={event_id}`. Nexus keeps it only while that request is selected and,
when Run correlation exists, offers the return to `/orb/{run_id}?event={event_id}`. Closing the
inspector or selecting another transition drops the event context.

## When the accounts disagree

If a chip, raw status and host disagree—or a lost ticket leaves the outcome unknown—follow the
[existing runtime-transition contract](../../sepulcher/animator/runtime-transitions.md#the-transition-contract)
and its [Host Reactor observations](../../sepulcher/animator/runtime-transitions.md#switching-settings).
Keep the original request identity while reconciling the physical outcome. A contained or
unresolved result needs operator recovery; another transition request cannot clear that uncertainty.
Reconcile a unit/probe mismatch before retrying.

The current surface is a grouped observation board, preview, request ticket, and latest-observation
inspector. Narrow screens place details in the reading flow. It shows no queue order, leases,
GPU/VRAM/topology/thermal pressure, durable history, configuration editing, provider accounts,
billing, or credentials.

Its semantic board remains primary; any future body map starts as a read-only lens over validated observations. The
[Frontend Covenant](../../adr/15-frontend.md#decision-lock-and-reopening-gate) owns that design and
its admission gates.

## Reading direction

For interface review and design, use the following composition and acceptance case.

The current layout keeps snapshot time and containment first, then grouped observations
with their freshness, one selected preview, and its explicit request. Aligned eviction and
launch lists make the consequence easier to compare than an inferred topology graph. Preserve
the distinction between a capability row and the Animator that would be evicted; affected-row
highlighting requires exact identity mapping from the served data.

Ticket outcome and physical observation stay separately identified by request, target and time.
A recently observed phase is not a complete progress rail, and the latest bounded list is not
full history. Unknown or stale states remain recognizable even when a compact chip merges
several raw values. New memory, temperature, duration, impact, or health graphics need actual
observations and their interpretation before they gain a place on the board.

Acceptance case: inspect a proposed target while an older request is observed as verifying,
then lose the response to the new request. Keep both identities clear, retain the original
request, and avoid treating a settled ticket as physical success or making a fresh request to
cover the unknown result. Check keyboard return from the inspector and a narrow layout with
long Animator ids. These [presentation targets](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction)
do not deliver durable observation history, restart recovery, or a body map.
