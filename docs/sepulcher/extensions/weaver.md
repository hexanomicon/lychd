---
title: Weaver
icon: material/state-machine
---

# :material-state-machine: The Weaver: Composition Through Time

**Purpose:** The Weaver is LychD's workflow jurisdiction. It binds agents, deterministic steps,
pauses, evidence, and returns into a validated **Pattern** whose identity can survive long enough to
be inspected, invoked, and—at declared boundaries—resumed.

**Current boundary:** LychD has one internal Pattern, `bridge_chat`, built directly under
`src/lychd/agents/workflows/`. It has typed serializable state, deterministic route-once selection,
a sequential Pydantic Graph, per-step capability leasing, bounded consent parking, and a
run-keyed Postgres JSONB checkpoint adapter. The fixed registry is not populated by the empty
built-in `workflow` extension namespace. There is no Portfolio or Composition registry, schedule
catalogue, Occurrence admission, public contribution API, general workflow editor, Archive-backed
Memory Weaving, Censor, planning engine, parallel Pattern, or live Loom traversal.
[State records the current cognitive adapter and migration
boundary](../../state-of-the-work.md#pydantic-ai-v1-adapter), [graph Stasis
boundary](../../state-of-the-work.md#graph-stasis-consent), and [Loom
projection](../../state-of-the-work.md#loom-workflow-views).

**Law:** [ADR 28 — Workflow](../../adr/28-workflow.md) owns the Weaver's office;
[ADR 24 — Graph](../../adr/24-graph.md) owns topology and checkpoints; and [ADR 20 —
Agents](../../adr/20-agents.md) owns the typed cognitive atom. The living [Composition
Portfolio](../../compositions/index.md) maps application designs above Patterns without becoming
another Covenant.

> _“An Agent is a single note. The Weaver is the weaving: thread remembered across darkness,
> pause held without deceit, and scattered motion returned to one score.”_

## From Portfolio to Invocation

- The **Portfolio** is the set of registered Compositions governed by one Weaver.
- A **Reference Composition** is an operator-visible application with one purpose, Pattern
  catalogue, policy, data, dependencies, and projections. It owns product/application identity.
- The **Pattern** is the validated score owned by the Weaver. It names what may happen and the
  contract by which that shape remains legible.
- The **Loom** is the Altar instrument that projects a Pattern and may later hold inert drafts. It
  never owns execution truth.
- An **Invocation** is the admitted performance of a Pattern. The complete contract pins it to one
  immutable revision. Current `bridge_chat` Invocations have a run id, status, authority context,
  evidence, and a persisted Pattern name; revision identity and checkpoint-schema pinning remain
  part of the contribution horizon.

Graph supplies execution grammar. Weaver owns Pattern validation, registration, selection, and
continuity through time; the Composition supplies the application identity in which one or more
Patterns belong. The Dispatcher binds a logical capability request to an eligible provider. The
Orchestrator alone governs physical readiness and swaps. The Magus owns human judgment; HitL owns
the consent ordering and protocol. The Phylactery owns committed run and checkpoint truth. Weaver
coordinates these offices; it does not impersonate them.

The accepted Portfolio is documented under [Reference
Compositions](../../compositions/index.md). Those pages are architecture targets, not entries in a
working registry.

## The Pattern that has entered matter

The current Bridge Pattern follows a narrow score:

```text
WeaveContext -> Converse -> AwaitConsent? -> ProjectReply -> End
```

`WeaveContext` assembles identity, a bounded environment observation, recent conversation turns,
and the current query. Its Codex and Karma chambers are reserved but empty. It does not yet search
the Archive or inject vector memory.

`Converse` requests a chat grant through the Dispatcher and holds its lease only while the Agent is
running. A hardware-transition signal leaves the node for `GraphRunner` and the Orchestrator; the
Pattern does not operate containers.

`AwaitConsent` is a Gate. When one supported approval call must wait, the run releases its grant,
persists the pause, and exits into Durable Stasis. The current consent shape represents one approval
call per model round; it does not apply one verdict to a hidden bundle of calls.

`ProjectReply` validates named UI fragments, settles the turn, and returns the typed result. The run
worker—not the graph node—commits terminal run status before checkpoint cleanup.

The registry chooses a Pattern once when the Intent is admitted and persists its name. Resume looks
up that same name. A live run is never silently re-routed because another Pattern later wins a
trigger.

That name prevents trigger re-routing inside the current frozen registry; it is not an immutable
revision guarantee across deployments.

## Schedule without a rival scheduler

The future Composition control plane distinguishes three uses of “schedule”:

- **Weaver** owns calendar/event meaning, idempotent Occurrences, logical priority, dependencies,
  overlap, coalescing, and admission of a pinned Pattern revision.
- **Workers and Ghouls** own durable delivery, queue claims, retry, backoff, and crash pickup.
- **Orchestrator** owns physical readiness, prewarming, lease drain, eviction, and model swaps.

A timer submits through the ordinary run-admission boundary. It never calls a Graph node, Agent,
container, or model directly. Multiple Invocations may be logically active while finite iron
serializes their physical work.

## The Fermata: a pause with an owner

A fermata is not “save everything.” It is a declared interruption boundary.

- **Live Stasis** keeps the graph in the resident process and may use in-memory snapshots while the
  Orchestrator converges hardware.
- **Durable Stasis** exits the process and requires a run-owned checkpoint before Reanimation may
  resume it.
- **Terminal truth** is committed to the run ledger before the checkpoint may be deleted.

The current `Workflow` derives its persistence tier from the presence of a Gate. That is a useful
floor, not the final compatibility contract. A graph result does not prove a reboot-safe workflow,
and a process death outside a supported durable boundary may fail the run honestly rather than
replay an effect.

## The Pattern contribution law

Weaver becomes a real extension organ only when a contribution is more than a Python graph object.
Every contributed Pattern must declare and validate:

1. **Identity:** stable Pattern id, immutable revision, owner, provenance, support tier, and
   description.
2. **Typed contract:** input, output, serializable state, error and truthful-noncompletion shapes,
   plus bounded size rules.
3. **Topology:** runtime adapter, entry point, legal transitions, termination bounds, joins, and
   reducer semantics.
4. **Requirements:** logical capabilities, modalities, tools, execution-plane class, budgets, and
   whether a step may wait.
5. **Authority:** required Sigil claims, object/effect policy hooks, consent gates, and the rule that
   no live grant or secret enters durable state.
6. **Continuity:** checkpoint schema, resume cursor, idempotency keys, completed-effect receipts,
   compatible prior revisions, and explicit migrate, drain, or fail behavior.
7. **Projection:** safe title, description, node and edge labels, gates, requirements, and redacted
   metadata for the Loom. Projection data never grants execution.
8. **Evidence:** focused deterministic tests, failure and cancellation tests, serialization corpus,
   and the receipts required by its support envelope.

Contributions enter through an explicit, shaped store at assembly time; LychD must not scan
arbitrary packages. Assembly rejects duplicate ids, ambiguous trigger precedence, unknown runtime
adapters, unreachable stations, unsafe cycles, unserializable state, absent migration policy, and
forbidden effects. The validated registry is then frozen for the process generation.

Pre-v1 built-ins may remain coupled to LychD internals, but that is not permission to expose the
current `Workflow` dataclass as a stable third-party ABI. The public contribution surface should be
harvested only after several built-in Patterns prove the same law.

## Memory and the Censor

The Archivist and Censor remain real offices in the design, but neither is ambient magic.

**Memory Weaving** must call a typed Archive port with a declared query, budget, classification,
provenance, and refusal rule. Retrieved records become explicit context blocks and evidence. A
Pattern may request this preparation; it may not issue hidden SQL or claim that an empty Karma block
contains memory.

The future **Censor** sits only after the Dispatcher and security policy have admitted an external
crossing. It may redact, tokenize, minimize, or reject what was already allowed to leave. It may
never authorize egress, widen a Sigil, invent reversible anonymization, or make a Portal or Legion
safe merely because a workflow named the transform.

## The forked horizon

LychD currently executes the installed `pydantic-graph==1.25.1` legacy `BaseNode` API and adapts its
public persistence interface. That is the checkpoint-bearing path in matter.

The same installed package contains a `pydantic_graph.beta` builder with functional steps,
decisions, broadcast, map, fork, join, reducers, and sibling cancellation. LychD does not execute or
persist those graphs today. Current Pydantic AI promotes GraphBuilder to the top level, but its
parallel runtime still provides no native snapshot persistence; Pydantic AI v2 also removes the
legacy `pydantic_graph.persistence` package on which the present Stasis adapter depends.

Therefore parallelism enters through a separate experimental `WorkflowRuntime` adapter, never as a
side effect of the dependency upgrade. Before fork and join can carry a live Invocation, LychD must
prove stable branch and step ids, deterministic reducer order, bounded concurrency, lease release,
consent behavior, cancellation, completed-effect idempotency, crash points on both sides of a join,
and a LychD-owned durable cursor.

Pydantic AI's Temporal, DBOS, and Prefect capabilities may later wrap bounded Agent activity. They
do not replace the Phylactery run ledger, Ward authority, Dispatcher grants, Orchestrator leases,
HitL ordering, or the Weaver's Pattern revision. An external durability engine is an adapter, never
a second LychD control plane.

## The Visible Score

The [Loom](../../divination/altar/loom.md) currently renders static topology for the fixed registry.
It does not show an active node, branch progress, memory injection, or a waiting run. A future live
view must join a Pattern revision to durable run events by stable run, lane, step, and event ids;
the diagram remains a projection even then.

Likewise, a future editor may shape an inert draft but cannot mutate a live Pattern. Publication
creates a reviewed immutable revision, and every Invocation remains pinned to the revision and
checkpoint schema with which it began.

> _The Weaver does not command the iron, pronounce truth, or counterfeit memory. It keeps the
> thread by which each rightful organ may act—and by which the whole can find its way home._
