---
title: 14. Workers
icon: material/excavator
---

# :material-excavator: 14. Workers

!!! abstract "Context and decision"
    A Run ledger records the work before SAQ sees it. Each delivery claims one exact hop; waiting,
    cancellation, cleanup, and recovery move that ledger rather than trusting a queue result.

## Topology and limits

A Run is the canonical workflow record. A worker is the long-lived SAQ engine, and a Ghoul is
one task invocation; several sequential Ghouls may carry one Run. Queueing lets that work outlive
a request without providing process isolation.

The Vessel runs two fixed PostgreSQL SAQ workers, `runs` and `rites`, in its single process and
event loop (`separate_process=False`, no SAQ server lifespan). The application constructs these
workers explicitly and does not register the raw Litestar `workers run` process launcher.
The unused optional batched heartbeat manager is disabled at construction; the live Run
heartbeat below remains invocation-owned. Both use SAQ's separate autocommit
pool and tables; Run, Step, checkpoint, consent, and delegated-job records remain LychD data.
Lifespan connects queues before publishing the run substrate and disconnects them in reverse order
after workers stop. Per-queue concurrency is bounded, but it is not an admission quota, CPU cap,
memory limit, or producer throttle for slow subscribers. A blocking Ghoul can impair HTTP and an OOM or
interpreter crash kills the Vessel.

| Queue | Default source | Registered work |
| --- | --- | --- |
| `runs` | Bridge and CLI workflows | `perform_run` |
| `rites` | background workflow intents | `perform_run` |

These are physical delivery lanes, not Spellweaver service classes. A future `foreground`,
`deadline_windowed`, or `spare_capacity` admission may be delivered through either lane or another
bounded topology; queue name, source, worker concurrency, and scalar priority cannot substitute for
the persisted temporal contract. Work that is not yet eligible must remain with Spellweaver's durable
Occurrence truth rather than occupy a Ghoul while sleeping for its window.

`reconcile_runs` is called directly by lifespan startup with its captured boot cutoff. It is not
registered as broker-callable work, because an invocation without that process boundary could
misclassify live current-boot Runs as orphans.

