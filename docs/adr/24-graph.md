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

LychD uses the installed serial pydantic_graph BaseNode API. A Workflow binds typed Graph,
start-node type, admitted-Intent state factory, deterministic routing trigger, and immutable
PatternManifest. Each BaseNode receives mutable state and run-scoped dependencies and returns its
next node or End. Python return types declare intended transitions; Pydantic validates construction
and serialization, not every hidden premise or mutation.

The engine is serial. GraphBuilder, broadcast, map/spread, joins, reducers, and parallel execution
are not installed behavior; State owns the Pydantic AI v2 migration boundary.

Migration is staged: `1.25.1` → exact final-v1
[`1.107.1`](https://github.com/pydantic/pydantic-ai/releases/tag/v1.107.1) with deprecations as
errors → versioned checkpoint/cursor and parked-Run migration → a `WorkflowRuntime` port → audited
v2. Version `1.107.0` is forbidden because `1.107.1` closes its AG-UI trailing-message
authorization bypass. GraphBuilder parallelism and external durability remain separate experiments;
neither may ride inside the checkpoint-format migration.

## State and dependencies

Resume state is a JSON-round-tripping Pydantic model containing only declared continuation data.
Live models, grants, toolsets, sessions, connectors, and service handles belong in deps; messages
needed after a park are serialized first. Frames, token fragments, temporary objects, and
uncommitted work may die. This is declared memory, not total recall.

## Pattern binding

PatternManifest is Weaver's renderer-neutral score: URL-safe key/revision, checkpoint-schema id,
unique stations, unique permitted edges, and deterministic digest. Every executable station maps
one-to-one to a Python node; mapped implementations equal the node set; delegated stations use
DelegatedAgentNode; edge endpoints are declared. The digest proves declared snapshot, not source
equivalence or every return path.

Admission pins the full manifest. Before execute or resume, worker requires that snapshot to remain
valid and exactly equal the registered revision; drift fails instead of silently changing score.
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
`occurrence_id`; canonical Weaver **Occurrence** instead names a schedule or external-trigger firing
before Invocation admission. Dispatch adds its grant event only after lease admission;
Orchestrator events retain the station-attempt correlation. Events observe; they neither recover
work nor establish a global order.

## Capability handshake

Capability nodes ask [Dispatcher](22-dispatcher.md), never bind runtimes directly. On
HardwareTransitionRequired GraphRunner finds the signal even through a task group, snapshots state
only when the exception tree resolves unambiguously to that signal; mixed signal/failure groups fail
closed rather than swallowing a sibling. It snapshots state and current node, marks waiting, sets
AWAITING_HARDWARE, asks [Orchestrator](23-orchestrator.md) to
converge, returns RUNNING, resumes persistence, and dispatches again. Default limits are eight
hardware resumes per Run and three consecutive requests for one capability; exceeding either fails.
The waiting run holds no lease and does not know whether convergence was a load, systemd swap, or no effect.

## Live and Durable Stasis

Live Stasis leaves the loop resident; current linear hardware waits use an in-memory
LiveStasisPhylactery. Durable Stasis exits the worker after mandatory checkpoint and re-enters by a
new queue claim. Gate or DelegatedAgentNode automatically selects the durable tier.

| Park | Signal | Run status |
| --- | --- | --- |
| Human verdict | ConsentPending | AWAITING_CONSENT |
| Delegated job | DelegatedAgentPending | AWAITING_DELEGATE |

Long Sleep means a durable wait that outlives the worker. Vessel lifecycle and A2A waits remain
designs until they use this same checkpoint/re-admission rule. Missing checkpoint fails as stasis
lost; process death in RUNNING or AWAITING_HARDWARE reconciles to failure, never opportunistic replay.

## Checkpoint Ownership and Terminal Commit

DurableStasisPhylactery stores one Run-owned snapshot document. PostgreSQL replaces complete
validated snapshot history in one JSONB row with INSERT ON CONFLICT UPDATE; memory uses defensive
process-local copies. A snapshot contains typed state, next node, status, and completed/end
snapshots—not dependencies or event stream.

GraphRunner can create/resume snapshots but cannot decide their deletion. Terminal order is fixed:

1. Commit DONE, FAILED, or CANCELLED to Run ledger.
2. Release run-scoped context.
3. Delete durable checkpoint.
4. Publish the single terminal event from committed status.

Cleanup is best-effort. Failed deletion retains checkpoint for reconciliation; committed terminal
truth remains authority. Repository evidence proves adapter and memory-profile recovery, not a real
PostgreSQL consent-plus-checkpoint restart, schema migration, transactional outbox, or distributed fence.

## Consent re-entry

A Gate stores serializable message suffix/call ids, snapshots itself, and parks. Worker commits the
consent relation and AWAITING_CONSENT; one guarded verdict edge admits QUEUED and the next worker
resumes the same Graph. One approval call per model round, with bounded chained rounds, is current;
ADR 25 owns verdict order and recovery.

## 3. Delegated Agent Macro-Nodes

DelegatedAgentNode is one typed opaque station. Graph owns purpose and result routing, not the
foreign planner, subagents, tool loop, or events. DelegatedAgentRequest names request/run/step,
exact runtime adapter, read/candidate/verify containment, bounded prompt, and immutable input
ArtifactRefs.

AgentJob follows:

```text
QUEUED → ADMITTED → PREPARING → RUNNING → terminal
```

Terminals are SUCCEEDED, FAILED, CANCELLED, TIMED_OUT, LOST. Request id is idempotency key:
different reuse fails, first admitted terminal wins, late terminals are inert. LOST records
indeterminate external truth and never authorizes automatic repetition.

delegated_rite@1 proves no-effect reference submit, park, adoption, re-admission, and projection.
It performs no subprocess, provider, network, credential, or workspace effect. Runtime selection is
exact-name only, not Dispatcher grant or Orchestrator capacity; memory store is process-local.
Postgres adapter/schema/migration lack a real receipt. Coffin, Provider Gate, effectful adapters,
cancellation, artifact custody, budgets, and cross-process recovery remain State-bounded. Provider
testimony is labelled, bounded evidence, never hidden reasoning.

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

## Correspondence

Graph gives Flux a shape: node as station, edge as passage, checkpoint as lawful beginning again.
Identity and judgment stay elsewhere.

## Consequences

!!! success "Accepted"
    - Serial typed execution has bounded hardware recovery, durable parks, pinned revisions, and terminal-before-cleanup law.
    - Later parallelism has a narrow compatibility seam.

!!! failure "Cost"
    - Checkpoint schemas require deliberate versioning; durable replacement rewrites whole history.
    - Live waits die with process; manifest edges and Python paths can drift without stronger proof.

## Verification

State round-trip/tier-selection, GraphRunner, worker, consent, delegation, checkpoint, and event
tests cover the current path. [State of Work](../state-of-the-work.md) separates those memory-profile
facts from PostgreSQL and external-runtime receipts.
