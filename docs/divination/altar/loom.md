---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Scroll

Loom lets you read a Pattern revision as a declared Scroll: the stations it contains and the routes they permit. Use it to understand what a chosen workflow could do, then compare that declaration with the evidence of a particular Run in [Orb](orb.md). The current instrument is read-only.

## Find the exact score

After [Altar setup](index.md#bring-one-intent), open `http://127.0.0.1:7134/loom`. The catalogue retains `bridge_chat@1`, `bridge_chat@2`, and
`delegated_rite@1`; the rail pairs each title with its `pattern_id@revision` and marks the default,
other active routes, and retained revisions.

Opening `/loom` selects the configured default and replaces the URL with its exact route. Without
`weaver.bridge`, that is `/loom/bridge_chat/1`; configuring the
[Bridge capability selector](../../sepulcher/extensions/weaver/index.md#choose-a-bridge-capability)
selects `/loom/bridge_chat/2`. An exact revision link continues to open that retained score.

A direct link takes the form `/loom/{pattern_id}/{revision}`. Both parts are required: `/loom/{pattern_id}` is rejected. This lets a review name the revision it concerns instead of leaving its identity to a later selection.

## Read identity, then possibility

Read the three views together:

| View | What to inspect |
| --- | --- |
| Header | `title`, `description`, `pattern_id@revision`, and the UI label `published`. Here, published means registered from source; a durable publication store is not implemented. |
| **Semantic score** | Station and permission counts; each node's `label`, `key`, `kind`, and permitted next station. |
| **Immutable identity** | `checkpoint`, declared `entry`, reviewed `implementation` revision, 64-character `digest`, `trigger`, and plain-text Mermaid `source`. |

The semantic score is the main reading surface. A station and its permitted edge tell you what the score allows. A Run's retained evidence establishes which movements were observed.

**Reveal** and **Hide** under **Diagram lens** control an optional static diagram. It subscribes to no execution and highlights no live station.

The station's kind needs care when interpreting the score. A Spell is an independently identified semantic action, and the accepted grammar places its exact contract in a Scroll-local station. Current manifests do not yet carry independent Spell identity. In particular, the distinct glyph for a `delegate` station does not establish an independent Spell contract or provider-backed execution.

## Compare it with a Run

An Invocation is the admitted Circle; casting performs its Scroll, and the Run is its durable ledger identity. Compare the declaration in Loom with [Orb's retained evidence of traversal](orb.md), accounting for any gaps and omissions there.

Orb can open a score with `?run={run_id}` attached. That query supplies review context; it does not select the Pattern identity. Loom offers **Return to Run in Orb** only after the Run's pinned manifest validates and equals the entire registered score. Matching the digest, Pattern ID, and revision alone is insufficient. The return also preserves the selected event or delegated-job hint. Invalid, unavailable, or mismatched Run context is shown explicitly. Selecting another Pattern discards the Run query.

??? info "Compare the source contract"

    The revision endpoint is `/api/v1/loom/source/patterns/{pattern_id}/{revision}`. The
    current-revision shortcut is `/api/v1/loom/source/workflows/{workflow}`. Their separate source
    namespace keeps `/api/v1/loom/{pattern_id}/{revision}` legal, including a revision named `source`.

## The planned editor {#where-charcoal-must-wait}

Editing, proposal, publication, execution, and layout changes belong to the future design. The [Loom workflow views record](../../state-of-the-work.md#loom-workflow-views) tracks which parts of that design have been implemented.

Future charcoal drafts and grey Spell placements would first produce inert candidates and redacted
resolution reports. Until every exact placement passes [Scroll admission](../../adr/28-workflow.md#spells-scrolls-and-casting),
the whole candidate remains `castable=false`; no placeholder enters the executable Graph.

Follow [ADR 15's editing gate](../../adr/15-frontend.md#loom-workload-and-editing-gate) for the future editor and [Spellweaver](../../sepulcher/extensions/weaver/index.md) for a candidate's passage to a published revision.

## Reading direction

The next reading pass emphasizes the exact revision, registration from source, entry, station
counts, and declared successors before secondary digest and source detail. The current semantic
outline and optional static Mermaid lens remain the starting point. A future computed graph may
become the wide-screen default only when it makes branches, joins, and returns easier to
understand; narrow screens begin with the outline.

Both views must use the same declared nodes and permission endpoints. A station's incoming and
outgoing permissions belong in its detail. Draw a self-loop only when declared, and say **No
outgoing permission declared** rather than inferring execution termination. Do not invent
conditional edge labels, station effects, independent Spell identity, or execution colours from
placement. The read-only graph offers no handles that imply connecting, editing, publishing,
or running the score.

Acceptance case: open a retained exact revision with Run context, find all permitted successors
and a return loop using the keyboard, then disable or fail the diagram. The outline must still
answer the same question and preserve selection. Return to the original Orb event; selecting a
different Pattern discards that context. [Frontend](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction)
owns this target and the shared renderer gates; the mock diagram is not their production receipt.
