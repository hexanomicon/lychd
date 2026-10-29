---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Scroll

Open Loom when you want to understand what a workflow permits. It presents one exact Pattern
revision as a declared Scroll: its stations and the routes between them. Once you can read that
score, compare it with a particular Run's evidence in [Orb](orb.md). Loom is currently read-only.

## Find the exact score

After [Altar setup](index.md#bring-one-intent), open `http://127.0.0.1:7134/loom`. The catalogue retains `bridge_chat@1` through `bridge_chat@4` and
`delegated_rite@1` and `delegated_rite@2`; the rail pairs each title with its `pattern_id@revision` and marks the default,
other active routes, and retained revisions.

Opening `/loom` selects the configured default and replaces the URL with its exact route. Without
`weaver.bridge`, that is `/loom/bridge_chat/1`; configuring the
[Bridge capability selector](../../sepulcher/extensions/weaver/index.md#choose-a-bridge-capability)
selects `/loom/bridge_chat/2`; the
[public-note configuration](bridge.md#public-note-answers) selects
`/loom/bridge_chat/3`. The [Scout public-page profile](../../sepulcher/extensions/scout.md#public-page-answers)
selects `/loom/bridge_chat/4`. An exact revision link continues to open that retained score.

A direct link takes the form `/loom/{pattern_id}/{revision}`. Both parts are required: `/loom/{pattern_id}` is rejected. This lets a review name the revision it concerns instead of leaving its identity to a later selection.

## Read identity, then possibility

Read the views together:

| View | What to inspect |
| --- | --- |
| Header | `title`, `description`, `pattern_id@revision`, declared entry, and **Registered from source**. A durable publication store is not implemented. |
| **Pattern graph** | Pan and zoom through the declared score. **Whole Pattern** folds it into one group; **Stations** reveals the declared stations and permissions. |
| **Graph outline** | Station and permission counts; each node's `label`, `key`, `kind`, declared entry and permitted successors. Select a station to inspect it. |
| **Selected station** | Incoming and outgoing permissions with endpoint labels, keys and the declared relation; self-loops are explicit. **Back to selected station** returns keyboard focus to its row. |
| **Identity & source** | Expand the disclosure for `checkpoint`, declared `entry`, reviewed `implementation` revision, 64-character `digest`, `trigger`, and plain-text Mermaid `source`. |

The workflow canvas and semantic outline derive the same stations and permissions, including
declared wait loops, from the exact manifest. Zoom changes whole-Pattern and station detail;
explicit buttons offer the same operation. The shared Svelte Flow renderer supplies a read-only
computed layout. It subscribes to no execution and highlights no live station. A Run's retained
evidence in Orb establishes which movements were observed.

Hover or keyboard focus on a canvas node reveals its meaning and identity without selecting it.
Escape closes that preview. The same graph adapter serves Orb; a plain canvas background keeps
the score readable, while declared kinds remain distinct from inferred agent or tool identities.

The selected station and its outline remain usable if the graph fails. **No
outgoing permission declared** describes the manifest; it does not infer that execution has
terminated. A failed score read offers **Retry reading Pattern**, preserving the requested exact
revision instead of silently selecting another one.

Read a station's kind as a declaration in the current manifest. The accepted grammar also gives
a Spell its own identity and places that exact semantic-action contract in a Scroll-local
station. Current manifests do not yet carry that independent Spell identity. Thus a `delegate`
glyph identifies a station kind; it cannot establish an independent Spell contract or prove
provider-backed execution.

## Compare it with a Run

An Invocation is the admitted Circle; casting performs its Scroll, and the Run is its durable ledger identity. Compare the declaration in Loom with [Orb's retained evidence of traversal](orb.md), accounting for any gaps and omissions there.

Orb can attach `?run={run_id}` when it opens the score. This supplies the Run you are reviewing;
the path still selects the Pattern identity. Before offering **Return to Run in Orb**, Loom
validates the Run's pinned manifest and requires it to equal the entire registered score. Matching
only digest, Pattern ID, and revision is insufficient. It also checks that the separately fetched
displayed score still has the validated digest.

A valid return preserves the selected event or delegated-job hint. Invalid, unavailable, or
mismatched Run context remains explicit. Choosing another Pattern discards the Run query.

??? info "Compare the source contract"

    The revision endpoint is `/api/v1/loom/source/patterns/{pattern_id}/{revision}`. The
    current-revision shortcut is `/api/v1/loom/source/workflows/{workflow}`. Their separate source
    namespace keeps `/api/v1/loom/{pattern_id}/{revision}` legal, including a revision named `source`.

The fixed trusted source-browser [journey](../../state-of-the-work.md#current-evidence-envelope)
checks the exact `bridge_chat@2` score and keyboard return to its Run. It does not qualify the
planned editor, every graph interaction or the shared renderer's cross-engine lifecycle gate.

## The planned editor {#where-charcoal-must-wait}

Editing, proposal, publication, execution, and layout changes belong to the future design. The [Loom workflow views record](../../state-of-the-work.md#loom-workflow-views) tracks which parts of that design have been implemented.

Future charcoal drafts and grey Spell placements would first produce inert candidates and redacted
resolution reports. Until every exact placement passes [Scroll admission](../../adr/28-workflow.md#spells-scrolls-and-casting),
the whole candidate remains `castable=false`; no placeholder enters the executable Graph.

Follow [ADR 15's editing gate](../../adr/15-frontend.md#loom-workload-and-editing-gate) for the future editor and [Spellweaver](../../sepulcher/extensions/weaver/index.md) for a candidate's passage to a published revision.

## Reading direction

For interface review and design, use the following composition and acceptance case.

The exact revision, source registration, entry, station counts, and declared successors should
be legible before the reader opens digest or source detail. The computed graph has an outline
and station inspector beside or below it as space permits. That outline must answer the same
question without pan or zoom gestures.

Judge every mark against the manifest. Both views share declared nodes and permission endpoints;
station detail exposes incoming and outgoing permissions. Placement cannot supply a conditional
edge label, station effect, independent Spell identity, or execution colour. Handles must not
imply connecting, editing, publishing, or running this read-only score.

Acceptance case: open a retained exact revision with Run context, find all permitted successors
and a return loop using the keyboard, then fail the graph. The outline must still
answer the same question and preserve selection. Return to the original Orb event; selecting a
different Pattern discards that context. [Frontend](../../adr/15-frontend.md#reading-hierarchy-and-visual-direction)
owns this target and the shared renderer gates; installation does not establish the required
cross-engine lifecycle receipt. [State](../../state-of-the-work.md#loom-workflow-views) keeps that
qualification separate from the available canvas.
