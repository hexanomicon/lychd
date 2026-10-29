---
title: Scheduling and service classes
icon: material/calendar-clock
---

# :material-calendar-clock: Scheduling and service classes

A Bridge turn needs attention now. A nightly rite may wait until five. A backfill may borrow
capacity only while it can safely release it. Scheduling must preserve each of these promises
through waiting, missed windows, yielding, and completion. The distinctions below explain what
admission can promise and which evidence is needed to keep that promise.

> _The night bell sounds above the forge. Below, a hammer is still falling._

No durable Occurrence service, periodic workflow scheduler, eligibility
engine, service-class field, or safe preemption is implemented. Current `runs` and `rites` queues
and scalar priorities remain delivery machinery. [Workflow](../../../adr/28-workflow.md#compositions-products-suites-and-schedules)
owns this temporal design; [Workers](../../../adr/14-workers.md) owns that present machinery.

## Three examples

### Foreground conversation

A Bridge turn is eligible now and normally receives foreground preference. It may still wait for
worker or capability readiness. The name promises attention, not instantaneous execution.

### A flexible nightly rite

A schedule nominally fires at `02:00 Europe/Bratislava`, permits initial Invocation admission
strictly before `05:00`, forbids overlap, and skips rather than replays an occurrence older than
one day. Spellweaver may admit it at any feasible instant in that window. If it is still unadmitted
at `05:00`, it records the miss without creating an Invocation. This latest-start bound does not
promise that a later worker claim or first effect begins before five; declare `finish_by` and the
required finish proof when completion time matters.

### Embedding backfill

Backfill processes one bounded shard against an already-WARM embedding capability, checkpoints,
releases its grant, and offers another shard only while protected capacity remains free. Without
that checkpoint and release proof it is ordinary non-preemptible work, not spare-capacity labor.

## One admission office, three tempos

The three classes describe when work may enter ordinary Invocation admission. They do not prescribe
three broker queues:

| Service class | Admission boundary |
| --- | --- |
| `foreground` | Eligible now and latency-sensitive; preference never guarantees an immediate start. |
| `deadline_windowed` | Admit at or after `not_before` and strictly before `latest_start_at` and any `finish_by`. If still unadmitted at or beyond either applicable upper bound, record a miss; before eligibility, wait only while all applicable upper bounds remain open. Optional `finish_by` governs accepted finish and does not prove safe cancellation. |
| `spare_capacity` | No completion-time promise; scarce resources require bounded yielding or an explicit quiet window. |

`immediate` is not the canonical name because it would promise capacity and preemption that do not
exist. `cron` is a trigger grammar, not a class: a scheduled firing may be deadline-windowed, strict
foreground work, or intentionally suppressed. `opportunistic` alone is also too weak; beginning
while the host looks idle does not prove that the work can release a worker, Animator lease, GPU, or
effect safely.

Origin is orthogonal to tempo. A local operator, schedule, owned Legionnaire, or sovereign A2A peer
may request any class its policy allows; `remote` is not a fourth bucket. Admission preserves that
provenance and may lower or refuse the requested class, but a sender cannot promote its own labor by
labelling it foreground.

```text
Schedule or external trigger
  → durable unique Occurrence
  → Spellweaver eligibility and service-class decision
  → ordinary revision-pinned Invocation / Run admission
  → QueueRouter chooses a physical delivery lane
  → Worker / Ghoul
  → Graph
  → Dispatcher
  → Orchestrator only when readiness must converge
```

Future-due work remains in Occurrence truth. It must not consume a Ghoul by sleeping inside a
worker until its window opens.

## The Occurrence before the Run

Before admitting an Invocation, Spellweaver identifies the schedule or external-trigger firing
that requested it. That firing is an **Occurrence**. Find it by authority-qualified stable Schedule
and recoverable source firing before consulting the active revision. A calendar source identifies
its nominal firing and, where applicable, selected fold member; an external source supplies a
durable source-qualified event identity. Jitter, input equality, delivery attempts, and delayed
eligibility never create another firing. This defines the identity boundary, not a public
identifier encoding.

Each firing is assigned to one exact Schedule revision once. A repeated source event after a
revision switch retrieves that original assignment, even if its Run has already settled. For a
previously unassigned external event, the revision active at the first committed assignment owns
it; assignment and activation share serialized authority. Calendar assignments follow the pinned
cutover described below. Neither restart nor a relay using an old revision can assign the same
firing again.

At minimum, durable Occurrence truth binds the following. The three window-bound fields apply only
to `deadline_windowed`; foreground and spare-capacity work require no invented cutoff or sentinel.

| Field | Meaning |
| --- | --- |
| `occurrence_id` | Stable deduplication identity for the firing. |
| Schedule identity and revision | The stable Schedule and the one exact calendar, trigger, and policy generation assigned to this source firing. |
| Pattern key and revision | The only score eligible for admission. |
| Input digest and owner | Exact requested work and the principal accountable for it. |
| `service_class` and priority | Temporal doctrine plus ordering inside that doctrine; neither grants authority. |
| `not_before` | Inclusive earliest initial Invocation admission for deadline-windowed work. |
| `latest_start_at` | Exclusive latest initial Invocation admission for deadline-windowed work; later worker claims do not reset it. |
| `finish_by` | Optional exclusive bound on authoritative acceptance of the requested semantic finish; cancellation still requires a safe boundary. |
| Overlap, misfire, and catch-up policy | Exact treatment of a prior live Invocation and missed firings. |
| Budgets and policy generation | Concurrency, time, capability, token, spend, network, storage, and other ceilings to revalidate. |

Recovery returns to that retained assignment. A duplicate source firing with the same immutable
source content returns the existing Occurrence and its admission outcome under the originally
assigned revision. Changed source content fails closed; activating a new policy revision alone
does not change source content. After persistence but before admission, a crash relays the same
Occurrence. After admission commit, recovery retrieves its exact Invocation and initial Run
delivery. Neither recovery path mints another firing or proves exactly-once external effects.

The delivered Graph runtime also has a field named `occurrence_id` for each node attempt. That is a
legacy station-attempt correlation, not the durable Spellweaver Occurrence described here. A future
implementation must use distinct `trigger_occurrence_id` and `station_attempt_id` identities rather
than joining them by spelling.

## Calendar and overlap law

A calendar Schedule declares an IANA time zone, never implicit host-local time. Its immutable
revision also decides:

- which fold fires when daylight-saving fall-back repeats a civil time, or whether both fire;
- whether a nonexistent spring-forward time skips, advances to the next valid instant, or fails;
- the retained zone-rule interpretation for unresolved firings; a rule change requires a new revision;
- the bounded reboot or clock-jump misfire horizon;
- deterministic or bounded jitter and allowed delay; and
- maximum catch-up age, count, concurrency, and aggregate budget.

The default selects the earlier fold instant and skips a nonexistent civil firing without
shifting it. Recovery considers at most the newest still-eligible missed calendar firing for
admission and explicitly skips older unadmitted backlog. Other fold, gap, or bounded catch-up
policies must be pinned. Materialized calendar interpretation, absolute bounds, and selected jitter
survive restart unchanged; current host rules cannot replace missing retained rules.

Before activating another calendar revision, pin a disjoint, recoverable partition assigning the
unresolved old firings, cutover firings, and new firings to their exact revisions. Existing
assignments remain unchanged. A time-zone, cadence, or fold-policy change must identify which
nominal candidates under the two retained interpretations are the same source firing, which are
distinct, and which are explicitly skipped under their assigned revision. Do not sort civil times
from unrelated zones as if they formed one timeline. Refuse activation if the partition is missing,
ambiguous, or would reassign a firing. Both relays must recover the same cutover assignment,
including when they first discover it after the revision switch.

For example, a nightly source has one firing for the `2026-01-02` cycle. Revision 1 expresses that
firing as `02:00 Europe/Bratislava` (`01:00Z`); revision 2 would express it as `02:00 UTC`. An
activation at `01:30Z` explicitly pins both candidates to that same source firing under revision 1
and starts revision 2 with the `2026-01-03` cycle. Rediscovering the January 2 candidate at `02:00Z`
retrieves revision 1's Occurrence; it cannot create another under revision 2. The shared cycle
identity and this partition are declared by this example Schedule, not inferred from equal civil
dates or imposed as a universal identifier format.

For deadline-windowed work, allowed delay commonly derives `latest_start_at` from the nominal
firing. At or beyond that bound, an unadmitted firing records a miss without an Invocation. This
design retires the earlier Designed admitted-late option; no pinned miss policy may retain it.
The bound applies to initial admission, not a later worker claim.

Overlap means any earlier Invocation of the stable Schedule remains nonterminal, across all its
revisions, including Durable Stasis, cancellation, and required unresolved containment. A released
worker or broker task absence cannot prove settlement. A Schedule selects one closed policy;
`forbid` is the default:

| Policy | Result |
| --- | --- |
| `forbid` | Preserve the new Occurrence and record that overlap skipped its admission. |
| `serialize` | Preserve each Occurrence and consider it after its predecessor, still respecting its own window. |
| `bounded_parallel` | Admit only under declared concurrency and resource ceilings. |
| `coalesce` | Use a Pattern-owned typed merge; preserve every member and its `coalesced_into` relation. |

Coalescing refuses incompatible Pattern revisions, owners, authority generations, policies,
budgets, labels, or inputs. Restart catch-up is bounded by the same rules so a long outage cannot
become an unbounded effect or spending storm.

## Reading the window and finish

For deadline-windowed work, initial admission requires
`not_before <= decision_time < latest_start_at` and, when present, `decision_time < finish_by`.
Equality at either upper bound is late. Before eligibility, retain the Occurrence without sleeping
inside a worker. An earlier `finish_by` also closes an unadmitted window; no expired bound is
extended to make the work fit.

`decision_time` is a fresh trusted absolute UTC sample taken after acquiring the serialized
conditional decision authority. It counts only if that exact transaction commits. Opening a
transaction earlier, caller timestamps, and a delayed acknowledgement do not determine timeliness.
If acknowledgement is lost, observe the exact durable decision; a rollback accepts no decision.
A sample at `09:04:59` can therefore admit against `09:05` even if commit visibility is later.
This is a promise about the accepted decision, not physical completion by that time. Process-local
monotonic waits cannot become persisted recovery authority. Restart and clock correction recheck
undecided transitions without reopening any committed admission, skip, expiry, or terminal result.

Initial admission satisfies `latest_start_at` once. Consent or delegated return keeps the same
Invocation, pinned Pattern, and exact persisted wait owner, and rechecks current authority through
ordinary Workers, Graph, and HitL rules. Admission at `09:01`, followed by consent approval at
`09:06`, may therefore begin the first effect after a `09:05` latest-start bound. An optional
`finish_by=09:10` still bars new forward-effect admission at or after ten past; approval never
renews that bound. With no `finish_by`, latest-start makes no completion-time promise.

Timely finish requires the exact domain- and Scroll-owned semantic proof to be accepted by the
authoritative terminal Run decision strictly before `finish_by`. The transaction retains that
proof and its temporal disposition together; the required proof must already be valid when that
decision samples time. An intermediate artifact, `DONE`, lifecycle event,
or browser projection alone cannot prove finish. In a
[Companion presentation](../../../compositions/companion/utterance.md), committed text does not
complete required speech unless the admitted policy explicitly accepts text-only fallback. A
separately settled destination result does not finish that presentation or a Suite round trip.
Display is observational only when presentation is not the requested result.

At or after `finish_by`, absent a timely accepted finish, record the unmet deadline and close
forward-effect admission. Every new forward-effect admission checks the bound; an on-time expiry
callback is not assumed. A committed expiry prevents later timely-finish acceptance. Expiry does
not itself make the Run terminal or prove that a child stopped. Required unresolved containment
keeps the Run nonterminal. Already-started effects retain their identities, actual results, and
original safety budgets under their owning cancellation and reconciliation contracts. Late results
may resolve those obligations but cannot become temporal success, reopen terminal jobs, or
justify replacement submissions.

## Selection is not three FIFO lines

Foreground has the default latency preference, but deadline feasibility and protected capacity
must also shape selection. An absolute foreground preference could make deadline promises
dishonest under continuous demand. Spellweaver first removes invalid, revoked, duplicate, or
expired candidates. It then considers deadline feasibility and protected capacity, foreground
latency, remaining deadline-windowed work, and finally spare-capacity work. Within a class,
pinned priority and aging may order eligible candidates; neither may widen Sigil, budget, egress,
effect, or lifecycle authority.

`estimated_duration` and resource estimates may support feasibility only when their provenance and
confidence are explicit. Unknown capacity cannot be rounded into success. For deadline-windowed
work, overload before `latest_start_at` must refuse or miss explicitly rather than admit work whose
declared bound is already impossible.

### Spare capacity is a yield contract

Current Workers do not preempt an active Ghoul, and Orchestrator does not preempt a submitted
physical transaction. A `max_slice` value is therefore evidence only when the Pattern can, inside
that bound:

1. reach a lawful checkpoint or terminal boundary;
2. release every capability lease and worker claim it must yield;
3. contain or settle every begun effect; and
4. resume through ordinary fenced admission.

Unknown or non-checkpointable work is non-preemptible. As `spare_capacity`, it may use exclusive or scarce iron only in
an explicit operator-approved quiet window. By default `spare_capacity` may consume only an already
WARM, admission-open capability that requires no disruptive hardware transition. It cannot raise
its priority or trigger a hard swap merely to keep the machine occupied.

Deadline-windowed work may request readiness convergence only under its declared transition budget
and policy. Spellweaver declares the capability requirement; Dispatcher still chooses a candidate and
Orchestrator still owns the physical decision. Scheduling never binds a concrete Animator or
rewrites a deadline because the substrate is inconvenient.

## Authority, failure, and recovery

A Schedule retains intent across time. Current authority must still be checked when that intent
is acted upon: Occurrence creation, Invocation admission, worker claim, Stasis return, and every
consequential effect re-evaluate the current owner, Sigil, Pattern revision, input, budget, policy
generation, and required consent. Revocation invalidates affected pending work. Priority,
lateness, or catch-up never revives a credential or bypasses Ward.

The identity boundaries remain separate:

| Event | Identity and recovery |
| --- | --- |
| Broker publication loss | Republish the same Run and exact enqueue sequence. |
| Checkpoint return | Same Invocation, new fenced delivery hop. |
| Next schedule firing | New Occurrence and, when admitted, new Invocation. |
| Terminal retry | New explicitly related recovery Invocation only when Pattern effect law permits it. |
| Unknown or `LOST` effect | Contain for operator recovery; never repeat automatically. |

A finish deadline passing after initial admission does not retroactively make a non-cancellable
effect safe to kill. The Pattern follows its declared completion, checkpoint, compensation, or
containment law and records the unmet deadline honestly.

These Schedule rules do not change Orchestrator's activation cutoff. Timely actuator/adapter
invocation or honest readiness confirmation retires that local cutoff; settlement retains its
original safety budgets. An expired coalesced follower ends only its own wait. A local activation
cohort establishes neither a durable Occurrence nor workflow settlement.

## Evidence before delivery

Before this design becomes an operating promise, promotion needs an executable receipt covering
the declared calendar, deduplication, admission, overlap, yielding, authority, and recovery
behavior. The [Workflow Covenant](../../../adr/28-workflow.md#compositions-products-suites-and-schedules)
owns those obligations. Each temporal choice above must be exercised at its failure and restart
boundaries; a successful ordinary firing cannot establish them all.

Until that evidence exists, current `runs`/`rites`, priority constants, and proposed Whim or idle controls must
not be presented as this scheduler. The former no-effect `perform_rite` placeholder has been
removed.
