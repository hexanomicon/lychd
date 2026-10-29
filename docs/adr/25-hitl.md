---
title: 25. HitL
icon: material/account-supervisor-outline
---

# :material-account-supervisor-outline: 25. HitL

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
[State of Work](../state-of-the-work.md#graph-stasis-consent) owns the consent and stasis delivery boundary.

A candidate that touches a Spellweaver [Protected
Region](28-workflow.md#authorship-provenance-and-protected-regions) is always live-only. Its call
binds the exact base, candidate digest, affected region ids, old and replacement digests, an
authorized exact-diff artifact, and target-owner effect revision. Codex preauthorization, a
previous approval, or a broader repository grant cannot settle it. The verdict authorizes only
promotion of that candidate; it does not attest that a human authored the replacement.

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

`pending`, `granted`, and `denied` describe judgment; `cancelled` is a terminal audit settlement
used when Run cancellation withdraws the pending call without manufacturing a human verdict.

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

Judgment begins after the chat grant is released. AwaitConsent moves the Run to
AWAITING_CONSENT and lets its worker exit, leaving no model or VRAM lease. Checkpoint and
Run/Consent records hold this Durable Stasis; neither a sleeping coroutine nor an old event
channel owns the wait.

### Commit before projection

The permitted park order is:

1. validate one representable approval call;
2. persist censored consent row;
3. persist AwaitConsent checkpoint;
4. bind consent id to Run and commit AWAITING_CONSENT;
5. emit the Altar event.

A page snapshot can see the row sooner, so worker re-reads verdict after park; this and API use the
same atomic admission gate.

If the process dies between steps 3 and 4, startup accepts the park only when the first resumable
node snapshot names both this Run and the exact latest non-cancelled consent id. A verdict already
committed in that window is parked and then re-fired; an older approval round cannot lend its
checkpoint to a newer Consent row.

### One resume hop

First successful AWAITING_CONSENT → QUEUED compare-and-set for the exact current `consent_id`
receives a new monotonic enqueue_seq and creates one `PENDING` RunDelivery in the same transaction.
The gate re-reads that same-run Consent and requires a terminal verdict plus its decision principal
and timestamp. Newest-row ordering cannot substitute another Consent for the persisted owner.
Repeat clicks, historical cards, concurrent clients, post-park race closer, and startup
reconciliation lose that CAS. The external SAQ publication is not in that transaction: failure
leaves the admitted `QUEUED` hop and exact key for startup or the lifespan relay to publish. The
wait state is not recreated and a possibly existing broker key is never reused. Reconciliation
re-fires decided parked rows only for their current owner. Missing checkpoint fails as stasis lost,
never a restarted Pattern.

## Live judgment at the Altar

The route needs runs:approve, commits idempotent approve/deny before re-admission, and retains its
first result against contradictory clicks. Current card shows tool plus censored arguments. A mature
typed effect-owner projection may show Principal/Sigil; exact object/destination/amount/effect;
bound evidence; reversible and irreversible outcomes; policy provenance/expiry/history; and
approve/deny/revise/inspect alternatives. These are records, not model assurances; no workflow
produced diff, screenshot, test, or simulation artifact merely because a card exists.

Loopback bootstrap requires the [dedicated local credential](09-security.md) before assigning
the fixed `magus:*` Sigil. `runs:approve` is meaningful only at the documented same-host scope;
it does not establish remote identity or the [Ward](38-iam.md)'s effect-time authorization.

### Required review for native actions (Designed)

A native application may require review of an action it has already prepared. Its Consent retains
an immutable binding to the owning Composition, native action, exact preparation, review profile
and revision, producer and revision, admitted audience, and review content. Requiredness remains
explicit even when the binding cannot be decoded. Missing, unsupported, or changed binding refuses
judgment and issuance; it cannot turn the request into an ordinary consent. Existing consents
without this requirement retain their current behavior. Adding this contract does not migrate
parked work or establish compatibility between application revisions.

The Composition produces its typed review from the frozen command and trusted admission records.
The authenticated reviewer reaches the same owner projection through snapshots, event streams,
and direct verdict responses. Before a stream event invokes that projection, its Consent must belong
to the event's Run. A mismatch invokes no producer and discloses no review. The owner checks current
permission to disclose the complete review and, separately, to judge that action. `runs:approve`
alone does not supply either object authority.
If required facts cannot be disclosed, the review remains unavailable and no verdict is admitted.
Generic arguments remain censored; private checkpoints, arbitrary metadata, and model-written
explanations cannot replace the required facts. Shared event history retains the Consent reference,
without caching one reviewer's disclosure for another.

A native verdict carries the exact review-binding digest presented by the client. Before settling
either approval or denial, or re-admitting a retry, the server checks that binding and the reviewer's
current eligibility again. The conditional verdict update preserves the binding and the first
settled decision. A client that omits or changes the digest cannot settle this native request;
older clients remain compatible with ordinary consents. The digest identifies the review being
judged. It does not prove that a human read it or authorize the later effect.

This client compatibility does not admit mixed server versions. Before native actions are admitted,
[Evolution](18-evolution.md#promote-across-the-temporal-boundary) must stop and replace every Consent
writer that predates the binding; an older pending-only update cannot enforce it.

The native action owner compares the retained preparation and review binding again before issuance
and performs the current authority checks required above. [Blockworld's Sentinel](../compositions/blockworld/sentinel.md)
defines the placement review; [Continuity](../compositions/blockworld/continuity.md) owns its atomic
preparation and action recovery. [Persistence](06-persistence.md#native-consent-bindings-designed)
owns schema compatibility. These requirements remain **Designed**: storage and transport alone do
not supply the owned preparation transaction, current authorizer, or complete client review.
[State of Work](../state-of-the-work.md#graph-stasis-consent) owns the delivered boundary.

## Consent history and proposal branches

The consent history extends the existing Consent ledger with attributable, append-only records.
One **proposal** binds one immutable request to its effect owner, effect revision, exact call or
native preparation/review binding, initiating Principal, and originating Run and occurrence. Its
stable identity is distinct from the Consent that judges it and any attempt that executes it.
A history group collects related proposals for inspection; it grants no authority of its own.

An admitted revision names the proposal it revises. Several alternatives may revise the same
proposal, forming branches. The server validates immutable, acyclic revision links within the
authorized group; the client cannot infer ancestry from timestamps, similar text, filenames, or
screen position. Additional dependency and artifact references remain typed links rather than
invented parentage. A group may relate work from different Runs only through an explicit,
authorized association; it cannot transfer either Run's consent or continuation ownership.

Each proposal's record sequence distinguishes preparation, judgment, withdrawal or supersession,
and references to effect-owner attempts and receipts. Records carry stable identities, an
owner-assigned sequence, actor/source attribution and recorded time. Human decisions and standing
policy decisions remain distinguishable. Corrections and bounded explanations append with their
provenance; they never rewrite the first settled verdict. Explanation text is untrusted content,
not executable direction, permission, an automatic Context injection, or training admission.

### Branches never inherit consent

A revision is a new proposal with a new identity and its own Consent. Approval cannot pass from
a parent, sibling, group, previously approved version, or human-authorship attestation. After
denial, a separately admitted revision remains possible, but denial itself neither schedules that
work nor promises an Agent response. If a proposal is later withdrawn, its historical approval
remains visible.

Creating an alternative does not silently supersede its predecessor. Explicit supersession must
close the predecessor's remaining issuance eligibility through its effect owner before admitting
the replacement as its successor. A pending verdict/withdrawal race uses the existing guarded
decision path. For an already approved proposal, withdrawal preserves that verdict and fences
future issuance separately; it cannot retract an issued effect. If an attempt may have started,
the owner must reconcile or complete cancellation before a replacement effect can be admitted.
An uncertain outcome never authorizes a duplicate attempt on another branch.

The consent state and its judgment history commit atomically before re-admission or UI publication.
The existing Consent decision path remains the judgment authority. The effect owner retains
effect-time authorization, attempt identity, execution and recovery. Its durable receipt or
reconcilable publication supplies history references bound to proposal, Consent, attempt and
effect revision; idempotent adoption cannot create an effect or infer its outcome from approval.
Missing, delayed, failed and unknown execution remain distinct. A lost history delivery cannot
cause a second effect, and a history read cannot resume a Run.

### Typed review, shared history

The shared history envelope covers file changes, network acquisition, external disclosure,
spending, and deployment. Each effect owner still supplies the versioned review profile and
receipt semantics for its own act: file review links exact base, candidate, and diff; network
review binds destination and limits; other types expose the facts their law requires. An
unsupported profile must remain visibly unavailable for judgment. The envelope cannot register
or authorize a new effect class.

Bridge presents proposals as a tree with separate decision and execution details. Orb correlates
the same identities to retained Run evidence. Both consume authorized, bounded pages from the
same records; neither copies a separate verdict store or derives success from a tree badge.
Expansion and filtering preserve stable identities and disclose pagination or unavailable
history. A semantic list with keyboard-operated disclosure supports the same inspection without
requiring a graph canvas. Group selection provides no blanket approval.

Artifact revision history and [authorship/protected-region records](28-workflow.md#authorship-provenance-and-protected-regions)
remain with the artifact owner. Consent links their exact revisions rather than duplicating them;
approval does not attest authorship or prove that the bytes were applied. Each read rechecks
disclosure of records and referenced artifacts, including ancestry and counts. A visible proposal
does not make a private predecessor, explanation, diff or receipt public.
[Persistence](06-persistence.md#consent-history-custody) owns journal consistency and retention.
[State of Work](../state-of-the-work.md#graph-stasis-consent) distinguishes this history contract
from the current consent implementation.

## Codex preauthorization

A Rune under runes/codex/preauth matches Sigil/tool patterns, supported argument allowlists or
string prefixes, optional expiry, and optional max uses; unknown constraints fail closed. PostgreSQL
uses guarded UPDATE RETURNING for budget consumption and commits a consumed use with its consent
row in one transaction. ZTE requires non-empty constraints, expiry, and max_uses; standard may still
be broader.

An expiry names an absolute instant with an explicit timezone. Rune validation rejects timezone-free
datetimes before policy admission rather than interpreting them in the host's local timezone.

A named argument constraint requires that argument to be present. Absence never aliases an explicit
JSON `null`, even when `null` is itself an allowed value; otherwise an omitted authority-bearing
field could satisfy policy accidentally.

Preauthorization is Magus policy, never model confidence. Startup reconciles the complete Rune-owned
set in one transaction: same-slug rows retain usage and a manual disable, changed policy fields are
replaced, and absent Rune-owned rows are disabled. PostgreSQL startup fails closed when this sync
fails. An auto-granted Consent stores a digest of the policy that authorized it; before Graph accepts
that verdict, PostgreSQL rechecks the row is enabled, unexpired by database time, and digest-equal.
This is standing-policy revalidation, not the still-required generic effect-time IAM/object/authority
check after arbitrary intervening work.

## Failure and recovery

| Failure | Result |
| --- | --- |
| Worker/Vessel dies pending | Consent and checkpoint persist; lease does not. |
| Verdict before queue publication | Exact pending delivery survives; startup/relay publishes it. |
| Duplicate/contradictory verdict | First settled verdict is authoritative. |
| Multiple deferred calls | Policy bottleneck; no shared verdict. |
| Missing checkpoint | Honest stasis-lost failure. |
| Old hop races newer | Hop ownership/enqueue_seq bars old settlement. |
| Run cancelled while pending | Consent settles as `cancelled`; no later verdict can re-admit it. |
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
verdict-before-resume, delivery reconciliation, memory-backed preauthorization,
Sigil guards, terminal cleanup, PostgreSQL first-verdict concurrency, and preauthorization rollback.
Disposable PostgreSQL receipts cover use-and-consent atomicity, complete-set Rune sync, DB-time
expiry, policy-digest invalidation, and startup failure propagation. Generic effect-time
reauthorization and a full Consent-plus-Checkpoint process-restart receipt remain absent. State owns
graph-stasis and local-Sigil delivery claims.
