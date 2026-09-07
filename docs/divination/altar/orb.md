---
title: Orb
icon: material/crystal-ball
---

# :material-crystal-ball: Orb

Before trusting a result, find the Run that produced it and the limit of what was retained.
Looking through the **Orb** is **scrying**: inspecting ordered structural evidence with its gaps
still visible.

Choose **Look into the Orb** at a Bridge result, or open `/orb/{run_id}`. The bare `/orb` route
sends you toward Bridge; there is no authorized searchable Run list. During this browser visit,
the shell’s **Orb** tab returns to the last selected Run and event.

## Establish the account you are reading

Confirm the **Run id**, canonical status, and capture class in the header. The Run owns ledger
status. The Orb shows the bounded trace its sources can supply and cannot replace Run, consent,
grant, effect, or artifact truth.

**[Oculus](../../sepulcher/extensions/oculus.md)** names the body’s evidence service; **Orb** is
its Altar surface. Native durable Oculus storage is
not delivered. Current evidence is available through this running Vessel and is labeled
`process local` or `durable best effort`.

Then read the coverage strip:

| Label | Boundary |
| --- | --- |
| **snapshot** | The snapshot being inspected. |
| **retained through** | The retained ledger head. |
| **loaded through** | How far this page has loaded. |
| **live updates** | Current snapshots say `not available`. |

**Refresh** requests a new bounded snapshot. The first page contains up to 100 evidence records;
**Load more retained evidence** requests another page while more remain. A visible `#start–end`
gap means an unknown or omitted interval. The Orb does not infer why those sequence numbers are
absent.

## Locate the event

Select a row to open **Selected event**. Its stable review URL is
`/orb/{run_id}?event={event_id}`. The inspector shows recorded sequence, kind, subject, phase,
occurrence, and capture class.

If the linked event lies beyond the loaded page, load more. If it is no longer retained, the Orb
says so. To investigate a wait, inspect its recorded status, phase, subject, occurrence, and
transition correlation. These observations may leave the cause unknown; the Orb has no
**Why waiting?** analysis. Follow [Stasis and return](../../sepulcher/extensions/weaver/stasis-and-return.md)
for the recorded wait's owner and return boundary, or
[Reanimation](../../sepulcher/phylactery/reanimation.md#reanimation-a-new-vessel-judges-durable-truth)
when the Vessel has died.

When delegated work exists, **Delegated jobs** shows at most the newest 32 summaries, each with
its `AgentJob` identity, runtime, Coffin profile, station, status, bounded-result presence,
artifact-reference count, and up to the latest 64 lifecycle events. Older omitted jobs and
truncation are explicit. Prompts, output text, and private errors are not exposed.

## Follow a relation only where it was recorded

**Bridge** returns to the owning conversation and focuses the exact Run’s turn when available.
An unavailable turn is reported. **Exact Pattern** opens [Loom](loom.md) only when the Run's pinned
manifest validates. Its Run and selected-event query preserves the return destination; neither
changes Pattern identity.

A selected event with exact transition correlation offers **Open transition in Nexus** and
carries the selected event id. The link supplies a relation worth inspecting; viewing it requests
no mutation. [Nexus](nexus.md) keeps any lifecycle decision separate.

Selection and pagination leave Run state unchanged. To inspect another Run, return through
Bridge. The current Orb offers no annotation, retry, cancellation, approval, publication or
transition action. Multi-Run fields, graph canvases, time lenses, historical replay and live tails
also remain outside this surface.

## Witness without possession

Evidence ends where capture, retention, or loading ends. Future graph views must preserve those
limits; [Frontend's folding law](../../adr/15-frontend.md#folding-not-scale) governs their groups,
expansion, and faithful sequence.

That projection is designed. [Oculus](../../sepulcher/extensions/oculus.md) owns the evidence office.
Neither a richer view nor more retained rows can authorize the Orb to invent the
missing part of a history.

## Reading direction

The planned hierarchy brings Run identity, canonical status, capture class, snapshot time,
retained and loaded boundaries, omissions, and unavailable live updates before the records.
Delegated-job detail unfolds after that account, so a large job collection cannot hide the
limits that qualify all evidence.

A future lane view can arrange records by their supplied subject and sequence. Equal spacing
means order, not elapsed time; proximity does not establish causality. Unknown subjects remain
unknown. Gaps span the account instead of being bridged by an invented connector. Delegated-job
events retain their own sequence unless the server supplies a Run correlation. List and lanes
preserve identical record selection and omissions. Complete fold membership, counts and bounded
expansion need the [server-owned folding contract](../../adr/15-frontend.md#folding-not-scale).

Acceptance case: open an event beyond the first page, distinguish not-yet-loaded evidence from
an unretained interval or failed read, inspect the exact score or correlated physical transition,
and return to the same selected event using only the keyboard. A narrow display should start
with a readable list. Efficient direct event seeking needs a separate retrieval contract; the
current path remains loading subsequent pages. This is a [presentation
target](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction), not a delivered graph,
live tail, complete trace, or execution control.
