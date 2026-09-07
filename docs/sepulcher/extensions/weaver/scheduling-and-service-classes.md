---
title: Scheduling and service classes
icon: material/calendar-clock
---

# :material-calendar-clock: Scheduling and service classes

A Bridge turn needs attention now. A nightly rite may wait until five. A backfill may borrow only
capacity it can safely release. These are three admission promises, each with a different way to
wait, miss, yield, or finish.

> _A bell may announce work. It does not grant authority, seize the iron, or perform the score._

Scheduling is Designed: no durable Occurrence service, periodic workflow scheduler, eligibility
engine, service-class field, or safe preemption is implemented. Current `runs` and `rites` queues
and scalar priorities remain delivery machinery. [Workflow](../../../adr/28-workflow.md#compositions-products-suites-and-schedules)
owns this temporal design; [Workers](../../../adr/14-workers.md) owns that present machinery.

## Three examples

### Foreground conversation

A Bridge turn is eligible now and normally receives foreground preference. It may still wait for
worker or capability readiness. The name promises attention, not instantaneous execution.

### A flexible nightly rite

A schedule nominally fires at `02:00 Europe/Bratislava`, permits start until `05:00`, forbids
overlap, and skips rather than replays an occurrence older than one day. Spellweaver may admit it at any
feasible instant in the window. At `05:00` it records the pinned miss outcome instead of silently
running at noon.

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
| `deadline_windowed` | Eligible at `not_before`; claim by `latest_start_at` or settle under the miss policy. Optional `finish_by` supplies no safe cancellation. |
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

An **Occurrence** is one schedule or external-trigger firing before Invocation admission. A
calendar identity derives from the immutable schedule identity and revision plus its nominal
instant and, when civil time repeats, the selected fold. Jitter or delayed eligibility never changes
that identity.

At minimum, durable Occurrence truth binds:

| Field | Meaning |
| --- | --- |
| `occurrence_id` | Stable deduplication identity for the firing. |
| Schedule identity and revision | The exact calendar, trigger, and policy generation that emitted it. |
| Pattern key and revision | The only score eligible for admission. |
| Input digest and owner | Exact requested work and the principal accountable for it. |
| `service_class` and priority | Temporal doctrine plus ordering inside that doctrine; neither grants authority. |
| `not_before` | Earliest lawful admission instant. |
| `latest_start_at` | Last instant at which a claim may begin without invoking the miss policy. |
| `finish_by` | Optional completion objective; cancellation still requires a safe boundary. |
| Overlap, misfire, and catch-up policy | Exact treatment of a prior live Invocation and missed firings. |
| Budgets and policy generation | Concurrency, time, capability, token, spend, network, storage, and other ceilings to revalidate. |

A duplicate identity with the same immutable payload returns the existing Occurrence and its
admission outcome. Reusing it for changed work fails closed. A crash after persistence but before
admission relays the same Occurrence; it does not mint another firing.

The delivered Graph runtime also has a field named `occurrence_id` for each node attempt. That is a
legacy station-attempt correlation, not the durable Spellweaver Occurrence described here. A future
implementation must use distinct `trigger_occurrence_id` and `station_attempt_id` identities rather
than joining them by spelling.

## Calendar and overlap law

A calendar Schedule declares an IANA time zone, never implicit host-local time. Its immutable
revision also decides:

- which fold fires when daylight-saving fall-back repeats a civil time, or whether both fire;
- whether a nonexistent spring-forward time skips, advances to the next valid instant, or fails;
- how a tzdata change affects already materialized Occurrences;
- the bounded reboot or clock-jump misfire horizon;
- deterministic or bounded jitter and allowed delay; and
- maximum catch-up age, count, concurrency, and aggregate budget.

The allowed delay commonly derives `latest_start_at` from the nominal firing. Passing that instant
before claim settles the Occurrence as missed, expired, or explicitly admitted-late according to its
pinned policy. Silence is not a fourth outcome.

Overlap means the prior Invocation remains nonterminal, including while parked in Durable Stasis;
broker task presence is not sufficient truth. A Schedule selects one closed policy:

| Policy | Result |
| --- | --- |
| `forbid` | Preserve the new Occurrence and record that overlap suppressed its admission. |
| `serialize` | Preserve each Occurrence and consider it after its predecessor, still respecting its own window. |
| `bounded_parallel` | Admit only under declared concurrency and resource ceilings. |
| `coalesce` | Use a Pattern-owned typed merge; preserve every member and its `coalesced_into` relation. |

Coalescing refuses incompatible Pattern revisions, owners, authority generations, policies,
budgets, labels, or inputs. Restart catch-up is bounded by the same rules so a long outage cannot
become an unbounded effect or spending storm.

## Selection is not three FIFO lines

Foreground receives the default latency preference. That preference cannot be absolute: continuous
foreground demand would otherwise make a deadline promise dishonest. Spellweaver first removes invalid,
revoked, duplicate, or expired candidates, then considers deadline feasibility and protected
capacity, foreground latency, remaining deadline-windowed work, and finally spare-capacity work.
Within a class, pinned priority and aging may order eligible candidates; neither may widen Sigil,
budget, egress, effect, or lifecycle authority.

`estimated_duration` and resource estimates may support feasibility only when their provenance and
confidence are explicit. Unknown capacity cannot be rounded into success. Overload before
`latest_start_at` must refuse or miss explicitly rather than start work whose declared bound is
already impossible.

### Spare capacity is a yield contract

Current Workers do not preempt an active Ghoul, and Orchestrator does not preempt a submitted
physical transaction. A `max_slice` value is therefore evidence only when the Pattern can, inside
that bound:

1. reach a lawful checkpoint or terminal boundary;
2. release every capability lease and worker claim it must yield;
3. contain or settle every begun effect; and
4. resume through ordinary fenced admission.

Unknown or non-checkpointable work is non-preemptible. It may use exclusive or scarce iron only in
an explicit operator-approved quiet window. By default `spare_capacity` may consume only an already
WARM, admission-open capability that requires no disruptive hardware transition. It cannot raise
its priority or trigger a hard swap merely to keep the machine occupied.

Deadline-windowed work may request readiness convergence only under its declared transition budget
and policy. Spellweaver declares the capability requirement; Dispatcher still chooses a candidate and
Orchestrator still owns the physical decision. Scheduling never binds a concrete Animator or
rewrites a deadline because the substrate is inconvenient.

## Authority, failure, and recovery

A Schedule is durable intent, not stored authority. Occurrence creation, Invocation admission,
worker claim, Stasis return, and every consequential effect re-evaluate the current owner, Sigil,
Pattern revision, input, budget, policy generation, and required consent. Revocation invalidates
affected pending work. Priority, lateness, or catch-up never revives a credential or bypasses Ward.

The identity boundaries remain separate:

| Event | Identity and recovery |
| --- | --- |
| Broker publication loss | Republish the same Run and exact enqueue sequence. |
| Checkpoint return | Same Invocation, new fenced delivery hop. |
| Next schedule firing | New Occurrence and, when admitted, new Invocation. |
| Terminal retry | New explicitly related recovery Invocation only when Pattern effect law permits it. |
| Unknown or `LOST` effect | Contain for operator recovery; never repeat automatically. |

A deadline passing after claim does not retroactively make a non-cancellable effect safe to kill.
The Pattern follows its declared completion, checkpoint, compensation, or containment law and
records the miss honestly.

## Evidence before delivery

Promotion requires an executable receipt for the declared calendar, deduplication, admission,
overlap, yielding, authority, and recovery behavior. The [Workflow Covenant](../../../adr/28-workflow.md#compositions-products-suites-and-schedules)
owns those obligations; each temporal choice above must be exercised through its failure and
restart boundaries before it becomes an operating promise.

Until that evidence exists, current `runs`/`rites`, priority constants, and proposed Whim or idle controls must
not be presented as this scheduler. The former no-effect `perform_rite` placeholder has been
removed.
