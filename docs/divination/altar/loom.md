---
title: Loom
icon: material/vector-polyline
---

# :material-vector-polyline: Loom: The Visible Scroll

Open Loom when you want to understand what a workflow permits. It presents one exact Pattern
revision as a declared Scroll: its stations and the routes between them. Once you can read that
score, compare it with a particular Run's evidence in [Orb](orb.md) or use Evaluation to review
a retained output. The score remains read-only.

## Find the exact score

After [Altar setup](index.md#bring-one-intent), open `http://127.0.0.1:7134/loom`.
Loom selects the configured default, then puts the exact Pattern and revision in the address.
For example, the unconfigured Bridge opens at `/loom/bridge_chat/1`. Copy the full address
when you want someone to review the same score. A link without the revision is rejected.

Look at the labels beside `pattern_id@revision`. **Default** identifies the ordinary route for
a new request. Other selectable entries can show **Route** with its rank or **Active route**.
**Retained** means the revision is still available to inspect after routing changes. Use [Weaver's admission table](../../sepulcher/aspects/weaver/pattern-lifecycle.md#identity-before-motion)
to check which Bridge or delegation score a configuration selects.

Selected extensions and connected profiles can add exact inspection-only scores through the same
catalogue. **Inspection binding** names the source, Registrant, profile, generation and publication
meaning. **Observation only · not executable in this Vessel** does not change local routing or
permit admission or resume. An executable native entry is separately labelled **Executable in
this Vessel**. The complete remote source/profile/generation selection stays in its detail link;
an unavailable or changed binding is reported instead of opening a similarly named score.

These descriptions come from the same manifest as the source profile. Profile metadata does not
change that Pattern's checksum. Registering a descriptor does not publish executable code or
activate an extension. [Oculus](../../sepulcher/aspects/oculus.md#connected-components-and-activity)
owns the bounded source handoff used by the first connected profile.

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

## Review a retained output

An exact revision's **Evaluation** view offers **Manual output review**. It is a retrospective
review of a historical answer, with no new execution. Begin with a bounded goal, the criteria and
evidence needed to judge it, and your declared reviewer name. Freeze that contract before loading
the output for this review; this does not claim that the criteria preceded the original Run.

Choose an exact Run whose full pinned manifest and inspection binding match the displayed score.
The review reads the matching retained agent turn from its exact Session. Its quoted words,
supplied identities, timestamp and content digest identify the source. A missing or ambiguous
answer stays unavailable; the review never substitutes the most recent answer or a process-local
Orb projection.

For each criterion, inspect what is actually present, then enter your verdict, reason and
supporting quotation or evidence limitation. `UNKNOWN` is the starting verdict. A completed Run
can contain an incorrect answer; an output that claims an effect does not prove the effect
occurred. Source Run status and your review's completion remain separate from quality verdicts.

Finishing freezes a local review record. Regrading creates another revision with the same frozen
criteria and output. To change criteria or reviewer, start a new review and freeze a new contract.
Export JSON or readable Markdown to keep the exact source, criteria, judgments, limitations and
declared reviewer together. Reviews last only in this open browser document and are not saved to
Vessel or localStorage; export before leaving. The reviewer name is self-declared, not authenticated
attribution. Current access refusal clears protected captures and fences late reads.

This is an authored review over retained output. It does not run a Trial Suite, establish new
cost/latency observations, prove that another workflow revision improves outcomes, promote a
model, or create a durable Drift Outcome. [Drift](../../adr/34-drift.md) owns those evaluation
contracts. Orb remains the place to inspect the source Run's bounded execution evidence.

## The planned editor {#where-charcoal-must-wait}

Editing, proposal, publication, execution, and layout changes belong to the future design. The [Loom workflow views record](../../state-of-the-work.md#loom-workflow-views) tracks which parts of that design have been implemented.

Future charcoal drafts and grey Spell placements would first produce inert candidates and redacted
resolution reports. Until every exact placement passes [Scroll admission](../../adr/28-workflow.md#spells-scrolls-and-casting),
the whole candidate remains `castable=false`; no placeholder enters the executable Graph.

Follow [ADR 15's editing gate](../../adr/15-frontend.md#loom-workload-and-editing-gate) for the future editor and [Spellweaver](../../sepulcher/aspects/weaver/index.md) for a candidate's passage to a published revision.

## Reading direction

The exact revision, source registration, entry, station counts, and declared successors should
be legible before the reader opens digest or source detail. The computed graph has an outline
and station inspector beside or below it as space permits. That outline must answer the same
question without pan or zoom gestures.

The proposed [shared workflow station inspector](index.md#shared-workflow-station-inspector)
opens on the station's definition in Loom.

The future workflow map expands nested declared subgraphs until each agent can be inspected.
Open one group to work within it, or expand the complete declared graph. Context policy and
[Evaluation](../../adr/34-drift.md#evaluating-a-workflow-change) follow the exact revision.
For example, a policy could request a retained rollout decision with its source.
[Archive](../../adr/27-memory.md) governs eligibility, and
[Context](../../adr/21-context.md#explicit-archive-projection) governs assembly for the Invocation.
The current Score reads supplied stations and permissions. Evaluation supports retrospective
[manual review](#review-a-retained-output).

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
