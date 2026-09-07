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
| Durable Gate or delegate wait | `RUNNING → AWAITING_CONSENT` or `AWAITING_DELEGATE` | Checkpoint and exact wait owner | Fresh enqueue and worker claim, including in the same Vessel |
| Terminal Run | `DONE`, `FAILED`, or `CANCELLED` | Canonical ledger | None |

A `Gate` or `DelegatedAgentNode` makes its Pattern durable, but hardware
waiting stays Live: the worker remains resident without a capability lease. A Run may make up to
eight hardware convergence calls in total and three consecutively for one capability. A further `HardwareTransitionRequired` fails before another Orchestrator call. The
initial ordinary node execution is not a counted hardware convergence request.
[Live and Durable
Stasis](../../../adr/24-graph.md#live-and-durable-stasis) owns the distinction.

A durable park ends the current worker execution; it does not require the Vessel to die. If the
process does die, [Reanimation](../../phylactery/reanimation.md) reconciles committed Run, queue,
checkpoint, and wait-owner truth in the replacement process. Restoring an earlier whole-body
snapshot is a separate [Restoration](../../../adr/07-snapshots.md) rite and remains Designed.

## What crosses the threshold

The consent or job identity exists before GraphRunner snapshots. The worker then commits the exact
wait owner and status without terminal `DONE`. Consent has released the Agent lease before its
Gate, and return reads the durable verdict before requesting another grant.

A checkpoint is Run-keyed Graph history. A `NodeSnapshot` carries typed Graph state,
next node, and execution status; an `EndSnapshot` carries final state and Graph result. Live
grants, secrets, runtime dependencies, provider handles, events, and `AgentJob` truth stay
elsewhere. It is declared state, neither process image nor effect receipt.

Every workflow state that can request hardware carries a typed `hardware_resume_budget` in that
checkpoint. Its total and per-capability counters therefore survive a durable park and a replacement
GraphRunner; reconstructing a runner cannot reset them. Checkpoints written before this field decode
with zero counters and cannot prove attempts that happened before the upgrade.

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

Committed terminal status closes the return path even if checkpoint cleanup fails. The worker
settles its exact delivery before releasing Context and attempting cleanup; retained stasis cannot
revive that Run. [Ghouls](../../vessel/ghouls.md#parks-terminal-truth-and-cancellation) carries the
terminal-event and cleanup sequence, governed by
[Graph's commit law](../../../adr/24-graph.md#checkpoint-ownership-and-terminal-commit).

Cancellation fences Run claims and delivery rotation while the parent broker job, delegated jobs,
and Consent authority are contained. Only acknowledged containment permits `CANCELLED`; failure
leaves honest, retryable `CANCELLING` truth. Completion that already won makes cancellation a no-op.

Every effectful station needs its own idempotency identity, completion receipt, cancellation rule,
compensation or refusal path, and illegal-repeat boundary. A checkpoint cannot settle an uncertain
external effect.

[Topology-A local runs](../../../state-of-the-work.md#topology-a-local-runs) are **Available**.
[Graph Stasis and consent re-admission](../../../state-of-the-work.md#graph-stasis-consent) and
[delegated execution](../../../state-of-the-work.md#delegated-agent-execution) are **Partial**.
Real checkpoint-plus-Consent/delegate restart proof, distributed fencing, and general periodic
workflow recovery remain absent. [Workers](../../../adr/14-workers.md) owns custody;
[Spellweaver](index.md) routes the subsystem.
