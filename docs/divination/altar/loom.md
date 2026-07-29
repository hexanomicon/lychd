---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Score

**Purpose:** The Loom is the Altar's map of authored possibility: the instrument for navigating
the Weaver Portfolio, inspecting an exact workflow **Pattern** revision, and—only after a
declarative contract exists—reviewing inert workflow drafts. It shows the score. It does not
perform the music.

**Current boundary:** The Loom is a read-only projection over exact immutable Pattern manifests in
one fixed registry. Today that registry contains `bridge_chat@1` and `delegated_rite@1`. The page makes the semantic
station/permission outline primary, names its checkpoint schema and manifest digest, and offers
Mermaid as an optional secondary lens with plain-text source. An admitted run pins the same
validated manifest snapshot. The manifest is a declarative score fingerprint, not proof that its
edge list was mechanically recovered from every executable Python return path. Loom does not show
live execution, branch state, injected memory, or approval decisions, and it cannot draft,
publish, mutate, or invoke a Pattern. It has no Portfolio or Composition projection. [State records
the exact Loom boundary](../../state-of-the-work.md#loom-workflow-views).

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
http://127.0.0.1:7134/loom
```

The Pattern rail currently offers **Bridge Chat** and the offline reference **Delegated Rite**.
The Svelte route loads the typed catalogue and
exact manifest from `/api/v1`; `/loom` selects the catalogue default and replaces the browser URL
with `/loom/bridge_chat/1`. `/loom/{pattern_id}` is not an accepted browser deep link. When Orb
opens an exact revision, `?run={run_id}` is disposable review context that lets Loom return to the
selected Run only after the Run snapshot's pinned Pattern id and revision match the displayed
score. Selecting another Pattern drops that context; the query is not part of Pattern identity.
The semantic outline remains readable without JavaScript diagramming. The optional source link returns
`stateDiagram-v2` text, and bundled browser code
renders it locally rather than sending the graph to an external renderer.

The visible Bridge score contains five possible stations:

1. `WeaveContext` assembles the current bounded context floor.
2. `Converse` leases a granted chat capability and runs the Agent.
3. `AwaitConsent` is entered only when one supported approval must park the run.
4. `ProjectReply` validates the projected fragments and settles the turn.
5. `End` is the declared terminal station.

`End` is a declarative outcome in the score, not an executable `BaseNode` occurrence. Pydantic
Graph returns `End` as the graph result, so the Orb observes the final executable station settling
and the run's terminal status rather than inventing a synthetic `End` node occurrence.

The Delegated Rite score contains one sealed delegated station, one result-projection station,
and the declared terminal. Its self-edge records the durable wait/resume possibility; it is not an
expanded hidden subgraph or proof that an effectful provider adapter exists.

The diagram is static. It does not light the active node or subscribe to a run, and this page has no
**Run** or **Publish** action. Offer a conversational Intent through the [Bridge](./bridge.md); do
not mistake viewing `bridge_chat` here for invoking it.

## The Designed Map

Loom's future scope changes through explicit routes, selections, and breadcrumbs—not by assigning
new domain meaning to a wheel-zoom threshold:

1. **Portfolio and Composition:** browse registered Reference Compositions and their Pattern
   families, ownership, enablement, and declared dependencies.
2. **Pattern and revision:** inspect one immutable revision, its stations, branches, joins, gates,
   capability requirements, and continuity law.
3. **Node occurrence:** inspect the referenced Agent or deterministic step, declared input and
   output schemas, Posture and prompt revision references, tools and capability requirements,
   budgets, evaluators, authority requirements, failure shape, and checkpoint boundary.
4. **Draft review:** compare one attributable candidate against its base revision, read validation
   results, and inspect what publication would affect.

An Agent specification is reusable. A node is one occurrence or reference in a Pattern, not the
singleton Agent itself. Likewise, a visual group is not automatically a callable nested Pattern.
LychD has not yet accepted Sub-Pattern invocation, state-transfer, resume, or checkpoint semantics,
so Loom must not manufacture that abstraction from a frame on the canvas.

A `DelegatedAgentNode` is a visually distinct opaque macro-node, not an expandable imported
subgraph. Its inspector names typed inputs and outcomes, eligible Coffin profile, budget, timeout,
provider capability constraints, artifact policy, cancellation/failure routes, and Durable Stasis
boundary. CLI commands, credential values, provider quota posture, and claimed private subagents
do not belong in the Pattern score.

The initial projection recognizes the accepted `delegate` manifest kind and marks that station
with the delegated-node glyph. The complete typed inspector and authoring controls remain staged;
the glyph alone does not prove an effectful runtime is available.

Typed ports may project schemas the Weaver actually declares. A browser connection gesture cannot
claim compatibility; the Vessel must return the validation verdict. Required authority and
checkpoint compatibility belong in explicit labelled panels, not in a glow that implies the run
has already been admitted.

## Charcoal, Law, and Publication

Loom must name the status of what it displays:

- **charcoal** — an attributable inert candidate pinned to a base revision;
- **law** — a validated, reviewed, published immutable Pattern revision; and
- **layout** — disposable browser coordinates, expansion, selection, and viewport state.

A Bridge **Propose in Loom** action may eventually create charcoal with a preview of its source
references and assumptions. Model-authored changes remain untrusted candidates. Dragging,
connecting, grouping, or accepting a suggestion never publishes or invokes anything.

## Before the Loom May Accept Executable Drafts

A future editing surface must preserve the difference between charcoal and law:

1. Weaver must own one canonical declarative Pattern intermediate representation. Current Python
   `BaseNode` graphs are executable source projections, not round-trippable visual documents.
2. That contract must represent stable identity, typed ports, state transfer, reachability,
   termination bounds, effects, gates, capability requirements, authority, provenance, and
   checkpoint compatibility.
3. The browser edits an inert typed draft pinned to a base revision. It cannot modify the live
   registry or an in-flight Invocation, and renderer nodes and coordinates never become the IR.
4. The Vessel validates the complete draft. Review and any required consent happen before
   publication, never as a side effect of a canvas gesture.
5. Publication creates a new immutable Pattern revision. New Invocations may select it; existing
   live and parked runs remain pinned to the revision and checkpoint schema they began with.
6. Removing a revision requires an explicit drain, migration, or honest failure policy for every
   parked run that still names it.

The current Loom is a Svelte route with a read-only Mermaid renderer. A future editor may use
Svelte Flow through one bounded adapter for pan, zoom, selection, edges, and local draft gestures;
`@xyflow/svelte` is not installed in the Altar today. The adapter owns presentation state only.
Validation, persistence, authorization, publication, and Invocation remain in the Vessel and
Weaver.

The Loom must continue to project through a LychD-owned adapter. Changing an upstream graph library
must not change the Loom's URL, turn a draft into authority, or make a diagram the checkpoint
format. Every canvas must have a keyboard-operable outline and inspector; Mermaid/plain-text source
remains a useful current fallback rather than a format to parse into the future editor.

> _Read the score here. Offer the act elsewhere. Let only the Weaver bind the two._
