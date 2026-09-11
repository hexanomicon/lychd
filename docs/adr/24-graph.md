---
title: 24. Graph
icon: material/graph-outline
---

# :material-graph-outline: 24. Graph

!!! abstract "Context"
    An Invocation must survive deterministic work, capability waits, consent, and bounded foreign
    labor. That requires a recoverable control boundary, not a process image or a second authority
    ledger.

## Decision

LychD uses Pydantic Graph v2's native GraphBuilder with serial BaseNode stations. A Workflow binds typed Graph,
start-node type, admitted-Intent state factory, deterministic routing trigger, and immutable
PatternManifest. Each BaseNode receives mutable state and run-scoped dependencies and returns its
next node or End. Python return types declare intended transitions. LychD compares the native
builder routes to the pinned manifest and rejects an undeclared returned successor or End before
any successor executes. Typed shape and declared routing still cannot prove hidden premises or
the meaning of a mutation.

The delivered engine is serial. Broadcast, map/spread, joins, reducers, arbitrary function steps,
and parallel execution have no admitted checkpoint contract and are rejected by this adapter.

## State and dependencies

Resume state is a JSON-round-tripping Pydantic model containing only declared continuation data.
Live models, grants, toolsets, sessions, connectors, and service handles belong in deps; messages
needed after a park are serialized first. Frames, token fragments, temporary objects, and
uncommitted work may die. This is declared memory, not total recall.

## Pattern binding

PatternManifest is Spellweaver's renderer-neutral score: URL-safe key/revision, checkpoint-schema id,
unique stations, unique permitted edges, and deterministic digest. Every executable station maps
one-to-one to a Python node; mapped implementations equal the node set; delegated stations use
DelegatedAgentNode; edge endpoints are declared. The digest proves declared snapshot, not source
equivalence or every return path.

In the accepted workflow grammar, one station places a Spell contract. The current manifest has no
independent Spell identity or catalogue: its stations are legacy inline placements bound directly
to Python nodes. `PatternManifest` is therefore not the portable Scroll ABI.

Admission pins the full manifest. Before execute or resume, worker requires that snapshot to remain
valid and exactly equal the registered revision; drift fails instead of silently changing score.
Fresh execution must begin at the builder's declared entry station; only a validated durable
cursor may enter at a later station. Fresh calls retain the caller's state and node objects while
checkpoint storage retains detached copies.
Both delivered Bridge revisions validate fresh and restored state against admitted Run identity,
session, prompt, priority, and capability binding before node execution.
Workflow.mermaid() is a projection.

### Boundary metadata (Designed)

A future contribution declares execution plane, eligible local/Portal providers, local-only/egress
behavior, writes, delegation, quarantine, label propagation, and required declassification receipt,
Gate, or consent. station.kind remains mechanics, not a generic danger bit. Loom may badge that
declaration; occurrence evidence must name actual provider, decision, payload digest, receipt, and
result. Current manifests cannot prove it. Context owns labels; Security owns declassification.

## Execution and occurrence identity

perform_run is the single execution site: it rejects stale/duplicate delivery, claims exact
enqueue sequence, verifies pinned Pattern, builds run services, then invokes GraphRunner. Each node
attempt gets a process-local station-attempt correlation and an entered, settled, waiting
(hardware/consent/delegate), or failed event. Its delivered field remains the legacy
`occurrence_id`; canonical Spellweaver **Occurrence** instead names a schedule or external-trigger firing
before Invocation admission. Dispatch adds its grant event only after lease admission;
Orchestrator events retain the station-attempt correlation. Events observe; they neither recover
work nor establish a global order. Ordinary observer exceptions are logged and cannot replace
completion, the original execution failure, or a checkpointed wait. Cancellation still propagates.

## Capability handshake

Capability nodes ask [Dispatcher](22-dispatcher.md), never bind runtimes directly. On
HardwareTransitionRequired GraphRunner finds the signal even through a task group, snapshots state
only when the exception tree resolves unambiguously to that signal; mixed signal/failure groups fail
closed rather than swallowing a sibling. It snapshots state and current node, marks waiting, sets
AWAITING_HARDWARE, asks [Orchestrator](23-orchestrator.md) to
converge, returns RUNNING, resumes persistence, and dispatches again. Default limits are eight
hardware resumes per Run and three consecutive requests for one capability; exceeding either fails.
The counters live in checkpointed Run state, so a durable park or replacement `GraphRunner` cannot
reset the budget. A pre-budget legacy checkpoint decodes with zero counters because past attempts
cannot be reconstructed retroactively. The waiting run holds no lease and does not know whether
convergence was a load, systemd swap, or no effect.

