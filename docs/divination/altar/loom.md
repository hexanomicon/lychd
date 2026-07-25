---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Score

**Purpose:** The Loom is the Altar's instrument for inspecting a workflow **Pattern**: the named,
validated shape through which an Intent may move. It shows the score. It does not perform the
music.

**Current boundary:** The Loom is a read-only Pattern projection over one fixed registry. Today that
registry contains the `bridge_chat` Pattern. The page can render its name, title, description,
trigger hint, node names, and Mermaid topology, and it can expose the same Mermaid source as plain
text. It does not show capability requirements, typed inputs or outputs, live execution, branch
state, injected memory, or approval metadata, and it cannot draft, publish, mutate, or invoke a
Pattern. It has no Portfolio or Composition projection. [State records the exact Loom
boundary](../../state-of-the-work.md#loom-workflow-views).

**Law:** [ADR 28 — Workflow](../../adr/28-workflow.md) owns the Weaver Pattern;
[ADR 24 — Graph](../../adr/24-graph.md) owns execution topology and checkpoint law. The
[Weaver](../../sepulcher/extensions/weaver.md) page explains how those offices meet, while the
[Composition Portfolio](../../compositions/index.md) maps evolving application parents.

> _“The score may reveal every return and fermata, yet the hall remains silent until an Invocation
> gives it breath.”_

!!! warning "Use the contained Altar"
    The Loom shares the Altar's temporary same-host browser boundary. Keep the listener on literal
    `127.0.0.1`, use the dedicated local browser profile, and do not proxy, tunnel, or port-forward
    it. Begin with the [Altar boundary](./index.md) if that containment is not already in place.

## Composition, Pattern, Loom, Invocation

These names are one movement, not synonyms:

- A **Pattern** is the Weaver-owned workflow definition: identity, typed state and transitions,
  gates, requirements, and the compatibility law for resuming it.
- A **Reference Composition** is the Pattern's operator-visible application parent. One
  Composition may expose several Patterns; the Loom does not yet show that parent relation.
- The **Loom** is a projection of that Pattern. A future editor may hold an inert draft, but the
  browser never becomes the workflow authority.
- An **Invocation** is a runtime act. An admitted Intent selects an exact Pattern, receives a run
  identity, enters the ledger, and is executed by the Vessel's run substrate.

!!! important "A score is not a performance"
    A node appearing in a diagram means the Pattern permits that station. It does not prove that a
    run entered the node, that a branch completed, that a pause is durable, or that an effect was
    authorized. Runtime truth belongs to the run ledger, checkpoints, consent records, and evidence
    events—not to the drawing.

## What the Loom renders now

Under the contained same-host profile, open:

```text
http://127.0.0.1:7134/loom/
```

The Pattern rail currently offers **Bridge Chat**. The legacy implementation replaces the graph
panel through HTMX and gives the selection an honest URL; direct navigation renders the full Altar
page. The source link returns `stateDiagram-v2` text, and bundled browser code renders it locally
rather than sending the graph to an external renderer. This is current evidence, not the accepted
Svelte implementation.

The visible Bridge score contains four possible stations:

1. `WeaveContext` assembles the current bounded context floor.
2. `Converse` leases a granted chat capability and runs the Agent.
3. `AwaitConsent` is entered only when one supported approval must park the run.
4. `ProjectReply` validates the projected fragments and settles the turn.

The diagram is static. It does not light the active node or subscribe to a run, and this page has no
**Run** or **Publish** action. Offer a conversational Intent through the [Bridge entry in the Altar
map](./index.md#the-doors-that-answer-now); do not mistake viewing `bridge_chat` here for invoking
it.

## When the Loom may accept drafts

A future editing surface must preserve the difference between charcoal and law:

1. The browser edits an inert, typed draft with a base revision. It cannot modify the live registry
   or an in-flight Invocation.
2. The Vessel validates identifiers, types, reachability, termination bounds, gates, capability
   requirements, authority, checkpoint compatibility, and extension provenance.
3. Review and any required consent happen before publication, never as a side effect of dragging a
   node.
4. Publication creates an immutable Pattern revision. New Invocations may select it; existing runs
   remain pinned to the revision and checkpoint schema they began with.
5. Removing a revision requires an explicit drain, migration, or honest failure policy for every
   parked run that still names it.

The canonical Loom is a Svelte route. It may use Svelte Flow through one bounded adapter for pan,
zoom, layout, edges, and local draft gestures. It owns presentation state only. Validation,
persistence, authorization, publication, and Invocation remain in the Vessel and Weaver. The
current HTMX/Jinja route is removed when the Svelte route proves equivalent browsing and source
access.

The Loom must also project through a LychD-owned adapter. Today's legacy graph produces Mermaid
through `mermaid_code()`; the newer GraphBuilder generation uses `render()`. Changing an upstream
graph library must not change the Loom's URL, turn a draft into authority, or make a diagram the
checkpoint format.

> _Read the score here. Offer the act elsewhere. Let only the Weaver bind the two._