Tomb still has no delivered queue, executor,
credentials, workspace, or cancellation protocol. [State of Work](../state-of-the-work.md#tomb-untrusted-execution)
owns that delivery boundary.

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

### Idempotent admission and session order

A surface may supply one scoped idempotency key. The ledger derives a server-owned deterministic
Run UUID, atomically creates Run plus delivery once, and returns the prior admission only when its
session, prompt, source, Sigil, scopes, content, and requested priority still match. Topology A
single-flights concurrent same-key retention and publication; PostgreSQL primary-key conflict
resolution provides durable cross-request convergence. Key reuse for different work fails closed.

Before returning, a replay classifies the prior exact delivery. An unresolved `HELD` admission is
re-retained through the caller's idempotent context hook and released; a held admission with no
retention owner fails loudly. No successful handle may leave custody stranded. An exact `PENDING`
delivery is published again before replay returns, while an already published or claimed hop is
only observed.

The returned Run and retained turn remain the canonical admission. Replay does not consult the
current workflow router, so a later registry generation cannot invalidate already admitted truth.

Bridge additionally requests a Topology-A session fence. The process-local admission coordinator
serializes that session's admission decision, permits an exact idempotent replay, and otherwise
refuses a second nonterminal Run through a bounded ledger lookup. Durable terminal Run truth
releases the policy naturally; no process-local active-session marker becomes recovery authority.
This is a one-process conversation causality rule, not a cross-process quota.

### Publication and exact-hop claims

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

The worker also verifies the pinned Pattern and, for a resume, the typed checkpoint and its current
wait owner before the first native builder station runs. LychD's serial adapter owns persistence;
upstream builder scheduling does not authorize checkpoint replay. Decodable pending/running/error
history does not replace a created resumable cursor. `retries=0`;
`timeout=0` disables only SAQ's generic wall clock, while each operation retains its own bound.
Each Run job carries a 120-second SAQ heartbeat and its live invocation refreshes broker `touched`
truth every 30 seconds until the hop returns. This makes abandoned active jobs sweepable without
putting an arbitrary wall-clock limit on a valid graph.

Doctrine priority is 0–100, higher first. PostgreSQL SAQ dequeues lower values first, so the
enqueue edge writes `100 - priority` exactly once. Priority does not preempt an active Ghoul.
Both configured routing rules and explicit `Intent.priority` overrides validate the same range.

### Failed claim acknowledgements

Within Topology-A, one per-Run guard remains held from the authoritative unclaimed
prestate through the claim attempt and any failed-acknowledgement resolution. An
outer `QUEUED` read is only a fast rejection; it supplies no ownership proof.
PostgreSQL establishes the prestate in the same transaction that will claim the
Run, under [Persistence's exact row order](06-persistence.md#atomic-claims-and-checkpoints).
The memory adapter checks and mutates without an intervening await.

Both adapters apply these prestate rules:

| Current prestate | Outcome |
| --- | --- |
| Run absent | Acknowledged skip; no attempt. |
| Well-formed Run with another sequence or a known non-`QUEUED` status | Acknowledged skip; an old delivery is not required. |
| Exact `QUEUED` Run with exact `HELD` delivery | Acknowledged skip; admission has not released it. |
| Exact `QUEUED` Run with exact `PENDING` or `PUBLISHED` delivery | Establish the unclaimed prestate and enter one claim attempt. |
| Malformed Run status, or exact `QUEUED` Run with missing, malformed, or inconsistent delivery authority, including `CLAIMED` or `SETTLED` | Fail before mutation; no observer or settlement. |

The last rule deliberately makes corrupt delivery authority an invariant failure.
It grants no terminal, containment, or checkpoint-deletion authority.

The ledger returns one immutable, invocation-local outcome: acknowledged win,
acknowledged skip, failure before mutation, or failure after entering the attempt.
It records entry into the attempt immediately before the first mutation or mutating
await, after proving the prestate and before any write can occur. The complete
outcome covers the operation, commit, and session exit, retaining original body
and cleanup errors. Callers inspect its explicit fields; there is no Boolean
compatibility facade, mutable receipt, durable token, or ownership registry.
The worker directly awaits this boundary inside its existing shielded claim task.

Recovery requires the attempt fact and an eligible interruption. Each retained
body and cleanup error must independently be an ordinary exception, including an
ordinary exception group, a direct cancellation, or a whole cancellation group
admitted by the terminal-settlement rule. A fatal leaf in either error forbids
observation, containment, settlement, and Graph execution. A later cleanup error
has outward precedence, retaining the original body error and its existing causal
chain; otherwise the original body error propagates. Groups remain unsplit.

Only after the original mutating coroutine has completed with its failed outcome
may the worker invoke the exceptional observer. Under the uninterrupted guard,
its fresh transaction must resolve the exact Run and delivery together:

| Authoritative observation | Permitted result |
| --- | --- |
| Same sequence, `RUNNING` Run and `CLAIMED` delivery | This guarded attempt won. |
| Exact cancellation or terminal authority | Relinquish to its existing owner. |
| Same sequence, `QUEUED` Run and `PENDING` or `PUBLISHED` delivery after the prior transaction is fenced | This attempt did not acquire durable ownership. |
| Successor, park, inconsistent or missing proof, failed observation, or expired observation budget | Unresolved; preserve that state and acquire no authority over it. |

A proved interrupted winner never enters Graph. Release the observation guard
before invoking `_settle_interrupted_claim`, which rechecks the exact generation
and may reacquire the guard for containment. Only the owner of the terminal commit
emits terminal evidence. Loss or unresolved proof permits no containment, terminal
write, checkpoint deletion, or later unguarded adoption.

Caller cancellation continues waiting for the shielded claim task's actual
outcome. A claim-operation failure retains precedence over caller cancellation;
successful settlement or relinquishment propagates the elected original
interruption without replacing its causal chain. A resolution failure propagates
with the elected interruption retained in its causal chain and grants no ownership.
Settlement-helper failure retains the existing outward precedence and context rules.

The observer's deadline does not bound the original claim operation. This contract
never abandons a live mutating coroutine or releases its guard while it could issue
another claim command. It provides no cross-process attribution or automatic retry.

## Events, settlement, and waits

`perform_run` alone drives Graph execution and publishes semantic lifecycle events. Replay and each
live subscriber queue retain at most 256 events. A cursor outside replay or a live reader that falls
behind receives one `resync` boundary at the current cursor; its authoritative snapshot replaces
everything through that boundary before live tailing continues.
An ordered asynchronous tee writes non-token events to Step rows; token deltas are live-only and
settled text belongs in the session record. Terminal paths wait for that run's writer chain before
closing their channel, so recovery does not report completion while its terminal Step is merely
scheduled. A failed Step append is surfaced at that barrier but cannot roll back already committed
Run truth, so this evidence remains `durable_best_effort`, not a transactional event outbox or
durable live stream.

The bus detaches mutable event metadata at every replay, subscriber, snapshot, and persistence
boundary. All waiters on one failed writer generation observe the same latched failure. If terminal
evidence persistence fails, the closed process-local channel is discarded; startup or a later
single-flight repair confirms canonical terminal truth, starts an explicit fresh writer generation,
seeds a fresh sequence, and retries the missing Step exactly once.

### Terminal settlement

Normal return, failure, and cancellation settle the claimed status/sequence under shielding.
Early refusal for an unavailable Pattern or missing checkpoint also contains correlated effects
before committing failure.
Terminal Run state commits before contextual release and best-effort stasis deletion. The channel
accepts one terminal `DONE`, rejects later events, then closes after subscribers drain or grace
expires. Cleanup failure cannot conceal terminal truth.

A cancellation exception group, including nested groups with ordinary failures, follows the same
exact-claim settlement and cancellation-election rules. Successful settlement or relinquishment
propagates the original unsplit group. If settlement itself fails, that failure propagates with
the original interruption as context; unresolved containment retains nonterminal truth. Groups
containing other process-control exceptions remain outside this cancellation rule.

Within Topology-A, claims, durable park commits, and worker failure containment share a per-Run
process-local guard. Failure re-reads the exact sequence and active status before touching child
or consent authority and holds the guard through containment and settlement. A stale Ghoul cannot
cancel a successor's effects, and a committed park survives a lost commit acknowledgement.
Resume publication occurs outside the guard. API cancellation uses its durable `CANCELLING`
fence independently, so waiting for broker abort does not deadlock the worker's acknowledgement.

### Durable consent, delegated and peer waits

Consent and delegation release their Ghoul but retain the Run. Consent persists the checkpoint and
Consent row before one Run transaction verifies that authority, parks `AWAITING_CONSENT`, and
settles the claimed delivery while storing the exact owner in `Run.consent_id`. Startup recognizes
the narrow crash window after checkpoint plus Consent but before that park only when the first
resumable node snapshot binds both the same Run id and the exact latest non-cancelled consent id;
parking then makes that id authoritative. An already decided owner is parked and then re-fired.

The same exact-state rule recovers a checkpointed delegated job before its Run park. Delegation
parks atomically `AWAITING_DELEGATE` with its exact `AgentJob` owner.

A verdict or terminal job CASes status/owner and creates the next `PENDING`
delivery in one transaction. That transaction re-reads the exact persisted Consent owner and
requires decided, non-cancelled truth with a decision principal and timestamp, or re-reads the
same-run `AgentJob` and requires a shape-valid terminal result matching that job and status. The generic
status writer cannot move either wait state back to `QUEUED`; only the owner-specific CAS may do so.
Both consent verdicts resume and Graph reads the durable decision.

The Run's consent, delegated-job and peer-task pointers identify its single current durable wait,
not history. Each park sets its exact owner and clears the other pointers atomically; the related
Consent, AgentJob, peer custody and event records retain history. That single owner survives
re-admission and claim.
Before the first restored node executes, the worker requires its station kind and checkpoint
owner id to match the Run's current owner. Missing, ambiguous, or stale bindings fail without
executing the checkpoint. Switching between wait kinds therefore cannot resurrect a historical
approval or job. In-process hardware re-entry after this check does not reconsume the wait owner.

Concurrent handlers converge. Publication failure leaves the new `QUEUED` hop for the relay; no
wait state is recreated and no possibly published key is reused. Delegation additionally requires
terminal truth for the same job.

The [native public peer station](26-a2a.md#native-public-peer-station) prepares its immutable task
without contact, checkpoints it, then parks `AWAITING_PEER`. Only that committed owner may send.
Its owner-specific CAS rereads canonical same-Run task and admissible terminal/disposition under
current authority, creates one successor delivery and refuses generic wait-to-queue writes.
Exact created checkpoint recovery follows the consent/delegate pre-park rule; prepared rows alone
never authorize replay. A bounded relay exits each iteration and holds no Graph capability lease.

Consent and delegate re-admission remain cancellable: interruption before their atomic transaction leaves the
wait; interruption after commit leaves the exact pending delivery for recovery. Optional broker
error diagnostics do not defer cancellation. Required containment of a late published job retains
its separate cancellation shield.

### Live hardware waits

During hardware stasis, the Run keeps the same Ghoul. That Ghoul checkpoints, marks
`AWAITING_HARDWARE`, awaits a bounded orchestrator transition, returns to `RUNNING`, and resumes
from persistence. It holds no capability lease while waiting but continues to occupy its worker
task, unlike a durable consent or delegated wait.

## Cancellation, mutation, and recovery

### Cancel and contain

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
A Ghoul observing its exact generation in `CANCELLING` releases volatile execution resources so
the broker can acknowledge containment, retaining its durable checkpoint until terminal commitment.
An interruption before that commit waits only for the local election or leader failure, then re-reads durable truth; it never waits for full API settlement, which may
itself need that worker to exit. If election failed, the worker may attempt its exact-generation
`FAILED` transition. Completion may win before election and makes cancellation an idempotent
no-op. This coordination is valid only in the one-process topology.

Sovereign peer work has a narrower local obligation: durable closure of result adoption for every
bound task and actual retirement of all Run-owned local exchanges must acknowledge before terminal
cancellation or orphan failure. That closure does not require remote authentication or a foreign
task id. After it and all ordinary local containment succeed, local `CANCELLED` may commit while
retaining explicit remote outcome uncertainty. Remote cancellation is separate bounded
reconciliation and asserts no process containment or rollback; an unreachable sovereign cannot
retain local continuation authority. This exception never applies to AgentJobs, owned children,
managed service execution or unresolved local cleanup. Retained peer debt survives terminal
checkpoint deletion and is visible through an authorized status projection.

### Close admission before mutation

Runtime mutation closes affected capability lease admission and the global pre-claim gate, then
waits for those exact leases to drain. `pause_queues()` is only that gate: SAQ may still dequeue a
task which then waits before ledger claim. Queue depth and
worker count do not prove quiescence. Pre-effect drain timeout, cancellation, or failure reopens
the gates. A submitted mutation reopens them only on verified no effect, observed success, or exact
restoration under
[Orchestrator's settlement law](23-orchestrator.md#host-mutation-port-and-privilege-boundary);
uncertain physical outcomes retain containment.

### Startup reconciliation

Startup classifies existing work in this order:

1. Synchronize standing policies, retry `CANCELLING` Runs, repair missing terminal evidence
   across every canonical terminal status, and perform paged retries of idempotent checkpoint
   deletion across all terminal Runs.
2. Fence every pre-boot SAQ generation before failing orphan `RUNNING` or `AWAITING_HARDWARE`
   work as lost. Recover an exact checkpoint-plus-Consent or delegated-job pre-park crash window
   by parking. For the remaining orphan failure paths, contain correlated effects before
   terminal failure. Uncertain containment retains nonterminal Run truth and degrades required
   startup.
3. Inspect the exact delivery for every `QUEUED` Run and apply the matching case below. An
   active broker row without a trustworthy start timestamp degrades recovery.

    | Queued-delivery case | Action |
    | --- | --- |
    | `HELD` admission is still unresolved | Refuse. |
    | Current-boot broker work is active or queued | Retain. |
    | A pre-boot active broker generation is proven | Terminally fence it, probe again, then rotate delivery. |
    | No broker job exists | Republish the same key. |
    | A terminal broker record exists | Use a new sequence, retaining the stored fresh/resume mode. |

4. Reconcile Consent using the owner persisted on the Run, never the newest consent row.
   Re-admit decided consents and terminal delegated waits before a second delivery flush.

Delivery pagination orders by the Run’s eligibility-changing `updated_at` plus identity.
Creation time is unsuitable: an older parked Run that becomes `QUEUED` after a cursor has passed
must appear on a later page. Begin the scan from every queued Run so missing delivery rows
remain visible as corruption; a join must not filter them away. Missing or mismatched delivery
truth, an unavailable queue, an unprobeable broker, or an unfenced orphan degrades the pass. If
required reconciliation is degraded, abort PostgreSQL startup before publishing workers or HTTP
services. The memory profile remains best-effort.

### Ongoing recovery and fairness

After startup, lifespan-owned delivery, delegated-wait, and consent relays repeat bounded recovery.
One internal page scheduler retains every distinct degraded, caller-held, or clean-but-still-active
external-wait page and alternates queued revisits with forward cursor progress. Multiple old poison,
live broker, unfinished delegate, pending consent, or not-yet-released pages therefore neither
disappear from repair nor starve newer identities. Exceptions are isolated per owner within a page.
Each consent owner has one ten-second deadline covering lookup and re-admission, including broker
publication. A timed-out owner remains eligible for a later pass while the page advances to others.
The same consent/delegate bounds cover the worker's optional probe after a durable park. Reference
delegate result adoption is cancellable; acknowledged projection retirement finishes under
shielding, and a later terminal read repairs retirement after an unknown commit outcome.

The lifespan supervisor restarts any relay that exits before shutdown with deterministic
exponential backoff capped at five seconds. Delegated and consent probes share their timeout-bounded
reconciliation paths with startup; a verdict or terminal child committed after an earlier clean
probe is therefore re-fired without requiring another process restart.

Recovery stops at declared checkpoints. The relays preserve Graph effects' claim-sequence
fences and idempotency law; they do not provide generic SAQ retry, a periodic workflow scheduler,
or public failed-Run retry. Uncheckpointed process death is recorded as failure rather than
guessed forward.

### Shutdown order and deadline

Shutdown cancels all maintenance relays and stops every in-process worker before shared services or
queue pools are dismantled. A relay timeout or worker-stop failure raises and leaves those shared
dependencies live.

Teardown must prove that worker tasks have ended before closing what they use. A stop method's
return is insufficient if its captured worker task remains live. Lifespan therefore owns both
the stop coroutine and SAQ's captured launcher task, cancels the launchers, and proves every
observed worker task ended under one 30-second deadline. Otherwise teardown would manufacture
use-after-close behavior.

Queue teardown then attempts every configured disconnect and reports the grouped failures
instead of abandoning later pools after the first error. Cancellation is retained but deferred until
the queue currently closing has completed and that reverse sweep has attempted every queue. The
PostgreSQL queue facade is installed before
connect and explicitly closes a managed pool if SAQ opens it but fails schema initialization before
marking itself connected; SAQ's disconnected-flag no-op cannot leak that partial owner.

### Unsettled failure and late publication

A Ghoul retries transient child-authority containment before committing worker failure. Persistent
failure remains explicit nonterminal Run truth because `FAILED` would falsely claim required
locally owned effects are contained. Sovereign peer tasks retain the local closure and remote
uncertainty distinction above. There is not yet a same-boot failure-custody watchdog or a dedicated `FAILING` state;
restart orphan reconciliation is the current final recovery boundary.

A publisher that loses its acknowledgement after cancellation re-probes and retries exact broker
abort three times before surfacing failure. That fence completes under caller cancellation before
the disconnect is propagated. Persistent late-job abort failure remains fenced by the Run/delivery
claim CAS and is retried by explicit cancellation or startup reconciliation; it is not misreported
as physical containment.

The memory persistence profile and `LiveStasisPhylactery` are test/local process state. PostgreSQL
checkpoint shapes exist, but the standard suite does not prove checkpoint-plus-consent restart on a
real PostgreSQL lifecycle.

## Service job attempts

Long-running image, video, Form, Kinesis, Scanner, Scout, speech, engine, or provider work is not a
broker retry and cannot be represented by a live Connector handle in Graph state. The accepted
common mechanical envelope is `ServiceJobAttempt@1`; source, migrations, adapters, and restart
receipts are not delivered yet.

Before the first local or remote submit, the owning domain Worker persists an attempt containing:

- owner job and Run/station-attempt identity, exact request digest, idempotency identity, and retry
  generation;
- one discriminated execution binding: either a capability-backed interface, immutable profile
  revision/digest, operation, driver and dialect revisions; or a direct-tool-backed Spell
  implementation and Resolution Lock, immutable `ToolProfile`, and executor or Tomb profile;
- classified source and working `ArtifactRef`s, destination, purpose, consent/egress decision, and
  relevant policy revisions;
- state, provider/executor job identity when known, progress cursor, result and diagnostic refs, usage,
  cost, warnings, cancellation request, and reconciliation evidence; and
- for managed local resident or scarce substrate, the exact durable Orchestrator-visible
  reservation/fence that prevents readiness from disappearing while the effect can still execute.

The mechanical attempt states are:

```text
PREPARED → SUBMITTING → ACCEPTED → RUNNING → SUCCEEDED | FAILED | CANCELLED
               |             |         |
               +-------------+---------+→ INDETERMINATE
```

`PREPARED` proves no submit has started. A CAS to `SUBMITTING` occurs before the driver is called,
and the exact idempotency identity accompanies every permitted transmission. The returned
provider/executor job identity is persisted before `ACCEPTED`. A timeout, disconnect, crash,
malformed acknowledgement,
or lost cancellation acknowledgement after submit stays `SUBMITTING` or settles
`INDETERMINATE`; it never fabricates failure or authorizes a new effect. Reconciliation first looks
up the same provider/executor identity and idempotency identity. Re-submit is legal only when its
evidence proves no effect occurred, or when the admitted adapter proves atomic server-side same-
key/same-payload replay that returns the original effect/job identity and rejects changed-content
key reuse. The domain retry policy must admit the same generation, sealed bytes and target must be
unchanged, and each physical transmission obtains a fresh EgressDecision. A provider or executor
unable to offer that idempotency guarantee or lookup cannot host autonomously repeatable durable
effects.

Cancellation records intent, asks the exact attempt owner, and continues reconciliation.
`CANCELLED` means execution containment is proved, not merely that a request was sent.
Containment also closes pending launch authority: a paused dispatcher, delayed request or executor
restart must not create work after cancellation acknowledges. The actual executor release owner
must order release against irreversible closure for the exact occurrence/generation, or prove all
old launch-capable actors and pending requests irreversibly drained. A database CAS, lease, PID,
unit name or empty hierarchy alone is insufficient. If release wins, cancellation contains that
in-flight effect and closes its generation; if closure wins, old release/create/start/restart
requests refuse. Unknown ordering or closure remains unresolved, with no `CANCELLED` receipt.
Local reservation release follows terminal containment; an indeterminate local or paid remote attempt
keeps the relevant fence or operator-visible containment instead of guessing. The common envelope
owns delivery, reconciliation, cancellation, and settlement mechanics. Scanner, Prism, Form,
Kinesis, Foundry, Scout, Echo, and each Composition retain their domain request/result contracts,
validation, acceptance, and finish law.

After checkpoint and exact attempt ownership are durable, the parent Run may park as
`AWAITING_SERVICE`. Only an owner-specific CAS from a proved terminal attempt creates the next
`PENDING` delivery; the generic status writer cannot resume it. Startup and the lifespan relay page
every service wait, reconcile the same attempt under a deadline, and contain unresolved effects.
No live Connector, grant, SDK client, stream, tensor, process, or session enters the checkpoint.

## Delegated `AgentJob` labor

Delegated work is neither Tomb execution nor a broker retry. The coordinator has idempotent typed
`AgentJob` submission/adoption/cancellation, parks the graph with exact ownership, and resumes one
bounded hop. The selectable `reference` adapter is deterministic and effect-free; it may rebuild
its process-local result projection from the persisted request before restart-time refresh or
cancellation, retains that projection across a failed store adoption, and retires it only after
authoritative terminal settlement. Its effect-free echo remains `SUCCEEDED` when the generated
text exceeds the result limit: the retained text is bounded with an explicit truncation marker
and can still be reconstructed for cancellation. This demonstration does not permit truncating
an effectful runtime's required result or terminal evidence into success. Effectful runtimes require lookup by
durable provider/executor identity and must never replay submission. Reference-only recovery cannot
stand in for an effectful adapter's durable lookup, containment or artifact custody. [State of
Work](../state-of-the-work.md#delegated-agent-execution) owns current delivery evidence.

Codex and Claude have bounded one-shot protocol adapters behind a refusing-by-default host port.
The command intent pins the CLI version, exact request and job, literal argv, stdin, isolated
environment and roots, and finite capture/wall limits. It is not an execution permit. A future
trusted host must retain that exact launch identity before effects and return its original limits
and matching whole-job containment evidence on lookup. Changed configuration cannot rewrite a
retained launch. Malformed, incomplete, conflicting or oversized protocol output cannot become
success; a timeout requires containment before terminal classification. Neither adapter is
registered by default, and no subprocess launcher or Provider Gate bridge is delivered.

Polling and containment use the exact store-retained request with its job reference. The
coordinator obtains that request from its current authoritative read. For the reviewed CLI
protocols, the prompt is exactly its UTF-8 stdin; lookup and cancellation never recreate a
submission. Both operations require the retained-request argument on the Python adapter port,
and built-ins change atomically under [Extension compatibility](05-extensions.md#7-extension-compatibility-tiers).

### Versioned CLI intent and owner binding

The existing `DelegatedAgentRequest` is the unchanged legacy request: no discriminator or policy
is backfilled, and its request, nested job and launch encodings retain their original meaning.
Reference work and retained Pattern revisions remain unchanged. Fresh legacy CLI starts refuse
before calling a host; historical lookup and containment retain their narrower request/stdin
correlation, without inventing previously unretained model, roots or limits.

A sibling `DelegatedCliRequestV2` uses the exact discriminator
`request_schema="lychd-delegated-cli-request@2"`. In addition to the existing occurrence and prompt
fields it requires immutable `cli_intent` and `owner_binding`. Its runtime is exactly `codex` or
`claude`. The intent pins `compiler_revision="official-one-shot@1"`, the exact reviewed CLI version,
canonical executable, explicit model, one parent `job_root` with three pairwise-disjoint strict
children, and all four existing capture and wall limits. The pinned compiler alone derives literal argv, replacement environment and stdin.
No arbitrary settings, added CLI flags, reasoning alias or model default enters that interpretation.
Current runtime defaults cannot reinterpret retained V2 work.

The first owner-binding namespace is `operator-campaign@1`. Each of its four references has an
immutable `record_id`, `revision` and lowercase `sha256:` content digest; identifiers are bounded
ASCII identifiers and revisions cannot mean `latest`. The binding also names the independent
`verifier_id`. These are opaque owner-qualified identities, never paths to resolve by the runtime:

- `task` binds the principal, campaign/task/attempt, acceptance and non-goals, standing authority,
  tools/effects, all budgets, cancellation, termination and separate promotion owner;
- `projection` binds the exact base plus admitted dirty patch and selected untracked bytes,
  their manifest and allowed paths;
- `custody` binds output format, quarantine, destination, retention and permitted downstream use;
- `verification` binds fixed commands, tool versions, environment, deadlines, pass criteria,
  independent verifier identity and reserved verification capacity.

A trusted injected owner-admission port, absent or denying by default, checks current owner truth
before V2 start. Its closed positive observation binds the exact job occurrence, canonical request
and intent digests, all four references and verifier, an admission identity, aware issue/expiry
instants and a nonnegative bounded generation. The consumer requires issued <= trusted now < expiry
and a positive validity window no longer than one day. Missing, denied, malformed, expired or
mismatching observations refuse before host launch. A caller cannot serialize a positive observation
into the request. The port checks existing admission; this passage grants no budget reservation or
execution permit. Current authority and generation are the producer's responsibility, not proved by
consumer equality checks. Poll and cancellation need no fresh owner admission, including after its
expiry or revocation, and never launch.

Explicit request decoding selects legacy only when the discriminator is absent, V2 only for its
exact tag, and refuses unknown/null tags and extra fields without fallback. The same codec governs
store writes, exact replay, detached reads and nested job JSON. Unknown stored versions remain
unchanged and unavailable; they are not translated or rewritten. Legacy launch digests remain
unchanged. V2 uses separate request/intent digest domains and a tagged launch encoding containing
the complete request and existing launch specification. Canonical bytes are sorted compact UTF-8
JSON with nonfinite numbers forbidden; this internal identity claims no general JCS/signature
canonicalization. Retained work keeps its compiler and codec versions.

For V2 lookup and containment, independently compile the complete expected specification from the
store-retained request and exact job, then compare the host specification and matching receipt.
Consistent substitutions of model, executable, argv, environment, roots, limits or owner bindings
must refuse even when the host recomputes its receipt. The host must additionally retain the exact
versioned launch and owner decision durably before effects, with create-once exact-job ownership;
lookup never repairs an absent record by resubmission.

Consumer conformance with an inert positive owner fixture is a mechanical prerequisite only. It
proves no actual owner-record producer, source-byte closure, current authorization/revocation,
custody service or verifier reservation. Those owners must be delivered and independently checked
before usable admission, including changed dirty/untracked bytes under unchanged names. The four
CLI limits do not supply ADR 09 CPU, memory, process, disk, provider or artifact budgets. Physical
host retention, enforcement and Gates remain separate prerequisites. Neither this contract nor a
migrated-store test registers a CLI or delivers native Creation.

### Host dispatch and irreversible closure

A future delegated-host attempt specializes [Service job attempt](#service-job-attempts) mechanics
under the existing AgentJob. It binds the exact versioned request/specification and digests,
actual owner decision, selected host policy, executor generation, dispatch/closure disposition,
and containment/custody evidence. [Phylactery](06-persistence.md#decision) owns its admitted
persistence. It introduces no competing generic attempt lifecycle, task selector, retry policy,
acceptance judge or promotion owner. AgentJob and `AWAITING_DELEGATE` keep their existing truth;
host disposition cannot independently resume Graph or create `AWAITING_SERVICE`.

Create-once exact-job ownership commits before a guest effect. The conditional
`PREPARED → SUBMITTING` handoff consumes dispatch before calling the executor. Conflict preserves
the original; absent or uncertain commit permits no release. A consumed dispatch can yield zero
executions if its owner dies before contact. This CLI profile does not inherit a service adapter's
conditional retransmission permission: an uncertain dispatch, lost acknowledgement, missing
lookup or lease expiry allows exact lookup/containment only, never replacement submission.
At-most-one admitted dispatch is not exactly-once execution or completion.

The trusted host must re-observe the actual owner producer over the exact retained identities
after preparation/queue/reservation waits. Forwarded runtime observations are historical evidence,
not live permits; `launch(spec)` can retain its shape only when trusted host construction supplies
that producer and the required release boundary. Source projection remains immutable through
release. Complete budget, custody and independent-verification reservations must actually exist;
Admission-consumer equality and its four capture/wall bounds establish none of them. A new positive
owner operation or host handoff needs its own accepted typed contract, rather than silently
expanding the existing observation port into reservation or authority.

Current admission, expiry/revocation and physical release must share the selected executor's ordered
release/closure boundary. A fresh check followed by an arbitrary pause is insufficient. The
executor must reject all stale create/start/restart requests after irreversible generation
closure, or the host must prove equivalent draining and loss of every old launch capability.
Containment evidence binds that generation, existing descendants and absence of pending/future
release. If that proof is unavailable, cancellation remains unresolved; neither an empty lookup
nor a mocked receipt permits `CANCELLED`. No selected executor supplying this boundary is delivered.

Dispatch and closure history cannot disappear through ordinary cleanup while an old occurrence
could be reused. Known database restore, lost control history or uncertain authority epoch closes
fresh launch until independently surviving executor/owner evidence and explicit authority
reconcile the generations and effects. Restored counters or old `PREPARED` rows cannot prove an
unspent occurrence. Missing evidence keeps launch closed; this decision creates no nonrollback
store and claims no machine/power-loss recovery profile. Return custody remains pending until
its actual owner seals the bounded artifacts and references; coordinator adoption failure never
permits relaunch or deletion of required evidence.

#### Mechanical host disposition precursor

The first `delegated-host-disposition@1` profile retains mechanical intent before usable host
admission. It is not the complete admitted host attempt above: no actual owner decision,
reservation, guest release, containment or custody is supplied. One permanent AgentJob row
serializes preparation, dispatch consumption and logical intake closure even before a
disposition record exists. Preparation retains the exact tagged V2 request and job, immutable
proposed host-policy identity and executor generation, and independently compiled launch digest
in bounded canonical bytes. Reconstructing the complete specification from that retained request
must reproduce the digest; a caller-supplied digest alone cannot establish it.
This precursor admits only complete canonical current stored V2 shape: decoding and re-encoding
must preserve its canonical JSON bytes, including scalar types and explicit defaults. Omitted
defaults or numeric aliases refuse without rewriting the stored request or changing the global
V2 codec's compatibility contract. Preparation, consumption and prepared-history reads all apply
that admission; logical close remains available without decoding damaged intent.

Only a newly inserted, acknowledged preparation yields one nonserializable handle owned by the
issuing adapter instance. Reads, exact replay, process replacement and retained PREPARED records
yield snapshots only. Consuming the handle retires it before the first asynchronous operation and
conditionally commits the one PREPARED-to-SUBMITTING disposition. Failure or uncertain commit
cannot reissue that opportunity, even if the retained preparation remains unconsumed. Such loss
may produce zero dispatches. No returned value is an owner permit or a capability to launch.

Logical intake closure is monotonic and may be retained before preparation. Closure that wins
prevents later preparation or dispatch consumption for the same AgentJob; changing policy or
executor generation cannot reopen it. Dispatch that wins remains potentially in flight when
logical close is recorded. This acknowledgement proves only that the store will admit no new
logical handoff; it cannot settle AgentJob CANCELLED, emit containment evidence or release a
reservation. Physical release and irreversible executor closure retain the separate law above.
The profile adds no registration, restore-reactivation, retry or positive owner operation.

The decisive future fixture pauses dispatcher A after admission/dispatch claim, lets B cancel or
close, then releases A. Either A is rejected after closure, or B cannot acknowledge cancellation
until A's in-flight release is contained and fenced. Repeat across lost acknowledgements, restart,
stale generation, expiry during a paused release, changed mounted input and restored records. Pure doubles prove protocol logic,
PostgreSQL proves its transaction claims, and a real selected executor proves physical fencing,
containment and ceilings. None substitutes for the absent owner producer, Gate or host qualification.

### Delegated settlement

`LOST` is terminal for result adoption and ordinary polling, but it is not evidence that an external
process stopped. Parent cancellation must still call the owning runtime's containment operation and
may record `LOST → CANCELLED` only after that operation returns.
An unclassified exception raised by `runtime.start` records `LOST`, never proof that the job failed
or stopped. Start-error diagnostics are bounded to the result contract, with an explicit truncation
marker when necessary; an oversized diagnostic cannot prevent settlement. Exact-request replay
retains the original job; late success is inert, and explicit cancellation still calls its owning
runtime. A failure before that invocation may record `FAILED`. An effectful adapter additionally
needs a proved definitely-rejected outcome and durable provider/executor lookup before its
reconciliation contract can be admitted.

Once start returns, the coordinator finishes one acceptance write despite repeated caller
cancellation. If that write raises an ordinary exception, observation and conditional settlement
share the store's
authoritative mutation lock. A committed `RUNNING` row or an existing terminal remains unchanged;
only a row still `PREPARING` under that lock may settle `LOST`. A prior snapshot of `PREPARING`
does not authorize settlement. This operation neither repeats submission nor retries the
acceptance write. Preserved `RUNNING` or terminal truth returns the original job reference;
newly recorded `LOST` propagates the original write failure. Caller cancellation propagates
after a known disposition. Failed locking, observation, or settlement remains an explicit
unresolved failure with the initiating write failure or interruption retained as context.
These rules neither reopen `LOST` nor replace owning-runtime containment.

Background work on `rites` now uses ordinary `perform_run` execution; the former no-effect
`perform_rite` placeholder has been removed. There is no Rite registry or Rite handler. Admitting
one later would require typed identifiers, extension provenance, payload schema, authorization,
idempotency, queue policy, and settlement.

## Consequences

- Exact hop keys and conditional settlement prevent an old delivery from rewriting a later resume.
- Pending broker work survives a Vessel restart and transient broker publication failure; active
  uncheckpointed execution does not.
- The [current evidence envelope](../state-of-the-work.md#current-evidence-envelope) records the
  tested persistence and recovery wiring with offline collaborators. Their composed behavior,
  real host/model/browser operation, and checkpoint-plus-consent restart still need separate proof.
