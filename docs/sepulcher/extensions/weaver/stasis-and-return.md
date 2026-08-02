---
title: Stasis and return
icon: material/pause-circle-outline
---

# :material-pause-circle-outline: Stasis and return

> _A true pause leaves a marked threshold. Return begins there, or it does not begin._

A pause records its owner and return boundary. Broken continuity never reroutes or restarts the
Intent. [ADR 28](../../../adr/28-workflow.md#gates-effects-and-stasis) owns this law.

## Three boundaries

| Boundary | State movement | Custody | Return |
| --- | --- | --- | --- |
| Live hardware wait | `RUNNING → AWAITING_HARDWARE → RUNNING` | Resident Ghoul; Orchestrator owns readiness | Same worker hop; no queue re-admission |
| Durable Gate or delegate wait | `RUNNING → AWAITING_CONSENT` or `AWAITING_DELEGATE` | Checkpoint and exact wait owner | Fresh enqueue and worker claim |
| Terminal Run | `DONE`, `FAILED`, or `CANCELLED` | Canonical ledger | None |

A `Gate` or `DelegatedAgentNode` makes its Pattern durable, but hardware
waiting stays Live: the worker remains resident without a capability lease. Eight total
transitions or three consecutive requests for one capability exhaust the bound and fail the Run.
[Live and Durable
Stasis](../../../adr/24-graph.md#live-and-durable-stasis) owns the distinction.

## What crosses the threshold

The consent or job identity exists before GraphRunner snapshots. The worker then commits the exact
wait owner and status without terminal `DONE`. Consent has released the Agent lease before its
Gate, and return reads the durable verdict before requesting another grant.

A checkpoint is Run-keyed Graph history. A `NodeSnapshot` carries typed Graph state,
next node, and execution status; an `EndSnapshot` carries final state and Graph result. Live
grants, secrets, runtime dependencies, provider handles, events, and `AgentJob` truth stay
elsewhere. It is declared state, neither process image nor effect receipt.

Memory returns defensive copies. The Postgres adapter replaces one JSONB history document per Run,
but no real Postgres consent-plus-checkpoint restart receipt proves that path.

## Return makes a new claim

Either verdict may win `AWAITING_CONSENT → QUEUED`; the resumed hop reads stored truth, never an
enqueue payload. Delegate return accepts only the terminal `AgentJob` owning the current wait.

The winner allocates a fresh monotonic enqueue sequence; its queue key derives from Run and
sequence. The status change and its pending delivery commit together. Publication failure leaves
that exact queued hop for the startup/runtime relay; it does not recreate the wait or reuse a
possibly escaped key. Duplicate verdicts and callbacks are inert.

Bridge admits one approval call per model round. Resumed rounds may chain, bounded to three.
Multiple approvals in one response create no consent row; they settle `DONE` with an honest
bottleneck.

A missing checkpoint fails exactly as `stasis lost`. An invalid document fails the claimed hop
with validator text, not a stable public code. Pinned-manifest mismatch, including
checkpoint-schema identifier drift, fails as `pinned Pattern unavailable`; [Pattern
lifecycle](pattern-lifecycle.md) owns compatibility, migration, and refusal. Process death during
`RUNNING` or `AWAITING_HARDWARE` never guesses a replay: startup recovers only an exact first-node
Consent or delegate park, otherwise contains correlated effects before failing the Run.

An exact pending or already-decided Consent survives the pre-park startup window; decided parked
consent is re-fired. The equivalent exact delegated checkpoint is parked, and startup also refreshes
each durable delegated wait and re-admits it only when its exact owning job is terminal.
[Delegated agents](delegated-agents.md) owns that boundary.

## Truth closes first

For a worker terminal hop: commit the ledger, release context, attempt checkpoint deletion, then
publish one terminal `DONE` from committed status and close. Failed deletion leaves
terminal truth intact as cleanup debt; startup retries terminal checkpoint deletion in bounded
keyset pages. API cancellation orders its writer as parent abort, final child/Consent sweep, commit
`CANCELLED`, publish and close, then delete stasis.
Competing writers converge on one terminal event. A retained checkpoint cannot make a terminal
Run resumable. [Checkpoint
ownership](../../../adr/24-graph.md#checkpoint-ownership-and-terminal-commit) owns the worker path.

Every effectful station needs its own idempotency identity, completion receipt, cancellation rule,
compensation or refusal path, and illegal-repeat boundary. A checkpoint cannot settle an uncertain
external effect.

[Topology-A local runs](../../../state-of-the-work.md#topology-a-local-runs) are **Available**.
[Graph Stasis and consent re-admission](../../../state-of-the-work.md#graph-stasis-consent) and
[delegated execution](../../../state-of-the-work.md#delegated-agent-execution) are **Partial**.
Real checkpoint-plus-Consent/delegate restart proof, distributed fencing, and general periodic
workflow recovery remain absent. [Workers](../../../adr/14-workers.md) owns custody;
[Weaver](index.md) routes the subsystem.
