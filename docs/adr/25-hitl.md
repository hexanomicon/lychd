---
title: 25. HitL
icon: material/account-voice
---

# :material-account-voice: 25. HitL

!!! abstract "Context"
    An Agent may propose an effect, never become its authority. A human decision or bounded standing
    policy may outlive the worker; it must retain the exact call, release scarce execution, and
    return through the same durable path without replaying a Pattern from origin.

In the Lich's tongue the Call can ask and the Blade can refuse. Here that is a durable, auditable
transition from one proposed effect to authority to attempt it—not proof, safety, or effect-time
authorization.

## Decision

The Magus Consent Protocol has three outcomes:

| Outcome | Meaning |
| --- | --- |
| Live verdict required | Exact call parks for authorized Magus approval or denial. |
| Codex preauthorized | Matching standing rule settles the same consent record. |
| Denied | Neither live verdict nor standing rule admits this effect class. |

Every effect declares eligible outcome. Confidence, repetition, previous approval, or broad tools
cannot change it. Core mutation, migration, destructive deletion, secret/authority change, and
host lifecycle remain live-only until narrower enforced law exists. Current ledger, bounded ZTE
Rune, Altar verdict, Graph park/resume, and guards do not prove a complete live-only taxonomy;
State owns delivery.

## Consent invariants

### One verdict, one visible call

A consent record names one Run, tool, deferred tool-call id, censored arguments, verdict, deciding
principal, and preauthorization provenance. Its paired checkpoint additionally binds capability,
durable toolset id and concrete type, tool name, project-owned effect id and revision, and
prepared-definition digest. Resume compares that binding before approved dispatch; missing or
changed identity settles as a policy bottleneck without invoking a handler. Approval-required
tools without an effect identity cannot park, and tool owners must revise the effect revision when
executable semantics change without changing the prepared definition. Bridge accepts one approval
request per model round and rejects multiple or external deferred calls: Pydantic AI demands every
deferred result, so one card cannot counterfeit consent for hidden calls.

Changed security-relevant argument, object, effect class, destination, amount, or authority creates
a new call. A safe projection can redact; executor remains bound to validated call. Consent may
authorize eligible disclosure but cannot declassify, repair missing lineage, approve different
provider/payload, override non-declassifiable categories, or replace Security's Privacy Cut and
EgressDecision.

### Verdict before effect

At Graph boundary:

```text
pending → Durable Stasis
granted → resume exact deferred call with approval
denied  → resume exact deferred call with refusal
```

Both decisions re-admit. AwaitConsent produces DeferredToolResults; denial never executes the
tool, carries no free-form critique, and does not promise a revised proposal. A verdict is not a
grant: before an approved effect, handler rechecks Principal, Sigil, object, effect, policy
generation, revocation, and IAM authority.

### No scarce lease across judgment

AwaitConsent follows release of chat grant. Run becomes AWAITING_CONSENT; worker exits; no model or
VRAM lease remains. This is Durable Stasis, held by checkpoint and run/consent records, not a
sleeping coroutine or old event channel.

### Commit before projection

The permitted park order is:

1. validate one representable approval call;
2. persist censored consent row;
3. persist AwaitConsent checkpoint;
4. bind consent id to Run and commit AWAITING_CONSENT;
5. emit the Altar event.

A page snapshot can see the row sooner, so worker re-reads verdict after park; this and API use the
same atomic admission gate.

### One resume hop

First successful AWAITING_CONSENT → QUEUED compare-and-set receives a new monotonic enqueue_seq
and publishes one SAQ job keyed by run/enqueue sequence. Repeat clicks, concurrent clients,
post-park race closer, and startup reconciliation lose that CAS. Verdict and publication are not
one transaction: failed/cancelled publication restores exact AWAITING_CONSENT but retains advanced
enqueue_seq; a possibly existing broker key is never reused. Reconciliation re-fires decided
parked rows. Missing checkpoint fails as stasis lost, never a restarted Pattern.

## Live judgment at the Altar

The route needs runs:approve, commits idempotent approve/deny before re-admission, and retains its
first result against contradictory clicks. Current card shows tool plus censored arguments. A mature
typed effect-owner projection may show Principal/Sigil; exact object/destination/amount/effect;
bound evidence; reversible and irreversible outcomes; policy provenance/expiry/history; and
approve/deny/revise/inspect alternatives. These are records, not model assurances; no workflow
produced diff, screenshot, test, or simulation artifact merely because a card exists.

Loopback bootstrap is fixed magus:* with no caller authentication. runs:approve is meaningful only
at documented same-host scope, not remote-consent evidence.

## Codex preauthorization

A Rune under runes/codex/preauth matches Sigil/tool patterns, supported argument allowlists or
string prefixes, optional expiry, and optional max uses; unknown constraints fail closed. Postgres
uses guarded UPDATE RETURNING for budget consumption, but match/use and consent insert are separate
commits: crash can burn a use without its row. ZTE requires non-empty constraints, expiry, and
max_uses; standard may still be broader. Expiry is not rechecked immediately before a long-waited
effect.

Preauthorization is Magus policy, never model confidence. Same-slug startup refresh retains usage;
it only upserts present Runes, does not disable removed/tightened enabled rows, and logs sync
failure while continuing. Until complete-set reconciliation with fail-closed startup, removing a
file does not prove standing authority dead.

## Failure and recovery

| Failure | Result |
| --- | --- |
| Worker/Vessel dies pending | Consent and checkpoint persist; lease does not. |
| Verdict before queue publication | Restore wait or startup reconciliation re-fires it. |
| Duplicate/contradictory verdict | First settled verdict is authoritative. |
| Multiple deferred calls | Policy bottleneck; no shared verdict. |
| Missing checkpoint | Honest stasis-lost failure. |
| Old hop races newer | Hop ownership/enqueue_seq bars old settlement. |
| Altar disconnects | Durable state remains; browser is not record. |

Memory-profile simulated restart proves this path; no maintained real PostgreSQL
Consent-plus-Checkpoint restart receipt exists.

## Rejected alternatives

### Hold the worker and model lease

It wastes scarce capacity and loses continuity.

### Poll a flag from the running Agent

It has neither an exact checkpoint nor single-owner re-admission.

### Treat review, simulation, and training as one pipeline

They remain distinct offices: consent does not promote Karma, assign credit, or train weights.

## Consequences

!!! success "Accepted"
    - Human latency occupies durable records, not model capacity.
    - One visible exact call gets an immutable attributable verdict; approval and refusal survive a declared boundary.
    - Missing state, duplicate decisions, and publication loss receive honest routes.

!!! failure "Cost"
    - Approval Patterns need serializable compatible checkpoints.
    - Consent, Run admission, and broker publication require reconciliation.
    - Redaction can limit review; live-only classification and effect-time reauthorization remain unsolved enforcement.

## Verification

Focused suites cover parks/resumes, chained single approvals, missing stasis, idempotency,
verdict-before-resume, reconciliation, publication compensation, memory-backed preauthorization,
Sigil guards, and terminal cleanup. PostgreSQL guarded update exists but has no use-and-audit
atomicity or stale-rule-revocation receipt. State owns graph-stasis and local-Sigil delivery claims.
