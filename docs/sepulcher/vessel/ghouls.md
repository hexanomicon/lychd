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
`QUEUED`, Pattern, Intent, queue, priority, authority, and its exact initial delivery in one
transaction. Caller retention keeps that delivery `HELD`; success releases it before the engine
opens the live channel and publishes `run:<run_id>:<enqueue_seq>`.

Database admission and broker publication are not one distributed transaction. Retention failure
settles only an unreleased held admission, with bounded compensation retry. Broker failure leaves
the exact queued delivery for the startup/runtime relay; ambiguous publication is resolved by
idempotent key and claim fencing. If cancellation fences canonical truth while broker acceptance is
still in flight, the losing publisher aborts the late physical job.

Only `perform_run` executes the Graph. It claims exact `(run_id, enqueue_seq)` through
`QUEUED → RUNNING`; stale or duplicate delivery returns `skipped`. Missing workflow, changed
Pattern, or missing checkpoint fails rather than starting over.

SAQ `timeout=0` disables its generic wall clock, not Graph, provider, or Orchestrator deadlines.
Each Run job instead has a 120-second heartbeat refreshed by its live invocation. Workflow jobs
have zero automatic SAQ retries; recovery belongs to Run and Graph state.

### Parks, terminal truth, and cancellation

Consent commits checkpoint and identity before `AWAITING_CONSENT`; delegated work parks as
`AWAITING_DELEGATE` with its owner. Resume wins one admission and creates the next pending delivery
in the same transaction; publication may follow later. `AWAITING_HARDWARE` resumes in the same
Ghoul and is not restartable.

Terminal order is commit `DONE`, `FAILED`, or `CANCELLED` plus exact delivery settlement; release
context; delete stasis best-effort; drain one terminal Step event; close. Cleanup cannot conceal
committed truth. Startup repairs missing or mismatched terminal evidence from every canonical
terminal Run before deleting residual stasis. Worker failure retries transient child containment;
if authority remains uncertain, the Run stays nonterminal for restart recovery instead of claiming
false `FAILED` truth. Cancellation elects one writer, commits `CANCELLING`, requires broker and
delegate containment, then commits fenced `CANCELLED`; it becomes a no-op when completion already
won.

`RunEvent` is process-local with bounded replay. Non-token events copy to `step` best-effort; token
deltas are live-only. Evidence is `durable_best_effort`.

### Death and reconciliation

Startup settles previous-process `RUNNING` and `AWAITING_HARDWARE` as `FAILED / ghoul lost`,
deletes checkpoints, and drains terminal events. Every `QUEUED` row must have its exact delivery:
current-boot work is retained, proven pre-boot active work is terminally fenced and re-probed,
absent work is republished, terminal broker records rotate without changing fresh/resume mode, and
unresolved held admission is refused. Missing/mismatched truth, an active row without trustworthy
start time, or an unprobeable queue reports degradation and aborts PostgreSQL startup. A
checkpoint-plus-Consent crash window parks only when the first resumable snapshot names the exact
latest pending consent; decided consent is re-fired; terminal delegated owners re-admit their exact waits. A
lifespan-owned relay set continues delivery, consent, and delegated-owner repair. Every distinct
degraded page is retained while forward scanning continues, rather than keyset-passing blocked
owners forever. There is no same-boot worker-failure custody watchdog, public failed-Run retry,
workflow scheduler, or transactional event outbox.

[Workers](../../adr/14-workers.md) owns claims, interruption, ordering, and recovery; [Graph
(24)](../../adr/24-graph.md) owns checkpoints and terminal commits.
[Topology-A](../../state-of-the-work.md#topology-a-local-runs) is **Available**; [graph stasis and
consent re-admission](../../state-of-the-work.md#graph-stasis-consent) remain **Partial**.

## The unbuilt worker

The designed **Tomb** would accept a narrow payload and workspace grant without model credentials
or Graph authority. Its worker, queue, credentials, and sandbox do not exist; unsafe execution is
disabled.

> _The Ghoul may borrow the hand. It never inherits the Will._
