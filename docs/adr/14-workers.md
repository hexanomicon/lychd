---
title: 14. Workers
icon: material/excavator
---

# :material-excavator: 14. Workers

!!! abstract "Context and decision"
    A Run ledger records the work before SAQ sees it. Each delivery claims one exact hop; waiting,
    cancellation, cleanup, and recovery move that ledger rather than trusting a queue result.

## Topology and limits

The Vessel runs two fixed PostgreSQL SAQ workers, `runs` and `rites`, in its single process and
event loop (`separate_process=False`, no SAQ server lifespan). Both use SAQ's separate autocommit
pool and tables; Run, Step, checkpoint, consent, and delegated-job records remain LychD data.
Lifespan connects queues before publishing the run substrate and disconnects them in reverse order
after workers stop. Per-queue concurrency is bounded, but it is not an admission quota, CPU cap,
memory limit, or slow-subscriber backpressure. A blocking Ghoul can impair HTTP and an OOM or
interpreter crash kills the Vessel.

| Queue | Default source | Registered work |
| --- | --- | --- |
| `runs` | Bridge and CLI workflows | `perform_run`, `reconcile_runs` |
| `rites` | background workflow intents | those tasks plus no-effect `perform_rite` |

A worker is a long-lived SAQ engine; a Ghoul is one task invocation; a Run is the canonical
workflow record and may require sequential Ghouls. Queueing separates request life from work; it
does not provide process isolation. Tomb has no delivered queue, executor, credentials, workspace,
or cancellation protocol. [State of Work](../state-of-the-work.md#tomb-untrusted-execution) owns
that boundary.

## Admission and exact claim

`RunEngine.submit()` is the sole admission path:

1. `WorkflowRegistry` selects the Pattern and `QueueRouter` chooses queue and doctrine priority.
2. `RunLedger.create()` records a canonical `QUEUED` Run with Pattern manifest, source, queue,
   priority, caller Sigil, and reconstructable intent.
3. Any optional caller-retention hook completes.
4. The engine opens the local event channel, increments `enqueue_seq`, and publishes
   `perform_run` under `run:<run_id>:<enqueue_seq>`.

Run creation and SAQ publication are separate transactions; there is no transactional outbox. On
retention, enqueue, or caller-cancellation failure, a shielded compensator may change only the
unclaimed matching `QUEUED` hop to `FAILED`, emit terminal truth, and close its channel. If an
ambiguous publication has already claimed it, the CAS loses and that Ghoul owns settlement.

SAQ receives the Run id, resume flag, and exact sequence; it rebuilds all state and authority from
the ledger. `perform_run` waits at the global claim gate, then atomically claims only matching
`QUEUED` status and sequence as `RUNNING`. A stale or duplicate delivery returns `skipped`.
It also verifies the pinned Pattern and, for a resume, the checkpoint. `retries=0`; `timeout=0`
disables only SAQ's generic wall clock, while each operation retains its own bound.

Doctrine priority is 0–100, higher first. PostgreSQL SAQ dequeues lower values first, so the
enqueue edge writes `100 - priority` exactly once. Priority does not preempt an active Ghoul.
Routing validates its range; `Intent.priority` presently overrides it without equivalent
validation, so callers cannot assume every supplied priority is checked.

## Events, settlement, and waits

`perform_run` alone drives Graph execution and publishes semantic lifecycle events. Replay is
bounded; a cursor outside the window receives resynchronization. Subscriber queues are unbounded.
An ordered, best-effort tee writes non-token events to Step rows; token deltas are live-only and
settled text belongs in the session record. A failed Step append is logged and does not alter Run
truth, so this evidence is `durable_best_effort`, not a durable live stream.

Normal return, failure, and cancellation settle the claimed status/sequence under shielding.
Terminal Run state commits before contextual release and best-effort stasis deletion. The channel
accepts one terminal `DONE`, rejects later events, then closes after subscribers drain or grace
expires. Cleanup failure cannot conceal terminal truth.

Consent and delegation release their Ghoul but retain the Run. Consent first persists checkpoint
and consent identity, then parks `AWAITING_CONSENT`; delegation parks atomically
`AWAITING_DELEGATE` with its exact `AgentJob` owner. A verdict or terminal job CASes status/owner,
allocates a new sequence, and publishes one resume. Both consent verdicts resume and graph reads
the durable decision. Concurrent handlers converge. A publication failure restores the exact wait
state while retaining the advanced sequence, because a possibly published key is never reused;
delegation additionally requires terminal truth for the same job.

Hardware stasis is different: the same Ghoul checkpoints, marks `AWAITING_HARDWARE`, awaits a
bounded orchestrator transition, returns to `RUNNING`, and resumes from persistence. It holds no
capability lease while waiting but still occupies its worker task.

## Cancellation, mutation, and recovery

API cancellation elects one process-local writer. It aborts the exact SAQ job when present,
commits `CANCELLED`, emits/closes the channel, and only then deletes stasis. A Ghoul receiving that
`CancelledError` waits for the election rather than racing `FAILED`; completion may win first and
makes cancellation an idempotent no-op. This is valid only in the one-process topology.

Runtime mutation closes affected capability lease admission and the global pre-claim gate, then
waits for those exact leases to drain. `pause_queues()` is only that gate: SAQ may still dequeue a
task which then waits before ledger claim. `broadcast_soft_stop()` is a v1 no-op. Queue depth and
worker count do not prove quiescence. Gates reopen after no effect, success, exact restoration,
timeout, or ordinary failure; uncertain physical outcomes retain containment.

Startup runs `reconcile_runs` once and logs a failed sweep rather than aborting boot. It fails
pre-boot `RUNNING` and `AWAITING_HARDWARE`; for aged `QUEUED` rows it fails only a job proved absent
by exact key and preserves it when the broker cannot be probed. It deletes checkpoints only for
rows it settles and emits a sequence-correct terminal event. `reconcile_consents` re-admits
decided consents, leaving pending ones alone. There is no startup delegated-wait recovery,
periodic scheduler, automatic SAQ retry, or public failed-Run retry. Recovery exists only at graph
checkpoints; uncheckpointed process death is failed, never guessed forward.

The memory persistence profile and `LiveStasisPhylactery` are test/local process state. PostgreSQL
checkpoint shapes exist, but the standard suite does not prove checkpoint-plus-consent restart on a
real PostgreSQL lifecycle.

## Delegated `AgentJob` labor

Delegated work is neither Tomb execution nor a broker retry. The coordinator has idempotent typed
`AgentJob` submission/adoption/cancellation, parks the graph with exact ownership, and resumes one
bounded hop. The selectable `reference` adapter is deterministic and effect-free. Database shapes,
a migration, and a PostgreSQL adapter exist, but no real PostgreSQL/migration receipt, provider
launch, Coffin supervisor, effectful child, cross-process pickup, or durable artifact custody is
proved. [State of Work](../state-of-the-work.md#delegated-agent-execution) owns the Partial claim.

There is no Rite registry: `perform_rite` is a logged no-effect placeholder, and background work
on `rites` is ordinary `perform_run` execution. Any future registry needs typed identifiers,
extension provenance, payload schema, authorization, idempotency, queue policy, and settlement.

## Consequences

- Exact hop keys and conditional settlement prevent an old delivery from rewriting a later resume.
- Pending broker work can survive a Vessel restart; active in-memory work cannot.
- PostgreSQL ledger/checkpoint and full application-lifecycle evidence remain conditional or
  skipped. [State of Work](../state-of-the-work.md#current-evidence-envelope) owns delivery
  boundaries.
