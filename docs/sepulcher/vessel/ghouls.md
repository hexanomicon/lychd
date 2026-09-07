---
title: Ghouls
icon: material/robot-dead
---

# :material-robot-dead: Ghouls

> _Work is queued. The dead hand rises. The result returns._

A **Run** carries the canonical identity and lifecycle of admitted work. A **Ghoul** is the
worker-task invocation that advances it. After a durable park, another Ghoul may carry the same
Run forward with its Invocation, pinned Pattern, and retained Agent selection. Return rebuilds step
dependencies, reacquires the grants it needs, and revalidates the recorded authority.

## The living worker

The single [Vessel](index.md) owns two fixed SAQ worker loops, `runs` and `rites`.
`QueueConfig.separate_process=False` keeps them in process;
`SAQConfig.use_server_lifespan=False` leaves startup and shutdown to the application. Exactly one
ASGI process is required while `RunEventBus` and the service graph remain process-local.

Queued work has no process isolation. A blocking Ghoul can block HTTP, and Vessel death destroys
the live task and subscribers even when the broker retains its job.

### Admission and claim

`RunEngine.submit` selects the workflow and queue. In one transaction, `RunLedger` mints the Run
id and commits `QUEUED`, the Pattern, Intent, queue, priority, authority, and exact initial
delivery. That delivery remains `HELD` until caller-owned retention succeeds. Release precedes
opening the live channel and publishing `run:<run_id>:<enqueue_seq>`.

Each failure keeps its own boundary:

| Failure | What remains true |
| --- | --- |
| Caller retention fails | Only an exact unreleased held admission may be settled; compensation retry is bounded. |
| Broker publication fails | The admitted Run and exact pending delivery remain for the startup/runtime relay. |
| Broker acceptance is ambiguous | The idempotent delivery key and claim fence settle ownership. |
| Cancellation wins while publication is in flight | The losing publisher aborts the late physical job. |

PostgreSQL admission and broker publication are separate commits. Only `perform_run` executes the
Graph: it claims exact `(run_id, enqueue_seq)` through `QUEUED → RUNNING`. A stale or duplicate
delivery returns `skipped`. A missing workflow, changed Pattern, or missing resume checkpoint
fails the claim; execution never starts the Intent over to fill the gap.

SAQ `timeout=0` disables its generic wall clock. Graph, provider, and Orchestrator deadlines still
apply, and the live invocation refreshes a 120-second Run-job heartbeat. Workflow jobs have zero
automatic SAQ retries.

### Parks, terminal truth, and cancellation

A hardware wait keeps this Ghoul resident: `AWAITING_HARDWARE` returns in the same hop and cannot
survive restart. A consent or delegated wait commits checkpoint and exact owner before entering
`AWAITING_CONSENT` or `AWAITING_DELEGATE`. One later resume admission creates the next pending
delivery in the same transaction; publication may follow. [Stasis and return](../extensions/weaver/stasis-and-return.md)
explains those thresholds.

The worker's terminal sequence is:

```text
commit DONE / FAILED / CANCELLED and exact delivery settlement
→ release context
→ delete stasis best-effort
→ durably drain one terminal Step event
→ close the live channel
```

Cleanup cannot revise committed status. If child containment fails transiently, the worker retries
it; continuing uncertainty leaves the Run nonterminal for recovery. It cannot claim `FAILED`
while correlated authority may still act.

Cancellation elects one writer, commits `CANCELLING`, and fences claims and delivery rotation.
Broker and delegate containment must acknowledge before the elected generation commits
`CANCELLED`. Uncertain containment preserves `CANCELLING`; completion that already won makes a
new cancellation a no-op.

`RunEvent` has bounded process-local replay. Non-token events copy to `step` best-effort; token
deltas are live-only. The evidence class is `durable_best_effort`, not a transactional event outbox.

### Death and reconciliation

A new process judges committed Run, delivery, checkpoint, Consent, and delegated-owner truth.
[Reanimation](../phylactery/reanimation.md#reanimation-a-new-vessel-judges-durable-truth) owns the
state-by-state return: unsupported active work becomes `FAILED / ghoul lost`, exact durable
waits may return, and missing or ambiguous required truth aborts PostgreSQL startup.

Before deleting residual stasis, startup repairs missing or mismatched terminal evidence from
canonical terminal Runs. Lifespan-owned relays continue delivery, consent, and delegated-owner
repair. They retain every degraded page while scanning forward, so a blocked owner is not lost
behind a keyset cursor. There is no same-boot worker-failure custody watchdog, public failed-Run
retry, or workflow scheduler.

[Workers](../../adr/14-workers.md) owns claims and recovery;
[Graph](../../adr/24-graph.md) owns checkpoints and terminal commits. [Topology-A](../../state-of-the-work.md#topology-a-local-runs)
is Available; [durable stasis and consent re-admission](../../state-of-the-work.md#graph-stasis-consent)
remain Partial.

## The unbuilt worker

The designed **Tomb** would receive a narrow payload and workspace grant without model
credentials or Graph authority. Its worker, queue, credentials, and sandbox do not exist; unsafe
execution remains disabled.

> _The Ghoul may borrow the hand. It never inherits the Will._
