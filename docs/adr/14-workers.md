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
| `runs` | Bridge and CLI workflows | `perform_run` |
| `rites` | background workflow intents | `perform_run` plus no-effect `perform_rite` |

`reconcile_runs` is called directly by lifespan startup with its captured boot cutoff. It is not
registered as broker-callable work, because an invocation without that process boundary could
misclassify live current-boot Runs as orphans.

A worker is a long-lived SAQ engine; a Ghoul is one task invocation; a Run is the canonical
workflow record and may require sequential Ghouls. Queueing separates request life from work; it
does not provide process isolation. Tomb has no delivered queue, executor, credentials, workspace,
or cancellation protocol. [State of Work](../state-of-the-work.md#tomb-untrusted-execution) owns
that boundary.

## Admission and exact claim

`RunEngine.submit()` is the sole admission path:

1. `WorkflowRegistry` selects the Pattern and `QueueRouter` chooses queue and doctrine priority.
2. One transaction records the canonical `QUEUED` Run and exact `RunDelivery` at sequence zero.
   The delivery is `HELD` when caller-owned admission context must still be retained; otherwise it
   is `PENDING`.
3. Any optional caller-retention hook completes, then atomically releases `HELD` to `PENDING`.
   Failure, including an error learned while the caller itself is cancelled, settles only that
   exact unpublished held generation. A release error is resolved from durable delivery state:
   an already advanced delivery remains admitted, while only a proven `HELD` delivery may fail.
4. The engine opens the local event channel and publishes `perform_run` under
   `run:<run_id>:<enqueue_seq>`; broker acknowledgement moves the delivery to `PUBLISHED`.

A surface may supply one scoped idempotency key. The ledger derives a server-owned deterministic
Run UUID, atomically creates Run plus delivery once, and returns the prior admission only when its
session, prompt, source, Sigil, scopes, content, and requested priority still match. Topology A
single-flights concurrent
same-key retention and publication; PostgreSQL primary-key conflict resolution provides durable
cross-request convergence. A replay classifies the prior exact delivery before returning: an
unresolved `HELD` admission is re-retained through the caller's idempotent context hook and released,
while a held admission with no retention owner fails loudly. It therefore cannot hand out a
successful handle while custody remains stranded. A replay returns the same canonical Run and
retained turn without consulting the current workflow router; a later registry generation cannot
invalidate already admitted truth. An exact `PENDING` delivery is published again before replay
returns, while an already published or claimed hop is only observed. Key reuse for different work
fails closed.

Run plus delivery intent are transactional; PostgreSQL plus SAQ publication are not one
distributed transaction. A broker error or caller cancellation after durable admission leaves the
Run `QUEUED` and its exact delivery recoverable. The process-owned relay probes the idempotent job
key and republishes the same hop when absent. It never guesses a new resume mode from Run status.
Migration 0004 refuses any legacy nonterminal Run because old rows cannot reveal whether their
current hop was fresh or resumed; it does not synthesize history. The migration holds an
`ACCESS EXCLUSIVE` lock on `run` through that refusal check and its transactional DDL so an old
writer cannot create ambiguous work between inspection and outbox installation or removal.

SAQ receives the Run id and exact sequence; it rebuilds all state and authority from the ledger.
The legacy broker `resume` argument remains accepted but is ignored: the claimed `RunDelivery`
owns fresh-versus-resume truth. `perform_run` waits at the global claim gate, then atomically claims
only matching `QUEUED` status and sequence as `RUNNING`. A stale or duplicate delivery returns `skipped`.
The claim moves that exact delivery to `CLAIMED` in the same transaction. Terminal settlement is
fenced by the claimed sequence and settles its delivery; an old Ghoul cannot rewrite a later hop.
`started_at` records the Run's first successful claim and remains stable across resume hops, so boot
ownership is not rewritten by later deliveries.
The worker also verifies the pinned Pattern and, for a resume, the checkpoint. `retries=0`;
`timeout=0` disables only SAQ's generic wall clock, while each operation retains its own bound.
Each Run job carries a 120-second SAQ heartbeat and its live invocation refreshes broker `touched`
truth every 30 seconds until the hop returns. This makes abandoned active jobs sweepable without
putting an arbitrary wall-clock limit on a valid graph.

Doctrine priority is 0–100, higher first. PostgreSQL SAQ dequeues lower values first, so the
enqueue edge writes `100 - priority` exactly once. Priority does not preempt an active Ghoul.
Both configured routing rules and explicit `Intent.priority` overrides validate the same range.

## Events, settlement, and waits

`perform_run` alone drives Graph execution and publishes semantic lifecycle events. Replay is
bounded; a cursor outside the window receives resynchronization. Subscriber queues are unbounded.
An ordered asynchronous tee writes non-token events to Step rows; token deltas are live-only and
settled text belongs in the session record. Terminal paths wait for that run's writer chain before
closing their channel, so recovery does not report completion while its terminal Step is merely
scheduled. A failed Step append is surfaced at that barrier but cannot roll back already committed
Run truth, so this evidence remains `durable_best_effort`, not a transactional event outbox or
durable live stream.
If terminal evidence persistence fails, the closed process-local channel is discarded so startup
or a later idempotent repair can seed a fresh sequence and retry the missing Step.

Normal return, failure, and cancellation settle the claimed status/sequence under shielding.
Terminal Run state commits before contextual release and best-effort stasis deletion. The channel
accepts one terminal `DONE`, rejects later events, then closes after subscribers drain or grace
expires. Cleanup failure cannot conceal terminal truth.

Consent and delegation release their Ghoul but retain the Run. Consent persists the checkpoint and
Consent row before one Run transaction verifies that authority, parks `AWAITING_CONSENT`, and
settles the claimed delivery while storing the exact owner in `Run.consent_id`. Startup recognizes
the narrow crash window after checkpoint plus Consent but before that park only when the first
resumable node snapshot binds both the same Run id and the exact latest non-cancelled consent id;
parking then makes that id authoritative. An already decided owner is parked and then re-fired.
The same exact-state rule recovers a checkpointed delegated job before its Run park. Delegation
parks atomically `AWAITING_DELEGATE` with its exact `AgentJob` owner. A verdict or terminal job CASes status/owner and creates the next `PENDING`
delivery in one transaction. That transaction re-reads the exact persisted Consent owner and
requires decided, non-cancelled truth with a decision principal and timestamp, or re-reads the
same-run `AgentJob` and requires a shape-valid terminal result matching that job and status. The generic
status writer cannot move either wait state back to `QUEUED`; only the owner-specific CAS may do so.
Both consent verdicts resume and Graph reads the durable decision.
Concurrent handlers converge. Publication failure leaves the new `QUEUED` hop for the relay; no
wait state is recreated and no possibly published key is reused. Delegation additionally requires
terminal truth for the same job.

Hardware stasis is different: the same Ghoul checkpoints, marks `AWAITING_HARDWARE`, awaits a
bounded orchestrator transition, returns to `RUNNING`, and resumes from persistence. It holds no
capability lease while waiting but still occupies its worker task.

## Cancellation, mutation, and recovery

API cancellation elects one process-local writer, locks the Run, and commits nonterminal
`CANCELLING` to freeze its exact delivery generation. The broker parent job is abort-fenced first;
only after that acknowledgement does the engine make its final bounded sweep of every correlated
delegated job and pending Consent, so the parent cannot create an effect behind the sweep. All must
acknowledge containment before the fenced `finish_cancel` transaction can expose `CANCELLED` and
settle that delivery. Failed, timed-out, or cancelled containment leaves honest, retryable
`CANCELLING`; startup retries it
with authority to fence a pre-boot SAQ job. Only after terminal truth does the engine persist
terminal evidence, close the channel, and best-effort delete stasis. Re-reading an already
`CANCELLED` Run repeats the child/consent sweep before repairing evidence and cleanup debt.
A Ghoul observing `CANCELLING` releases its execution resources and waits for the election rather
than racing `FAILED`; completion may win before election and makes cancellation an idempotent
no-op. This election is valid only in the one-process topology.

Runtime mutation closes affected capability lease admission and the global pre-claim gate, then
waits for those exact leases to drain. `pause_queues()` is only that gate: SAQ may still dequeue a
task which then waits before ledger claim. `broadcast_soft_stop()` is a v1 no-op. Queue depth and
worker count do not prove quiescence. Gates reopen after no effect, success, exact restoration,
timeout, or ordinary failure; uncertain physical outcomes retain containment.

Startup first synchronizes standing policy, retries `CANCELLING`, repairs missing terminal evidence
for every canonical terminal status, and pages across all terminal Runs to retry idempotent checkpoint deletion. It then
fences each pre-boot SAQ generation before failing orphaned
`RUNNING` or `AWAITING_HARDWARE` work as lost. An exact checkpoint-plus-Consent or delegated-job
pre-park window is parked instead; otherwise correlated effects are contained before terminal
failure, and uncertainty leaves the Run nonterminal while required startup degrades. It inspects
every `QUEUED` Run's exact delivery: unresolved `HELD` admission is
refused; current-boot active or queued broker work is retained; a proven pre-boot active generation
is terminally fenced and re-probed before delivery rotation; an absent job is republished under the
same key; and a terminal broker record rotates to a new sequence while preserving its stored
fresh/resume mode. An active row without a trustworthy start timestamp degrades recovery.
Missing or mismatched delivery truth, an unavailable queue, an unprobeable broker, or an unfenced
orphan makes the pass degraded. Settled consent reconciliation reads each Run's persisted owner,
never the newest row for that Run. Decided consents and terminal delegated waits are re-admitted before
a second delivery flush. PostgreSQL startup aborts before publishing workers or HTTP services when
required reconciliation is degraded; memory-profile startup remains best-effort.
Delivery pages are ordered by the Run's eligibility-changing `updated_at` plus identity, not its
creation time. A previously parked old Run that becomes `QUEUED` after a cursor has passed is
therefore visible in a later page. The scan starts from every queued Run, so a missing delivery row
is reported as corruption rather than filtered out by a join.

After startup, lifespan-owned delivery, delegated-wait, and consent relays repeat bounded recovery.
One internal page scheduler retains every distinct degraded, caller-held, or clean-but-still-active
external-wait page and alternates queued revisits with forward cursor progress. Multiple old poison,
live broker, unfinished delegate, pending consent, or not-yet-released pages therefore neither
disappear from repair nor starve newer identities. Exceptions are isolated per owner within a page.
The lifespan supervisor restarts any relay that exits before shutdown. Delegated and consent probes
share their timeout-bounded reconciliation paths with startup; a verdict or terminal child committed
after an earlier clean probe is therefore re-fired without requiring another process restart.
These relays are not generic SAQ retry: Graph effects remain
fenced by claim sequence and their own idempotency law. There is still no periodic workflow
scheduler or public failed-Run retry. Recovery exists only at declared checkpoints; uncheckpointed
process death is failed, never guessed forward.

Shutdown cancels all maintenance relays and stops every in-process worker before shared services or
queue pools are dismantled. A relay timeout or worker-stop failure raises and leaves those shared
dependencies live. Returning from a worker's stop method is insufficient when a captured worker
task remains live; teardown must not manufacture use-after-close behavior in a task whose stop was
never proved. Lifespan therefore owns both each worker's stop coroutine and SAQ's captured launcher
task, cancels the launchers, and proves every observed worker task ended under one 30-second
deadline. Queue teardown then attempts every configured disconnect and reports the grouped failures
instead of abandoning later pools after the first error. Cancellation is retained but deferred until
the queue currently closing has completed and that reverse sweep has attempted every queue. The
PostgreSQL queue facade is installed before
connect and explicitly closes a managed pool if SAQ opens it but fails schema initialization before
marking itself connected; SAQ's disconnected-flag no-op cannot leak that partial owner.

A Ghoul retries transient child-authority containment before committing worker failure. Persistent
failure remains explicit nonterminal Run truth because `FAILED` would falsely claim all effects are
contained. There is not yet a same-boot failure-custody watchdog or a dedicated `FAILING` state;
restart orphan reconciliation is the current final recovery boundary.

A publisher that loses its acknowledgement after cancellation re-probes and retries exact broker
abort three times before surfacing failure. That fence completes under caller cancellation before
the disconnect is propagated. Persistent late-job abort failure remains fenced by the Run/delivery
claim CAS and is retried by explicit cancellation or startup reconciliation; it is not misreported
as physical containment.

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
`LOST` is terminal for result adoption and ordinary polling, but it is not evidence that an external
process stopped. Parent cancellation must still call the owning runtime's containment operation and
may record `LOST → CANCELLED` only after that operation returns.

There is no Rite registry: `perform_rite` is a logged no-effect placeholder, and background work
on `rites` is ordinary `perform_run` execution. Any future registry needs typed identifiers,
extension provenance, payload schema, authorization, idempotency, queue policy, and settlement.

## Consequences

- Exact hop keys and conditional settlement prevent an old delivery from rewriting a later resume.
- Pending broker work survives a Vessel restart and transient broker publication failure; active
  uncheckpointed execution does not.
- A disposable two-boot application lifecycle proves application-factory, PostgreSQL, SAQ, HTTP,
  terminal Bridge state, and Orb recovery wiring after live dispatch, orchestration, and context
  collaborators are replaced with offline doubles. Their composed behavior and real
  host/model/browser and checkpoint-plus-consent restart receipts remain absent.
  [State of Work](../state-of-the-work.md#current-evidence-envelope) owns delivery boundaries.
