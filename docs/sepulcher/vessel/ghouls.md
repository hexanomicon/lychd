---
title: Ghouls
icon: material/robot-dead
---

# :material-robot-dead: Ghouls

> _Work is queued. The dead hand rises. The result returns._

A **Ghoul** is one worker-task invocation carrying admitted labor. A **Run** is the canonical
lifecycle record and may cross several sequential Ghouls after durable parks. Invocation, active
Agent, pinned Pattern, and authority remain attributable to the Run.

## The living worker

The current topology has two fixed SAQ worker loops, for `runs` and `rites`, inside the single
[Vessel](./index.md):

- `QueueConfig.separate_process=False`;
- `SAQConfig.use_server_lifespan=False`;
- application startup owns the worker lifecycle; and
- exactly one ASGI process is required while the live `RunEventBus` remains process-local.

Every workflow Run is a queued SAQ job, not an isolated process. A blocking Ghoul can block HTTP;
death destroys its live task and subscribers even when broker work survives.

### Admission and claim

`RunEngine.submit` selects workflow and queue. The `RunLedger` mints the Run id and commits
`QUEUED`, Pattern, Intent, queue, priority, and authority. After caller retention, it opens the live
channel, advances `enqueue_seq`, and publishes `run:<run_id>:<enqueue_seq>`.

Creation and publication are not one transaction. Failure compensates only an unclaimed `QUEUED`
row to `FAILED`, emits terminal truth, and closes. If an ambiguous job claimed, compensation loses.

Only `perform_run` executes the Graph. It claims exact `(run_id, enqueue_seq)` through
`QUEUED → RUNNING`; stale or duplicate delivery returns `skipped`. Missing workflow, changed
Pattern, or missing checkpoint fails rather than starting over.

SAQ `timeout=0` disables its generic wall clock, not Graph, provider, or Orchestrator deadlines.
Workflow jobs have zero automatic SAQ retries; recovery belongs to Run and Graph state.

### Parks, terminal truth, and cancellation

Consent commits checkpoint and identity before `AWAITING_CONSENT`; delegated work parks as
`AWAITING_DELEGATE` with its owner. Resume wins one admission, advances the sequence, and publishes
a Ghoul. `AWAITING_HARDWARE` resumes in the same Ghoul and is not durable.

Terminal order is commit `DONE`, `FAILED`, or `CANCELLED`; release context; delete stasis
best-effort; publish one terminal event; close. Cleanup cannot conceal committed truth.
Cancellation elects one writer and aborts the current job; completion winning makes it a no-op.

`RunEvent` is process-local with bounded replay. Non-token events copy to `step` best-effort; token
deltas are live-only. Evidence is `durable_best_effort`.

### Death and reconciliation

Startup settles previous-process `RUNNING` and `AWAITING_HARDWARE` as `FAILED / ghoul lost`,
deletes checkpoints, and emits terminal events. Aged `QUEUED` becomes `FAILED / enqueue lost` only
when its exact job is proved absent; an unprobeable queue preserves it and reports degradation.
Pending consent stays parked; decided consent is re-fired. Startup does not recover
`AWAITING_DELEGATE`; there is no public failed-Run retry, scheduler, or outbox.

[Workers](../../adr/14-workers.md) owns claims, interruption, ordering, and recovery; [Graph
(24)](../../adr/24-graph.md) owns checkpoints and terminal commits.
[Topology-A](../../state-of-the-work.md#topology-a-local-runs) is **Available**; [graph stasis and
consent re-admission](../../state-of-the-work.md#graph-stasis-consent) remain **Partial**.

## The unbuilt worker

The designed **Tomb** would accept a narrow payload and workspace grant without model credentials
or Graph authority. Its worker, queue, credentials, and sandbox do not exist; unsafe execution is
disabled.

> _The Ghoul may borrow the hand. It never inherits the Will._
