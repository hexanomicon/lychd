---
title: Orb
icon: material/crystal-ball
---

# :material-crystal-ball: Orb

**Purpose.** The **Orb** is the Altar instrument for scrying visible execution evidence: first one
selected **Invocation** with forensic clarity, and later a bounded field of active, waiting, and
recent work when that wider view can reduce operator attention without claiming omniscience.

**Current boundary.** `/orb/{run_id}` now renders one selected Invocation from a bounded
server-owned snapshot. It shows ordered retained status, node-occurrence, Dispatcher-grant, and
Orchestrator-transition evidence; the exact pinned Pattern reference when its manifest validates;
explicit cursor coverage, gaps, omissions, and capture class; and links back to Bridge, Loom, and
Nexus. Long runs use explicit bounded pagination, selected events are addressable by event id in
the URL, and narrow screens open their details as a focused sheet. `/orb` deliberately asks
the Magus to select a run from Bridge because there is no
authorized run index yet. This view has no live tail, durable native Oculus store, health model,
graph canvas, or multi-run field. [State owns the exact Orb
boundary](../../state-of-the-work.md#orb-instrument).

**Law.** The Orb is a projection, never a second source of truth. **Scrying** names the
disciplined act of looking into it. The
[Oculus](../../sepulcher/extensions/oculus.md) owns the evidence model and future read service; the
[Phylactery](../../sepulcher/phylactery/index.md) owns committed run truth at its supported
boundaries; the [Weaver](../../sepulcher/extensions/weaver.md) owns Pattern movement;
[Context](../../adr/21-context.md) owns the active cognitive field; and the
[Mirror](../../sepulcher/extensions/mirror.md) owns identity continuity. The glass may reveal their
evidence. It may not impersonate any of them.

> _“The eye gathers light. The Orb gives the light a surface. Neither invents what stands before
> it.”_

## The Orb and the Eye

The **Oculus** is the observing organ. The **Orb** is the Altar instrument. **Scrying** is the
disciplined act of looking into the Orb through the evidence the Oculus can lawfully provide. This
three-part distinction protects the Work from a subtle corruption: a beautiful display can feel
more authoritative than the event it depicts. In LychD, the image always points back to the run,
step, grant, consent record, transition, or retained trace that produced it.

Scrying through the Orb is therefore not a continuous transcript of a hidden inner voice. It is the legible,
partially ordered shape of observed work: an Intent entering a run, graph movement becoming steps,
a tool call meeting validation, a lease meeting physical pressure, a decision entering Stasis, and
an outcome returning with evidence. Where evidence is absent, the instrument must show absence
rather than complete the vision from inference.

The Weaver's design also reserves an internal **Scry** before a reasoning step: it would retrieve
relevant Karma into Context. That memory-preparation path is not implemented today. The same verb
names two related acts—preparing the field and witnessing its movement—but the operator-facing
instrument is always the **Orb**.

## The First Invocation

The domain act is an **Invocation**; the current UI and API call its tracked execution a **Run**.
The delivered selected-Run surface is deliberately smaller than the imagined sky. It
provides:

1. one selected Run with stable run and event identity, plus node occurrence, dispatch capability,
   and transition identities where the producing contracts supply them;
2. one producer-local ordered event list with an explicit ledger head, page boundary, pagination,
   and visible gaps, without
   fabricating a total order across independent producers;
3. a link to the exact immutable [Loom](./loom.md) Pattern revision only while the run's pinned
   manifest remains valid;
4. a URL-stable selected-event inspector and a direct [Nexus](./nexus.md) transition link where exact
   correlation exists; that hop carries the event id so Nexus can return to the same selection; and
5. explicit `process local`, `durable best effort`, omission, and `no live tail` labels.

The exact Loom link carries `?run={run_id}` as disposable review context. Loom validates the Run
snapshot against the displayed Pattern id and revision before showing a return link, and Pattern
navigation drops the query. The query never changes Pattern identity or revision.

An exact selected event uses `/orb/{run_id}?event={event_id}`. The URL identifies evidence; it does
not improve its capture class or retention.

An authorized searchable run list, graph-shaped evidence view, tool-call/artifact lineage, native
Oculus durability, and a bounded live tail remain later work.

The ordered list is primary today. Any later timeline or canvas remains a peer projection, not a
replacement caption. Current, terminal, waiting, stale, redacted, dropped, and unknown conditions
must remain legible without color or motion. Live process signals and committed facts are labelled
separately.

## Designed: Ask Why It Waits

The current Orb exposes the recorded generic status and phase only. A future **Why waiting?**
explanation may follow an explicit blocker relation to its owner. Where the owning contracts
eventually support it, the detail names:

- the wait and owning office;
- required and observed state;
- live or Durable Stasis;
- capability, queue, lease, consent, dependency, or peer relation;
- retryability and freshness; and
- the separate instrument or action that may lawfully respond.

A generic status string does not authorize the client to infer this path. When the blocker is not
known, the Orb says **unknown**.

A **time lens** may initially filter the retained event window while preserving occurred,
observed, and ingested times. It may claim historical replay or scrubbing only after a versioned
snapshot-plus-event contract can reconstruct the supported past state with visible gaps. Replaying
animation from the current process-local stream would not prove recoverability or complete
history.

## The Later Living Sky

After the selected-Invocation view and Oculus read model prove their semantics, the Orb may add one
calm, bounded field of multiple Invocations. In that view, “all active” means only work that is:

- visible to the current authorized principal;
- observed as active, waiting, or terminal-recent;
- inside an explicit time window and declared status or Pattern filters;
- under a declared cardinality, clustering, and pagination limit; and
- accompanied by visible truncation, sampling, staleness, redaction, and evidence gaps.

At wide scope, labelled constellations answer _what needs attention?_ Selecting one Invocation
opens its lanes, steps, branches, joins, waits, and evidence without leaving the Orb. Scope changes
through explicit controls, URLs, and breadcrumbs. Wheel zoom changes geometric scale only; it does
not silently replace the domain query.

The living sky is not a neural-network claim and not a literal battlefield. A brief branch flash
may acknowledge one recorded spawn event, but continuous lightning, token sparks, ambient pulses,
or automatic layout movement cannot stand in for execution. Existing objects retain stable
positions where practical so new evidence does not destroy spatial memory. Motion is pausable, and
reduced-motion mode uses static sequence and status markers.

## Relations, Affordances, and Thought

Every visible edge must state what it means. At minimum, the contract distinguishes containment,
Pattern permission, correlation, explicit causal parentage, waiting, grant/lease use, artifact
production, lineage, and evaluation. Temporal adjacency and a shared trace identifier do not prove
causality.

For a selected Agent step, a labelled detail panel may distinguish:

1. **Pattern-permitted** tools and handoffs;
2. **effectively offered** surfaces after current Sigil, provider, and policy resolution;
3. **requested** calls the Agent actually emitted;
4. **admitted** work accepted by the owning validator/runtime; and
5. the recorded **outcome**.

Optional ghosting is allowed only when the state remains explicit. Grey never means “the model
secretly considered this.” At wide scope, unused affordances are omitted.

The Orb may show observable cognition that was deliberately emitted and admitted for capture:
declared or current objectives, progress or strategy summaries, uncertainty, admitted context
references, retrieved memories with provenance, tool/handoff requests, evaluations, candidates,
and artifacts. These are first-person testimony or operated telemetry with named provenance—not
hidden chain-of-thought or a mind-reading claim. Content, arguments, and context remain governed by
capture, redaction, privacy, and retention policy.

A document-rewrite or concept-coverage result belongs to
[Riddle's rubric projection](../../sepulcher/extensions/riddle.md#vii-rubric-coverage-is-evidence-not-geometry):
The Orb may place its criterion-by-artifact matrix beside the selected Invocation and link each
verdict to evidence. It does not turn workflow topology into a three-dimensional ontology or treat
concept proximity as proof of coverage.

## Projection and Annotation Law

The canonical Svelte route may own selection, disposable layout, pan/zoom, filters, paused
playback, and other temporary presentation state. It may not own run transitions, persistence,
authorization, or consent. Snapshots and semantic JSON SSE come from the Vessel; model output is
never interpreted as markup. Graph rendering remains behind one LychD-owned adapter so the Oculus
contract is not coupled to Svelte Flow or another canvas library.

The Orb shows only the selected run's recorded capability/grant/provider relation; the durable
Animator inventory belongs in Nexus rather than occupying this field. Ordered queue positions
appear only when the queue contract supplies exact identity and order; otherwise the Orb shows
bounded depth or **order unknown**.

Future annotations are separate durable records anchored to exact run, step, event, tool-call,
artifact, or gap identities with author, privacy class, timestamps, retention, and authorization.
They never rewrite evidence or trigger retry, cancellation, approval, publication, or transition
as a side effect. **Pin and Ask** may create a new, previewed Bridge Intent instead.

## Witness Without Possession

The deepest purpose of scrying is not surveillance. It is answerability. A recurrent system can
repair only what it can return to with enough identity and evidence to say: _this occurred here,
under this authority, with this consequence_. The Magus does not gain omniscience at the Orb. The
Magus gains a bounded view whose limits are visible.

Use [Bridge](./bridge.md) to select or create the Run, **look into the Orb** to scry its bounded evidence,
[Loom](./loom.md) to read the permitted score, and [Nexus](./nexus.md) to inspect correlated
physical-transition truth.

> _See what was retained. Name what was not. Never complete the vision by invention._