## Live and Durable Stasis

Live Stasis leaves the loop resident; current linear hardware waits use an in-memory
LiveStasisPhylactery. Durable Stasis exits the worker after mandatory checkpoint and re-enters by a
new queue claim. Gate or DelegatedAgentNode automatically selects the durable tier.

| Park | Signal | Run status |
| --- | --- | --- |
| Human verdict | ConsentPending | AWAITING_CONSENT |
| Delegated job | DelegatedAgentPending | AWAITING_DELEGATE |
| Service job (Designed) | ServiceJobPending | AWAITING_SERVICE |

Long Sleep means a durable wait that outlives the worker. Vessel lifecycle and A2A waits remain
designs until they use this same checkpoint/re-admission rule. `AWAITING_SERVICE` is accepted law
but has no source, persistence, or relay yet. Missing checkpoint fails as stasis lost; process death
in RUNNING or AWAITING_HARDWARE recovers only an exact Consent or delegated pre-park boundary
bound by the first resumable checkpoint; otherwise startup contains correlated effects and records
failure. It never guesses a
replay. [Reanimation](../sepulcher/phylactery/reanimation.md#reanimation-a-new-vessel-judges-durable-truth)
keeps the state-by-state return conditions.

For a future service job, the owning station persists `ServiceJobAttempt@1` before first submit,
checkpoints the same owner, then parks. Re-entry reads terminal attempt truth and dispatches afresh;
it never resumes a Connector, grant, provider SDK object, or process handle. Unknown external
effect remains contained rather than being repeated. [Workers
(14)](14-workers.md#service-job-attempts-designed) owns the common attempt and recovery mechanics;
the Composition/domain contract owns result meaning and acceptance.

## Checkpoint Ownership and Terminal Commit

DurableStasisPhylactery stores one Run-owned snapshot document. PostgreSQL replaces complete
validated snapshot history in one JSONB row with INSERT ON CONFLICT UPDATE; memory uses defensive
process-local copies. A snapshot contains typed state, next node, status, and completed/end
snapshots—not dependencies or event stream.

The native builder has no persistence API. LychD owns the snapshot codec and execution statuses;
GraphRunner invokes the public native iterator and task-request API to execute one station at a
time. It records running before the native node call, records success/error afterward, and retains
the next station or final result before reporting settlement. Re-entry injects the decoded node
at the native iterator's initial boundary before any station runs. Native task ids and fork stacks
remain local to that invocation.

The codec preserves the supported v1 wire envelope while validating state and output against the
pinned graph and resolving node ids only from its declared classes. Unknown nodes or node fields,
duplicate snapshot ids, and multiple created cursors fail explicitly. A pending snapshot remains
decodable but is not automatically replayed; neither running nor error status grants a new attempt.
The `node_id` field belongs to the checkpoint envelope; node constructors cannot declare it.
Constructor fields are checked before writing and after reading, so serialization cannot silently
replace a node value with envelope metadata or retain fields the decoder cannot restore.

GraphRunner can create/resume snapshots but cannot decide their deletion. Terminal order is fixed:

1. Commit DONE, FAILED, or CANCELLED to Run ledger.
2. Release run-scoped context.
3. Delete durable checkpoint.
4. Publish the single terminal event from committed status, durably drain its Step evidence, then close the live channel.

Cleanup is best-effort. Failed deletion retains checkpoint for reconciliation; committed terminal
truth remains authority. Repository evidence proves adapter and memory-profile recovery, not a real
PostgreSQL consent-plus-checkpoint restart, schema migration, transactional Step-event outbox, or distributed fence.

## Consent re-entry

A Gate stores serializable message suffix/call ids, snapshots itself, and parks. Worker commits the
consent relation and AWAITING_CONSENT; one guarded verdict edge admits QUEUED and the next worker
resumes the same Graph. Typed checkpoint shape alone does not authorize that re-entry: before
the first node executes, its Gate/delegated station kind and retained owner id must match the Run's
single current wait owner. [Workers (14)](14-workers.md#durable-consent-and-delegated-waits) owns
replacement of that relation across chained or mixed waits; historical records remain evidence.
One approval call per model round, with bounded chained rounds, is current;
ADR 25 owns verdict order and recovery.

## Delegated Agent Macro-Nodes {#3-delegated-agent-macro-nodes}

DelegatedAgentNode is one typed opaque station. Graph owns purpose and result routing, not the
foreign planner, subagents, tool loop, or events. DelegatedAgentRequest names request/run/step,
exact runtime adapter, read/candidate/verify containment, bounded prompt, and immutable input
ArtifactRefs.

AgentJob follows:

```text
QUEUED → ADMITTED → PREPARING → RUNNING → terminal
```

Terminals are SUCCEEDED, FAILED, CANCELLED, TIMED_OUT, LOST. Request id is idempotency key:
different reuse fails. For result adoption and ordinary polling, the first admitted terminal wins
and late results are inert. LOST records indeterminate external truth and never authorizes automatic
repetition. Explicit cancellation still contains the owning runtime and may record `LOST → CANCELLED`
only after containment returns, as required by [Workers](14-workers.md#delegated-agentjob-labor).

delegated_rite@1 proves no-effect reference submit, park, adoption, re-admission, and projection.
It performs no subprocess, provider, network, credential, or workspace effect. Runtime selection is
exact-name only, not Dispatcher grant or Orchestrator capacity; memory store is process-local.
The [artifact-reference receipt](../state-of-the-work.md#artifact-reference-contract) covers a
bounded PostgreSQL metadata round-trip through job creation and result adoption, using tables
created from schema metadata. It does not establish migration execution, process restart,
provider effects, Graph park/resume, or artifact-byte custody.

Coffin, Provider Gate, effectful adapters, cancellation, artifact custody, budgets, and
cross-process recovery retain their [State boundaries](../state-of-the-work.md#delegated-agent-execution). Provider
testimony is labelled, bounded evidence, never hidden reasoning.

## Runtime migration

The installed version is owned by [Agents](20-agents.md#decision) and the lockfile. The v2 migration
uses the public builder and BaseNode interoperability; it does not retain the removed v1 runner or
vendor upstream persistence. Official [builder documentation](https://pydantic.dev/docs/ai/graph/builder/)
and the [migration map](https://pydantic.dev/docs/ai/overview/migration/) explain that native graph
snapshotting is absent. The LychD serial adapter preserves the existing Run/Stasis boundary instead
of introducing an external durability engine or agent-Harness authority.

Captured Pydantic Graph 1.107.5 consent, delegated, and hardware-wait documents exercise the owned
decoder in `tests/integration/test_graph_checkpoint_codec.py`. The captured consent continuation
runs on the native builder with either verdict; pending remains nonreplayable. These receipts do
not establish process restart, database schema migration, or broker recovery. Parallelism and
external durability remain separate designs.

## Future parallel topology

A future adapter must retain typed isolated branch state, fan-out identity/parentage, declared
join/reduction, bounded concurrency/capability admission, checkpoint compatibility, cancellation
settlement for every branch, and evidence separating topology from factual agreement. A reducer
only applies its predicate; consensus, first completion, or a model judge does not establish truth.

## Runtime evidence

| Record | Answers |
| --- | --- |
| Pinned Pattern manifest | What passage was permitted? |
| Station-attempt events (legacy `occurrence_id`) | Which station attempts were observed? |
| Dispatch/transition events | Which grant and hardware change correlated? |
| Run ledger | What lifecycle truth settled? |
| Graph checkpoint | Where may execution lawfully resume? |

Event replay is process-local. A terminal manifest station is declarative: Pydantic Graph returns
End directly, so observers must not fabricate a terminal-node occurrence.

## Following a pause and return {#correspondence}

[Stasis and return](../sepulcher/extensions/weaver/stasis-and-return.md) follows a running or
parked workflow. [Reanimation](../sepulcher/phylactery/reanimation.md) explains how a new Vessel
judges the durable records after process loss.

## Consequences

!!! success "Accepted"
    - Serial typed execution has bounded hardware recovery, durable parks, pinned revisions, and terminal-before-cleanup law.
    - Later parallelism has a narrow compatibility seam.

!!! failure "Cost"
    - Checkpoint schemas require deliberate versioning; durable replacement rewrites whole history.
    - Live waits die with process; valid routing cannot prove factual correctness or effect meaning.

## Verification

State round-trip/tier-selection, GraphRunner, worker, consent, delegation, checkpoint, and event
tests cover the current path. [State of Work](../state-of-the-work.md) separates those memory-profile
facts from PostgreSQL and external-runtime receipts.
